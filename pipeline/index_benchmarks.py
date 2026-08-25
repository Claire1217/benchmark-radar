#!/usr/bin/env python3
"""Index benchmark releases from arXiv's official OAI-PMH feed.

The pipeline is intentionally conservative: it publishes only papers whose
title/abstract contain explicit release language and benchmark evidence. Other
matches go to a review queue. It never invents code, data, dates, or adoption
signals.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
from pathlib import Path
import random
import re
import socket
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "pipeline" / "config.json"
DATA_PATH = ROOT / "data" / "benchmarks.json"
REVIEW_PATH = ROOT / "data" / "review_queue.json"
OVERRIDES_PATH = ROOT / "data" / "curated_overrides.json"
CURATED_RECORDS_PATH = ROOT / "data" / "curated_records.json"
RUNS_PATH = ROOT / "data" / "runs"
OAI_URL = "https://oaipmh.arxiv.org/oai"
OAI_MAX_ATTEMPTS = 5
OAI_RETRY_BASE_SECONDS = 1.0
OAI_RETRY_CAP_SECONDS = 60.0
PUBLICATION_TIMEZONE = ZoneInfo("Australia/Brisbane")
OAI_NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "raw": "http://arxiv.org/OAI/arXivRaw/",
}


def publication_today() -> date:
    return datetime.now(PUBLICATION_TIMEZONE).date()

BENCHMARK_TERMS = re.compile(
    r"\b(benchmark|bench|evaluation suite|testbed|challenge set|evaluation dataset)\b",
    re.I,
)
RELEASE_LANGUAGE = re.compile(
    r"\b(we (?:introduce|present|propose|release|develop|build)|"
    r"this (?:paper )?(?:introduces|presents|proposes|releases)|"
    r"introducing|a new benchmark|new evaluation suite)\b",
    re.I,
)
EVALUATION_LANGUAGE = re.compile(
    r"\b(metric|leaderboard|baseline|evaluation protocol|test set|human baseline|"
    r"tasks?|instances?|samples?|annotations?)\b",
    re.I,
)
EXTENSION_LANGUAGE = re.compile(
    r"\b(extend|extension|updated version|new version|successor|refresh|rebench)\b",
    re.I,
)
AGGREGATION_LANGUAGE = re.compile(
    r"\b(aggregate|unified suite|collection of benchmarks|benchmark suite)\b",
    re.I,
)
URL_RE = re.compile(r"https?://[^\s<>\]\[(){}\"']+")
NAMED_BENCHMARK_RE = re.compile(
    r"\b(?:introduce|present|propose|release|develop|build|construct)\s+"
    r"(?:an?\s+|the\s+)?(?:new\s+)?(?:\\(?:textbf|textsc|emph)\{)?"
    r"([A-Z][A-Za-z0-9+_.-]{2,50}(?:Bench|Benchmark)(?:-[A-Za-z0-9]+)?)",
    re.I,
)


@dataclass(frozen=True)
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    primary_category: str
    released_at: str
    updated_at: str
    entry_url: str
    pdf_url: str
    comments: str
    journal_ref: str = ""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def normalize_space(value: str | None) -> str:
    return " ".join((value or "").split())


def category_to_set_spec(category: str) -> str:
    group, leaf = category.split(".", 1)
    return f"{group}:{group}:{leaf}"


def oai_text(element: ET.Element, path: str) -> str:
    found = element.find(path, OAI_NS)
    return normalize_space(found.text if found is not None else "")


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_paper(record: ET.Element) -> Paper | None:
    raw = record.find("oai:metadata/raw:arXivRaw", OAI_NS)
    if raw is None:
        return None
    arxiv_id = oai_text(raw, "raw:id")
    versions = raw.findall("raw:version", OAI_NS)
    if not arxiv_id or not versions:
        return None
    first = parse_timestamp(oai_text(versions[0], "raw:date"))
    last = parse_timestamp(oai_text(versions[-1], "raw:date"))
    if first is None:
        return None
    categories = oai_text(raw, "raw:categories").split()
    return Paper(
        arxiv_id=arxiv_id,
        title=oai_text(raw, "raw:title"),
        authors=[item.strip() for item in oai_text(raw, "raw:authors").split(",") if item.strip()],
        abstract=oai_text(raw, "raw:abstract"),
        categories=categories,
        primary_category=categories[0] if categories else "",
        released_at=first.date().isoformat(),
        updated_at=(last or first).isoformat().replace("+00:00", "Z"),
        entry_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        comments=oai_text(raw, "raw:comments"),
        journal_ref=oai_text(raw, "raw:journal-ref"),
    )


def retry_after_seconds(error: HTTPError) -> float | None:
    """Parse Retry-After as delta seconds or an HTTP date."""
    value = error.headers.get("Retry-After") if error.headers else None
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        parsed = parse_timestamp(value)
        if parsed is None:
            return None
        return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())


def oai_retry_delay(attempt: int, error: Exception) -> float:
    """Return bounded Retry-After or exponential backoff with jitter."""
    if isinstance(error, HTTPError):
        retry_after = retry_after_seconds(error)
        if retry_after is not None:
            return min(retry_after, OAI_RETRY_CAP_SECONDS)
    exponential = min(OAI_RETRY_BASE_SECONDS * (2**attempt), OAI_RETRY_CAP_SECONDS)
    return min(exponential + random.uniform(0.0, exponential * 0.25), OAI_RETRY_CAP_SECONDS)


def request_oai(params: dict[str, str]) -> ET.Element:
    request = Request(
        f"{OAI_URL}?{urlencode(params)}",
        headers={"User-Agent": "BenchmarkRadar/1.0 (https://github.com/Claire1217/benchmark-radar)"},
    )
    body: bytes | None = None
    for attempt in range(OAI_MAX_ATTEMPTS):
        try:
            with urlopen(request, timeout=90) as response:
                body = response.read()
            break
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code <= 599
            if not retryable or attempt == OAI_MAX_ATTEMPTS - 1:
                raise
            time.sleep(oai_retry_delay(attempt, error))
        except (socket.timeout, TimeoutError, URLError) as error:
            if attempt == OAI_MAX_ATTEMPTS - 1:
                raise
            time.sleep(oai_retry_delay(attempt, error))
    if body is None:  # Defensive; every exhausted path above re-raises.
        raise RuntimeError("OAI-PMH request ended without a response")
    root = ET.fromstring(body)
    # OAI protocol errors are valid HTTP responses, not transport failures.
    # Keep them outside the retry loop so semantic errors are never swallowed.
    error = root.find("oai:error", OAI_NS)
    if error is not None and error.attrib.get("code") != "noRecordsMatch":
        raise RuntimeError(f"OAI-PMH error {error.attrib.get('code')}: {normalize_space(error.text)}")
    return root


def fetch_for_range(start_date: str, end_date: str, config: dict[str, Any]) -> list[Paper]:
    settings = config["arxiv"]
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end date must be on or after start date")
    until = min(end + timedelta(days=int(settings["lookahead_days"])), publication_today()).isoformat()
    seen: set[str] = set()
    papers: list[Paper] = []
    for category in settings["categories"]:
        params = {
            "verb": "ListRecords",
            "metadataPrefix": "arXivRaw",
            "set": category_to_set_spec(category),
            "from": start_date,
            "until": until,
        }
        while True:
            root = request_oai(params)
            for record in root.findall(".//oai:record", OAI_NS):
                paper = parse_paper(record)
                if paper is None or paper.arxiv_id in seen or not (start_date <= paper.released_at <= end_date):
                    continue
                seen.add(paper.arxiv_id)
                papers.append(paper)
                if len(papers) >= int(settings["max_papers"]):
                    return sorted(papers, key=lambda item: item.arxiv_id)
            token = oai_text(root, ".//oai:resumptionToken")
            if not token:
                break
            params = {"verb": "ListRecords", "resumptionToken": token}
            time.sleep(float(settings["request_delay_seconds"]))
    return sorted(papers, key=lambda item: item.arxiv_id)


def fetch_for_date(target_date: str, config: dict[str, Any]) -> list[Paper]:
    return fetch_for_range(target_date, target_date, config)


def first_sentence(text: str, limit: int = 240) -> str:
    cleaned = normalize_space(text)
    match = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0]
    return match if len(match) <= limit else match[: limit - 1].rstrip() + "…"


def named_title_release_pair(paper: Paper) -> tuple[str, str] | None:
    """Find a named benchmark identity followed shortly by a task release.

    Some abstracts establish the artifact identity ("X, a suite of tasks") and
    announce the public task release in a later sentence. Requiring the word
    "benchmark" and "release" in one sentence misses these papers. This path is
    deliberately limited to an explicit Bench/Benchmark title, the exact title
    name in the identity sentence, and a release of evaluation instances rather
    than code, weights, or a generic framework alone.
    """
    if not has_named_benchmark_title(paper.title):
        return None
    name = normalize_space(paper.title.partition(":")[0])
    if not name:
        return None
    identity_name = re.compile(rf"\b{re.escape(name)}\b", re.I)
    identity_artifact = re.compile(r"\b(?:benchmark|suite|testbed|evaluation set)\b", re.I)
    identity_instances = re.compile(r"\b(?:tasks?|instances?|examples?|test cases?)\b", re.I)
    released_instances = re.compile(
        r"\b(?:we|this work|the authors?)\s+(?:also\s+)?(?:publicly\s+)?release\b"
        r"[^.!?]{0,180}\b(?:tasks?|instances?|examples?|test cases?|test set|dataset|benchmark)\b",
        re.I,
    )
    sentences = re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract))
    for identity_index, identity in enumerate(sentences):
        if not (
            identity_name.search(identity)
            and identity_artifact.search(identity)
            and identity_instances.search(identity)
        ):
            continue
        # Permit one intervening sentence describing the task construction.
        for release in sentences[identity_index + 1 : identity_index + 3]:
            if released_instances.search(release):
                return identity, release
    return None


def evidence_sentence(paper: Paper) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract))
    # Prefer the sentence that names the released artifact. A preceding generic
    # phrase such as "benchmark evaluation" is weaker evidence and can make a
    # valid record appear unsupported in the public audit trail.
    for sentence in sentences:
        cleaned = sentence.replace("\\textbf{", "").replace("\\textsc{", "")
        if NAMED_BENCHMARK_RE.search(cleaned):
            return sentence[:500]
    for sentence in sentences:
        if BENCHMARK_TERMS.search(sentence) and RELEASE_LANGUAGE.search(sentence):
            return sentence[:500]
    release_pair = named_title_release_pair(paper)
    if release_pair:
        identity, release = release_pair
        return f"{identity} […] {release}"[:500]
    for sentence in sentences:
        if BENCHMARK_TERMS.search(sentence):
            return sentence[:500]
    return first_sentence(paper.abstract, 500)


def has_same_sentence_release_evidence(paper: Paper) -> bool:
    """Return whether one sentence explicitly releases a benchmark artifact."""
    sentences = re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract))
    return any(
        BENCHMARK_TERMS.search(sentence) and RELEASE_LANGUAGE.search(sentence)
        and not has_negated_benchmark_context(sentence)
        for sentence in sentences
    )


def has_release_evidence(paper: Paper) -> bool:
    """Require same-sentence evidence or a tightly constrained named pair."""
    return has_same_sentence_release_evidence(paper) or named_title_release_pair(paper) is not None


def has_named_benchmark_title(title: str) -> bool:
    prefix, separator, _ = title.partition(":")
    name = normalize_space(prefix)
    return bool(
        separator
        and looks_like_coined_name(name)
        and re.search(r"(?:Bench|Benchmark)$", name, re.I)
        and not re.search(r"^from\b.+\bto\s+(?:a\s+)?benchmark$", name, re.I)
    )


def looks_like_coined_name(value: str) -> bool:
    """Reject sentence-like title prefixes as automatic artifact identities."""
    name = normalize_space(value)
    return bool(
        2 <= len(name) <= 48
        and len(name.split()) <= 5
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+_.&'\-/ ]+", name)
    )


def has_negated_benchmark_context(sentence: str) -> bool:
    """Do not turn statements about a missing benchmark into identities."""
    return bool(
        re.search(
            r"\b(?:lacks?|lacking|no|without|does\s+not\s+(?:have|provide|include))\b"
            r"[^.!?]{0,80}\b(?:benchmark|evaluation suite|testbed)\b",
            sentence,
            re.I,
        )
    )


def exact_benchmark_identity(paper: Paper, name: str) -> bool:
    """Require NAME itself, rather than a nearby model or dataset, to be the artifact."""
    escaped = re.escape(normalize_space(name))
    identity = re.compile(
        rf"\b{escaped}\b\s*(?:,|\bis\b|\bconstitutes\b|\bprovides\b)\s*"
        rf"(?:an?|the|our|this)\s+(?:new\s+)?"
        rf"(?:[A-Za-z][A-Za-z-]*(?:\s+|,\s*)){{0,8}}?"
        rf"(?:benchmark|evaluation suite|testbed)\b",
        re.I,
    )
    for sentence in re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract)):
        if not identity.search(sentence) or has_negated_benchmark_context(sentence):
            continue
        if re.search(
            rf"\b{escaped}\b\s*(?:,|\bis\b)\s*(?:an?|the|our|this)\s+"
            rf"(?:[A-Za-z][A-Za-z-]*\s+){{0,4}}?(?:model|method|framework|dataset|approach|system)\b",
            sentence,
            re.I,
        ):
            continue
        if re.search(
            r"\b(?:existing|established|previously released|widely[- ]used)\b"
            r"[^.!?]{0,100}\b(?:benchmark|evaluation suite|testbed)\b",
            sentence,
            re.I,
        ):
            continue
        return True
    return False


def declared_non_benchmark_identity(paper: Paper, name: str) -> bool:
    """Detect when a tempting title prefix is explicitly typed as another entity."""
    escaped = re.escape(normalize_space(name))
    typed = re.compile(
        rf"\b{escaped}\b\s*(?:,|\bis\b|\bconstitutes\b)\s*"
        rf"(?:an?|the|our|this)\s+(?:new\s+)?(?:[A-Za-z][A-Za-z-]*\s+){{0,4}}?"
        rf"(?:model|method|framework|dataset|approach|system)\b",
        re.I,
    )
    return any(
        typed.search(sentence)
        for sentence in re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract))
    )


def benchmarked_on_named_dataset(paper: Paper, name: str) -> bool:
    escaped = re.escape(normalize_space(name))
    return bool(
        re.search(
            rf"\b(?:we\s+)?benchmark(?:ed|ing|s)?\s+"
            rf"(?:[^.!?]{{0,80}}\s+)?on\s+(?:the\s+)?{escaped}\b",
            normalize_space(paper.abstract),
            re.I,
        )
    )


def has_named_benchmark_entity(paper: Paper) -> bool:
    """Recognize coined names such as DeepSWE that do not end in 'Bench'."""
    prefix, separator, _ = paper.title.partition(":")
    name = normalize_space(prefix)
    if not separator or not looks_like_coined_name(name):
        return False
    return exact_benchmark_identity(paper, name)


def named_abstract_benchmark(paper: Paper) -> str | None:
    """Return an explicitly released Bench-name unless it is typed as something else."""
    cleaned = normalize_space(paper.abstract).replace("\\textbf{", "").replace("\\textsc{", "")
    for match in NAMED_BENCHMARK_RE.finditer(cleaned):
        name = match.group(1).rstrip("}")
        if not declared_non_benchmark_identity(paper, name) and not has_negated_benchmark_context(
            cleaned[max(0, match.start() - 80) : match.end() + 100]
        ):
            return name
    return None


def canonical_name(paper: Paper) -> str:
    title = paper.title
    prefix, separator, remainder = title.partition(":")
    safe_title_identity = bool(
        exact_benchmark_identity(paper, prefix)
        or AGGREGATION_LANGUAGE.search(paper.abstract)
        or (
            not declared_non_benchmark_identity(paper, prefix)
            and not benchmarked_on_named_dataset(paper, prefix)
            and not any(
                prefix.lower() in sentence.lower() and has_negated_benchmark_context(sentence)
                for sentence in re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract))
            )
        )
    )
    if has_named_benchmark_title(title) and safe_title_identity:
        return prefix.strip()
    # Prefer an exact coined title identity over a shorter Bench-token found in
    # the abstract (for example, "SWE-bench Science" must not become
    # "SWE-bench").
    if separator and has_named_benchmark_entity(paper):
        return prefix.strip()
    named = named_abstract_benchmark(paper)
    if named:
        return named
    if separator and re.search(r"(?:Bench|Benchmark)$", normalize_space(prefix), re.I) and not safe_title_identity:
        return title
    match = re.search(r"\b([A-Z][A-Za-z0-9+_.-]{2,30}(?:Bench|Benchmark))\b", title)
    return match.group(1) if match else title


def classify_area(paper: Paper) -> str:
    text = f"{paper.title} {evidence_sentence(paper)}".lower()
    if re.search(r"\b(cad|computer-aided design|engineering drawing|mechanical design)\b", text):
        return "Science & Engineering"
    if re.search(r"\b(robot|embodied|manipulation|navigation)\b", text):
        return "Robotics & Embodied AI"
    direct_agent_signal = re.search(r"\b(tool use|computer use|web navigation)\b", text)
    contextual_agents = re.search(r"\bagents?\b", text) and re.search(
        r"\b(interactive|simulator|phone|smartphone|ios|android|mobile|environment|autonomous)\b",
        text,
    )
    if direct_agent_signal or contextual_agents:
        return "Agents & Tool Use"
    if re.search(r"\b(safety|bias|fairness|toxicity|jailbreak|robustness)\b", text):
        return "Safety & Trustworthiness"
    if re.search(r"\b(multimodal|vision-language|video-language|audio-visual)\b", text):
        return "Multimodal"
    if re.search(r"\b(code generation|software engineering|programming|program repair|gpu kernel|ptx)\b", text):
        return "Code & Software"
    if re.search(r"\b(image|vision|video|3d|rendering|segmentation|detection)\b", text):
        return "Vision & 3D"
    if re.search(r"\b(audio|speech|voice)\b", text):
        return "Speech & Audio"
    if paper.primary_category in {"cs.SE", "cs.PL", "cs.PF"}:
        return "Code & Software"
    if paper.primary_category == "cs.RO":
        return "Robotics & Embodied AI"
    if paper.primary_category in {"cs.CV", "cs.GR"}:
        return "Vision & 3D"
    return "Language & Knowledge"


def infer_topics(paper: Paper) -> list[str]:
    text = f"{paper.title} {evidence_sentence(paper)}".lower()
    mapping = [
        (r"\b(cad|computer-aided design)\b", "CAD"),
        (r"\b(self-evolv\w+|self-improv\w+|recursive self-improvement|agent evolution)\b", "Self-Evolution"),
        (r"\b(ai scientist|research agent|scientific discovery)\b", "AI Scientist"),
        (r"\b(agent|tool use)\b", "Agents"),
        (r"\b(robot|manipulation)\b", "Robotics"),
        (r"\b(multimodal|vision-language)\b", "Multimodal"),
        (r"\b(long context|long-context)\b", "Long Context"),
        (r"\b(safety|jailbreak|alignment)\b", "Safety"),
        (r"\b(code generation|software engineering|gpu kernel|ptx)\b", "Code"),
        (r"\b(reasoning)\b", "Reasoning"),
    ]
    topics = [label for pattern, label in mapping if re.search(pattern, text)]
    return topics[:3] or [paper.primary_category or "General"]


def infer_application_domains(paper: Paper) -> list[str]:
    """Map source text to a small controlled, cross-domain vocabulary."""
    scope_text = f"{paper.title} {evidence_sentence(paper)}".lower()
    full_text = f"{paper.title} {paper.abstract}".lower()
    finance_pattern = (
        r"\b(finance|financial|investment|banking|credit risk|stock(?: market)?|"
        r"equities?|portfolio|securities|algorithmic trading|quantitative trading)\b"
    )
    mapping = [
        (r"\b(ios|android|smartphone|phone agents?|mobile device|mobile computing|personal computing)\b", "Mobile & Personal Computing"),
        (r"\b(rtl|verilog|vhdl|eda|chip design|circuit design|place and route|logic synthesis)\b", "Chip Design & EDA"),
        (r"\b(software engineering|code generation|program repair|repository|compiler|gpu kernel|ptx|tokenizer)\b", "Software & AI Compute"),
        (r"\b(cybersecurity|vulnerability|exploit|malware|intrusion|incident response)\b", "Cybersecurity"),
        (r"\b(theorem|formal proof|formal mathematics|mathematical reasoning|olympiad|geometry proof)\b", "Mathematics & Formal Science"),
        (r"\b(quantum computing|quantum circuit|qubit|quantum control)\b", "Quantum Computing & Control"),
        (r"\b(particle accelerator|tokamak|plasma control|scientific facility|beamline)\b", "Scientific Facilities"),
        (r"\b(material discovery|materials science|molecule|chemical reaction|chemistry)\b", "Materials & Chemistry"),
        (r"\b(drug discovery|protein|genomic|biomedical|clinical|pathology|medical)\b", "Biology & Drug Discovery"),
        (r"\b(automated laboratory|self-driving lab|laboratory automation|scientific experiment)\b", "Autonomous Laboratories"),
        (r"\b(power grid|energy system|electricity market|optimal power flow)\b", "Energy & Grid"),
        (r"\b(manufacturing|industrial control|process control|factory|assembly line)\b", "Manufacturing & Process Control"),
        (r"\b(robot|robotic|embodied|manipulation|locomotion)\b", "Robotics & Embodied AI"),
        (r"\b(autonomous driving|self-driving|driving policy|traffic planning|vehicle planning)\b", "Autonomous Driving"),
        (r"\b(logistics|supply chain|vehicle routing|inventory|warehouse)\b", "Logistics & Operations"),
        (r"\b(advertising|ad auction|click-through|recommendation pricing|dynamic pricing)\b", "Advertising & Pricing"),
        (finance_pattern, "Finance"),
    ]
    cross_domain_topics = [
        finance_pattern,
        r"\b(healthcare|health|clinical|medical)\b",
        r"\b(energy|power grid|electricity)\b",
        r"\b(transportation|traffic|mobility)\b",
        r"\b(education|educational)\b",
        r"\b(science|scientific|academic)\b",
        r"\b(law|legal)\b",
        r"\b(web|internet)\b",
        r"\b(spatial|maps?)\b",
        r"\b(software engineering|code|programming)\b",
        r"\b(mathematics|mathematical|theorem)\b",
        r"\b(games?|entertainment)\b",
        r"\b(agriculture|land management)\b",
        r"\b(email|calendars?|professional networking)\b",
    ]
    explicit_scope_phrase = re.search(
        r"\b(?:cross[- ]domain|multi[- ]domain|"
        r"across\s+(?:(?:\w+|\d+)[- ]?){0,3}domains?|"
        r"spanning\s+(?:(?:\w+|\d+)[- ]?){0,3}domains?|"
        r"spans?\s+\d+\s+(?:\w+\s+){0,2}domains?|"
        r"\d+\s+domain groups?|domains?\s+such\s+as)\b",
        full_text,
    )
    enumerates_multiple_domains = any(
        sum(bool(re.search(pattern, sentence)) for pattern in cross_domain_topics) >= 3
        for sentence in re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract).lower())
    )
    strong_finance_title = bool(re.search(finance_pattern, paper.title.lower()))
    is_explicitly_cross_domain = bool(
        not strong_finance_title
        and (explicit_scope_phrase or enumerates_multiple_domains)
    )
    scope_matches = [label for pattern, label in mapping if re.search(pattern, scope_text)]
    if is_explicitly_cross_domain:
        return ["General AI", *scope_matches[:2]]
    # Prefer the benchmark identity/evaluation-target sentence. Only use the
    # full abstract when that explicit scope has no controlled-domain match, so
    # an incidental finance task inside a phone benchmark cannot become primary.
    matches = scope_matches or [label for pattern, label in mapping if re.search(pattern, full_text)]
    return matches[:3] or ["General AI"]


def infer_industry_sectors(domains: list[str]) -> list[str]:
    mapping = {
        "Mobile & Personal Computing": "Consumer Technology",
        "Chip Design & EDA": "Semiconductors",
        "Software & AI Compute": "Software & Cloud",
        "Cybersecurity": "Cybersecurity",
        "Quantum Computing & Control": "Quantum Technology",
        "Scientific Facilities": "Research Infrastructure",
        "Materials & Chemistry": "Materials & Chemicals",
        "Biology & Drug Discovery": "Pharma & Biotech",
        "Autonomous Laboratories": "Laboratory Automation",
        "Energy & Grid": "Energy & Utilities",
        "Manufacturing & Process Control": "Manufacturing",
        "Robotics & Embodied AI": "Robotics",
        "Autonomous Driving": "Automotive",
        "Logistics & Operations": "Logistics",
        "Advertising & Pricing": "Digital Platforms",
        "Finance": "Financial Services",
    }
    return list(dict.fromkeys(mapping[domain] for domain in domains if domain in mapping))


def infer_capabilities(paper: Paper) -> list[str]:
    text = f"{paper.title} {evidence_sentence(paper)}".lower()
    mapping = [
        (r"\breasoning\b", "Reasoning"),
        (r"\bplanning\b", "Planning"),
        (r"\btool use\b", "Tool use"),
        (r"\bretrieval\b", "Information retrieval"),
        (r"\b(code generation|programming|gpu kernel|ptx)\b", "Code generation"),
        (r"\b3d|geometry|cad\b", "Geometric reasoning"),
        (r"\bmanipulation\b", "Robot manipulation"),
        (r"\brobustness\b", "Robustness"),
        (r"\bfactual|knowledge\b", "Factuality"),
    ]
    values = [label for pattern, label in mapping if re.search(pattern, text)]
    return values[:3]


def infer_construction(paper: Paper) -> tuple[str, str]:
    text = paper.abstract.lower()
    if re.search(r"\b(simulator|interactive environment|real[- ]world environments?)\b", text):
        return "Interactive Environment", "Unknown"
    if re.search(r"\bsynthetic|programmatically generated|procedurally generated\b", text):
        return "Original Synthetic", "Machine Generated"
    if re.search(r"\baggregate|collection of existing|combine existing\b", text):
        return "Aggregate Existing", "Mixed"
    if re.search(r"\bcurat|filter|re-annotat|post-process|derived from\b", text):
        return "Transform Existing", "Unknown"
    return "Unknown", "Unknown"


ACCEPTED_COMMENT_RE = re.compile(
    r"\b(?:accepted(?:\s+(?:at|to|by|for))?|to appear in|forthcoming in)\s+"
    r"(?:the\s+)?([^.;\n]{2,120})",
    re.I,
)
NEGATIVE_ACCEPTANCE_RE = re.compile(
    r"\b(?:not accepted|rejected|under review|submitted to|submission to)\b",
    re.I,
)


def infer_publication(paper: Paper, checked_at: str) -> dict[str, Any]:
    """Extract source-stated venue facts without upgrading author claims."""
    journal_ref = normalize_space(paper.journal_ref)
    if journal_ref:
        return {
            "status": "publication_reported",
            "venue": journal_ref[:160],
            "evidence": journal_ref,
            "evidenceUrl": paper.entry_url,
            "source": "arxiv-journal-reference",
            "evidenceLevel": "strong-author-metadata",
            "verifiedAt": checked_at,
        }

    comments = normalize_space(paper.comments)
    if comments and not NEGATIVE_ACCEPTANCE_RE.search(comments):
        match = ACCEPTED_COMMENT_RE.search(comments)
        if match:
            venue = normalize_space(match.group(1)).strip(" ,:-")
            return {
                "status": "acceptance_claimed",
                "venue": venue[:120],
                "evidence": comments[:300],
                "evidenceUrl": paper.entry_url,
                "source": "arxiv-comments",
                "evidenceLevel": "author-claim",
                "verifiedAt": checked_at,
            }

    return {
        "status": "unverified",
        "venue": None,
        "evidence": None,
        "evidenceUrl": paper.entry_url,
        "source": "arxiv-metadata",
        "evidenceLevel": "unverified",
        "verifiedAt": checked_at,
    }


def venue_entities(publication: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Keep review attempts and publication records as separate entities."""
    evidence = {
        "sourceType": publication["source"],
        "sourceUrl": publication["evidenceUrl"],
        "observedAt": publication["verifiedAt"],
        "rawValue": publication["evidence"],
        "level": publication["evidenceLevel"],
    }
    if publication["status"] == "acceptance_claimed":
        return {
            "venueAttempts": [{
                "venueName": publication["venue"],
                "reviewStatus": "accepted",
                "decisionRaw": publication["evidence"],
                "evidence": [evidence],
            }],
            "publications": [],
        }
    if publication["status"] == "publication_reported":
        return {
            "venueAttempts": [],
            "publications": [{
                "venueName": publication["venue"],
                "publicationStatus": "published",
                "evidence": [evidence],
            }],
        }
    return {"venueAttempts": [], "publications": []}


def extract_links(paper: Paper) -> dict[str, str | None]:
    urls = [url.rstrip(".,;:!?") for url in URL_RE.findall(f"{paper.abstract} {paper.comments}")]
    code = next((url for url in urls if "github.com/" in url.lower()), None)
    data = next(
        (
            url
            for url in urls
            if "huggingface.co/datasets/" in url.lower()
            or "zenodo.org/" in url.lower()
            or "figshare.com/" in url.lower()
        ),
        None,
    )
    project = next(
        (
            url
            for url in urls
            if not any(host in url.lower() for host in ("github.com/", "huggingface.co/", "zenodo.org/", "figshare.com/"))
        ),
        None,
    )
    return {
        "report": paper.entry_url,
        "paper": paper.entry_url,
        "pdf": paper.pdf_url,
        "project": project,
        "code": code,
        "data": data,
    }


def recognition(paper: Paper) -> tuple[float, str, list[str]]:
    title = paper.title.lower()
    text = f"{paper.title} {paper.abstract}"
    normalized_abstract = normalize_space(paper.abstract).replace("\\textbf{", "")
    reasons: list[str] = []
    score = 0.0
    named_title = has_named_benchmark_title(paper.title)
    named_entity = has_named_benchmark_entity(paper)
    named_abstract_name = named_abstract_benchmark(paper)
    named_abstract_release = named_abstract_name is not None
    if named_title:
        score += 0.5
        reasons.append("coined title prefix ending in Bench or Benchmark")
    elif named_entity:
        score += 0.7
        reasons.append("exact coined title identity tied to benchmark evidence")
    elif named_abstract_release:
        score += 0.5
        reasons.append("exact named benchmark artifact released in abstract")
    elif BENCHMARK_TERMS.search(paper.abstract):
        score += 0.1
        reasons.append("benchmark term in abstract")
    same_sentence_release = has_same_sentence_release_evidence(paper)
    paired_release = named_title_release_pair(paper) is not None
    release_evidence = same_sentence_release or paired_release
    if release_evidence:
        score += 0.35
        reasons.append(
            "benchmark release stated in one sentence"
            if same_sentence_release
            else "named benchmark identity and task release stated in nearby sentences"
        )
    if EVALUATION_LANGUAGE.search(paper.abstract):
        score += 0.15
        reasons.append("evaluation protocol evidence")
    if URL_RE.search(f"{paper.abstract} {paper.comments}"):
        score += 0.1
        reasons.append("public artifact URL")
    if not (named_title or named_entity or named_abstract_release) and not release_evidence:
        score = min(score, 0.55)
        reasons.append("no explicit benchmark release evidence")
    score = min(score, 1.0)
    decisive_text = f"{paper.title} {evidence_sentence(paper)}"
    if re.search(r"\b(extend|updated version|new version|successor|refresh|rebench)\b", decisive_text, re.I):
        relation = "extends"
    elif AGGREGATION_LANGUAGE.search(decisive_text):
        relation = "aggregates"
    elif release_evidence or named_title or named_entity or named_abstract_release:
        relation = "introduces"
    else:
        relation = "unclear"
    benchmark_study_title = bool(
        re.search(
            r"\b(?:benchmark(?:ing)? (?:study|comparison|analysis)|"
            r"systematic benchmark|comparative benchmark|comparison of benchmarks?)\b",
            title,
        )
    )
    existing_dataset_evidence = bool(
        re.search(
            r"\b(?:existing|established|public|publicly available|widely[- ]used|standard)\b",
            paper.abstract,
            re.I,
        )
        and re.search(r"\b(?:datasets?|benchmarks?|test sets?)\b", paper.abstract, re.I)
    )
    exact_named_artifact_action = bool(
        named_abstract_release
        or paired_release
        or (
            named_entity
            and (
                release_evidence
                or AGGREGATION_LANGUAGE.search(paper.abstract)
            )
        )
    )
    if benchmark_study_title and existing_dataset_evidence and not exact_named_artifact_action:
        relation = "evaluates_only"
        score = min(score, 0.55)
        reasons.append("benchmark study on existing or public datasets without a named artifact release")
    prefix = normalize_space(paper.title.partition(":")[0])
    exact_prefix_identity = bool(prefix and exact_benchmark_identity(paper, prefix))
    explicit_aggregation = bool(AGGREGATION_LANGUAGE.search(paper.abstract))
    non_benchmark_identity = bool(prefix and declared_non_benchmark_identity(paper, prefix))
    dataset_scoring_usage = bool(prefix and benchmarked_on_named_dataset(paper, prefix))
    negated_identity_context = any(
        prefix.lower() in sentence.lower() and has_negated_benchmark_context(sentence)
        for sentence in re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract))
    )
    if (
        (non_benchmark_identity or dataset_scoring_usage or negated_identity_context)
        and not exact_prefix_identity
        and not explicit_aggregation
    ):
        relation = "evaluates_only"
        score = min(score, 0.55)
        reasons.append("named entity is a model, method, framework, or dataset used in evaluation")
    if title.startswith("benchmarking ") and not RELEASE_LANGUAGE.search(paper.abstract):
        relation = "evaluates_only"
        score = min(score, 0.55)
        reasons.append("benchmarking study without explicit release")
    return score, relation, reasons


def stable_id(paper: Paper, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:42] or "benchmark"
    digest = hashlib.sha256(paper.arxiv_id.encode()).hexdigest()[:8]
    return f"bm_{slug}_{digest}"


def family_id(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", name.lower()) or "benchmark"
    return f"bmf_{hashlib.sha256(normalized.encode()).hexdigest()[:12]}"


def to_record(paper: Paper, indexed_at: str, score: float, relation: str, reasons: list[str]) -> dict[str, Any]:
    name = canonical_name(paper)
    application_domains = infer_application_domains(paper)
    construction, annotation = infer_construction(paper)
    links = extract_links(paper)
    readiness = "Runnable" if links["code"] else "Inspectable" if links["data"] else "Paper only"
    publication = infer_publication(paper, indexed_at)
    venue_metadata = venue_entities(publication)
    return {
        "id": stable_id(paper, name),
        "familyId": family_id(name),
        "name": name,
        "paperTitle": paper.title,
        "aliases": [],
        "oneLine": first_sentence(paper.abstract),
        "area": classify_area(paper),
        "applicationDomains": application_domains,
        "primaryDomain": application_domains[0],
        "industrySectors": infer_industry_sectors(application_domains),
        "domainCuration": {"state": "auto", "method": "rules-v1"},
        "capabilities": infer_capabilities(paper),
        "topics": infer_topics(paper),
        "construction": construction,
        "annotation": annotation,
        "readiness": readiness,
        "publication": publication,
        "venueAttempts": venue_metadata["venueAttempts"],
        "publications": venue_metadata["publications"],
        "releasedAt": paper.released_at,
        "firstSeenAt": indexed_at[:10],
        "indexedAt": indexed_at,
        "sourceUpdatedAt": paper.updated_at,
        "adoption30d": None,
        "heat": None,
        "confidence": "High" if score >= 0.9 else "Medium",
        "recognitionConfidence": round(score, 2),
        "relation": relation,
        "links": links,
        "motivation": first_sentence(paper.abstract, 420),
        "constructionDetail": "Unknown — the indexer does not infer construction details without explicit source evidence.",
        "metrics": [],
        "source": {
            "type": "arxiv",
            "id": paper.arxiv_id,
            "url": paper.entry_url,
            "title": paper.title,
            "authors": paper.authors,
            "categories": paper.categories,
        },
        "evidence": {
            "snippet": evidence_sentence(paper),
            "reasonCodes": reasons,
        },
        "dataStatus": "primary-source-indexed",
        "demo": False,
    }


def upsert(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source = {
        str(record.get("source", {}).get("id")): record
        for record in existing
        if record.get("source", {}).get("id")
    }
    for record in incoming:
        source_id = str(record["source"]["id"])
        previous = by_source.get(source_id)
        if previous:
            record["firstSeenAt"] = previous.get("firstSeenAt", record["firstSeenAt"])
            # Discovery refreshes must not erase the last valid enrichment
            # snapshot before the non-blocking metrics stage succeeds.
            for key in ("attention", "ranking", "watch"):
                if key not in record and key in previous:
                    record[key] = previous[key]
        by_source[source_id] = record
    return sorted(by_source.values(), key=lambda item: (item["releasedAt"], item["id"]), reverse=True)


def merge_patch(target: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Apply a small JSON Merge Patch-style curated overlay."""
    result = dict(target)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_patch(result[key], value)
        else:
            result[key] = value
    return result


def apply_curated_overrides(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not OVERRIDES_PATH.exists():
        return records
    overrides = read_json(OVERRIDES_PATH).get("byArxivId", {})
    return [
        merge_patch(record, overrides.get(str(record.get("source", {}).get("id")), {}))
        for record in records
    ]


def curated_records() -> list[dict[str, Any]]:
    """Load reviewed releases admitted from primary-source evidence."""
    if not CURATED_RECORDS_PATH.exists():
        return []
    return read_json(CURATED_RECORDS_PATH).get("records", [])


def persistent_review_candidates(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    range_start: str,
    range_end: str,
    excluded_source_ids: set[str],
) -> list[dict[str, Any]]:
    """Upsert one source window without deleting deferred candidates elsewhere."""
    previous_by_source = {
        str((candidate.get("source") or {}).get("id") or ""): candidate
        for candidate in existing
    }
    retained = [
        candidate
        for candidate in existing
        if not (range_start <= str(candidate.get("releasedAt", "")) <= range_end)
    ]
    by_source = {
        str((candidate.get("source") or {}).get("id") or ""): candidate
        for candidate in retained
        if str((candidate.get("source") or {}).get("id") or "") not in excluded_source_ids
    }
    for candidate in incoming:
        source_id = str((candidate.get("source") or {}).get("id") or "")
        if not source_id or source_id in excluded_source_ids:
            continue
        by_source[source_id] = candidate
    for candidate in by_source.values():
        candidate["capabilities"] = [
            value for value in candidate.get("capabilities", []) if value != "Evaluation"
        ]
    return sorted(
        by_source.values(),
        key=lambda item: (item.get("releasedAt", ""), item.get("id", "")),
        reverse=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index new benchmark releases from arXiv OAI-PMH.")
    parser.add_argument("--date", help="First-public-release date in YYYY-MM-DD.")
    parser.add_argument("--start-date", help="Inclusive first-public-release start date.")
    parser.add_argument("--end-date", help="Inclusive first-public-release end date.")
    parser.add_argument("--latest-with-papers", action="store_true", help="Look back to the latest non-empty arXiv date.")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def index_papers(
    papers: list[Paper],
    range_start: str,
    range_end: str,
    target: str,
    config: dict[str, Any],
    *,
    dry_run: bool = False,
    started_from: str = "arXiv OAI-PMH",
) -> dict[str, Any]:
    """Classify a complete source window and write it only after collection.

    Backfill orchestration can safely collect/checkpoint every source category
    before calling this function, so a transport failure never publishes a
    partially fetched window.
    """
    indexed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    publish_threshold = float(config["thresholds"]["publish"])
    review_threshold = float(config["thresholds"]["review"])
    # Deterministic rules are high-recall candidate prioritization only. New
    # Rules only discover candidates. Curated evidence determines publication.
    accepted: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for paper in papers:
        score, relation, reasons = recognition(paper)
        record = to_record(paper, indexed_at, score, relation, reasons)
        if score >= review_threshold:
            # Full source text is retained only in the non-website review queue so
            # a semantic reviewer can distinguish a new benchmark release from
            # a paper that merely evaluates on an existing benchmark.
            record["reviewContext"] = {
                "abstract": paper.abstract,
                "comments": paper.comments,
            }
            record["candidatePriority"] = "high" if score >= publish_threshold else "normal"
            review.append(record)

    current = read_json(DATA_PATH)
    previous_latest = str(
        (current.get("manifest") or {}).get("latestReportDate")
        or (current.get("manifest") or {}).get("latestSourceDate")
        or ""
    )
    # Replays do not remove historical canonical records.
    retained = list(current.get("records", []))
    records = apply_curated_overrides(
        upsert(retained, [*accepted, *curated_records()])
    )
    existing_review_payload = read_json(REVIEW_PATH) if REVIEW_PATH.exists() else {"candidates": []}
    excluded_review_sources = {
        str((record.get("source") or {}).get("id") or "")
        for record in [*accepted, *curated_records()]
    }
    persistent_review = persistent_review_candidates(
        existing_review_payload.get("candidates", []),
        review,
        range_start,
        range_end,
        excluded_review_sources,
    )
    manifest = {
        "schemaVersion": config["schema_version"],
        "pipelineVersion": config["pipeline_version"],
        "generatedAt": indexed_at,
        "dataAsOf": range_end,
        "timezone": "UTC",
        "recordCount": len(records),
        "sourceCoverage": ["arXiv OAI-PMH", "reviewed official project sources"],
        "isDemo": False,
        "latestReportDate": max(previous_latest, target),
        "run": {
            "sourceDate": target,
            "sourceWindow": {"from": range_start, "to": range_end},
            "papersFetched": len(papers),
            "accepted": len(accepted),
            "reviewQueued": len(review),
        },
    }
    payload = {"manifest": manifest, "records": records}
    review_payload = {
        "generatedAt": indexed_at,
        "sourceDate": target,
        "sourceWindow": {"from": range_start, "to": range_end},
        "queueMode": "persistent-source-upsert",
        "candidateCount": len(persistent_review),
        "candidates": persistent_review,
    }
    run_payload = {
        "schemaVersion": config["schema_version"],
        "pipelineVersion": config["pipeline_version"],
        "sourceDate": target,
        "sourceWindow": {"from": range_start, "to": range_end},
        "startedFrom": started_from,
        "generatedAt": indexed_at,
        "query": {
            "categories": config["arxiv"]["categories"],
            "firstVersionDate": {"from": range_start, "to": range_end},
        },
        "counts": {"fetched": len(papers), "accepted": len(accepted), "reviewQueued": len(review)},
        "accepted": [
            {
                "benchmarkId": record["id"],
                "name": record["name"],
                "sourceId": record["source"]["id"],
                "sourceUrl": record["source"]["url"],
                "confidence": record["recognitionConfidence"],
                "evidence": record["evidence"]["snippet"],
            }
            for record in accepted
        ],
    }
    result = {"manifest": manifest, "accepted": accepted, "review": persistent_review}
    if dry_run:
        print(json.dumps({"manifest": manifest, "accepted": accepted, "review": persistent_review}, ensure_ascii=False, indent=2))
        return result
    write_json(DATA_PATH, payload)
    write_json(REVIEW_PATH, review_payload)
    run_name = target if range_start == range_end else f"backfill_{range_start}_{range_end}"
    write_json(RUNS_PATH / f"{run_name}.json", run_payload)
    print(
        f"source_window={range_start}..{range_end} fetched={len(papers)} accepted={len(accepted)} "
        f"review={len(review)} total={len(records)}"
    )
    return result


def main() -> None:
    args = parse_args()
    config = read_json(CONFIG_PATH)
    if bool(args.start_date) != bool(args.end_date):
        raise SystemExit("--start-date and --end-date must be provided together")
    if args.date and args.start_date:
        raise SystemExit("use either --date or --start-date/--end-date")
    target = args.date or args.end_date or publication_today().isoformat()
    range_start = args.start_date or target
    range_end = args.end_date or target
    papers: list[Paper] = []
    if args.latest_with_papers:
        start = date.fromisoformat(target)
        for offset in range(max(0, args.lookback_days) + 1):
            candidate_date = (start - timedelta(days=offset)).isoformat()
            papers = fetch_for_date(candidate_date, config)
            if papers:
                target = candidate_date
                range_start = candidate_date
                range_end = candidate_date
                break
    elif args.start_date:
        papers = fetch_for_range(range_start, range_end, config)
    else:
        papers = fetch_for_date(target, config)
    index_papers(
        papers,
        range_start,
        range_end,
        target,
        config,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

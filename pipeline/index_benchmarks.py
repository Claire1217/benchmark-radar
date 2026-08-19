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
import re
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "pipeline" / "config.json"
DATA_PATH = ROOT / "data" / "benchmarks.json"
REVIEW_PATH = ROOT / "data" / "review_queue.json"
RUNS_PATH = ROOT / "data" / "runs"
OAI_URL = "https://oaipmh.arxiv.org/oai"
OAI_NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "raw": "http://arxiv.org/OAI/arXivRaw/",
}

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
    r"(?:an?\s+|the\s+)?(?:new\s+)?(?:\\(?:textbf|emph)\{)?"
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
    )


def request_oai(params: dict[str, str]) -> ET.Element:
    request = Request(
        f"{OAI_URL}?{urlencode(params)}",
        headers={"User-Agent": "BenchmarkRadar/1.0 (https://github.com/Claire1217/benchmark-radar)"},
    )
    with urlopen(request, timeout=90) as response:
        root = ET.fromstring(response.read())
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
    until = min(end + timedelta(days=int(settings["lookahead_days"])), date.today()).isoformat()
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


def evidence_sentence(paper: Paper) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract))
    for sentence in sentences:
        if BENCHMARK_TERMS.search(sentence) and RELEASE_LANGUAGE.search(sentence):
            return sentence[:500]
    for sentence in sentences:
        if BENCHMARK_TERMS.search(sentence):
            return sentence[:500]
    return first_sentence(paper.abstract, 500)


def has_release_evidence(paper: Paper) -> bool:
    """Require release and benchmark evidence in the same source sentence."""
    sentences = re.split(r"(?<=[.!?])\s+", normalize_space(paper.abstract))
    return any(BENCHMARK_TERMS.search(sentence) and RELEASE_LANGUAGE.search(sentence) for sentence in sentences)


def has_named_benchmark_title(title: str) -> bool:
    prefix, separator, subtitle = title.partition(":")
    if not separator or not (2 <= len(prefix.strip()) <= 70):
        return False
    return bool(
        re.search(r"(?:Bench|Benchmark)$", prefix.strip(), re.I)
        or re.search(r"\b(benchmark|evaluation suite|testbed)\b", subtitle, re.I)
    )


def canonical_name(paper: Paper) -> str:
    title = paper.title
    prefix, separator, remainder = title.partition(":")
    if has_named_benchmark_title(title):
        return prefix.strip()
    named = NAMED_BENCHMARK_RE.search(normalize_space(paper.abstract).replace("\\textbf{", ""))
    if named:
        return named.group(1).rstrip("}")
    if separator and 2 <= len(prefix.strip()) <= 70:
        return prefix.strip()
    match = re.search(r"\b([A-Z][A-Za-z0-9+_.-]{2,30}(?:Bench|Benchmark))\b", title)
    return match.group(1) if match else title


def classify_area(paper: Paper) -> str:
    title = paper.title.lower()
    text = f"{paper.title} {evidence_sentence(paper)}".lower()
    if re.search(r"\b(cad|computer-aided design|engineering drawing|mechanical design)\b", text):
        return "Science & Engineering"
    if re.search(r"\b(robot|embodied|manipulation|navigation)\b", text):
        return "Robotics & Embodied AI"
    if re.search(r"\b(agent|tool use|computer use|web navigation|research agent)\b", text):
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
    text = f"{paper.title} {paper.abstract}".lower()
    mapping = [
        (r"\b(rtl|verilog|vhdl|eda|chip design|circuit design|place and route|logic synthesis)\b", "Chip Design & EDA"),
        (r"\b(software engineering|code generation|program repair|repository|compiler|gpu kernel|ptx|tokenizer)\b", "Software & AI Compute"),
        (r"\b(cybersecurity|vulnerability|exploit|malware|intrusion|incident response)\b", "Cybersecurity"),
        (r"\b(theorem|formal proof|mathematical reasoning|olympiad|geometry proof)\b", "Mathematics & Formal Science"),
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
        (r"\b(finance|financial|trading|investment|banking|credit risk)\b", "Finance"),
    ]
    matches = [label for pattern, label in mapping if re.search(pattern, text)]
    return matches[:3] or ["General AI"]


def infer_industry_sectors(domains: list[str]) -> list[str]:
    mapping = {
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
    return values[:3] or ["Evaluation"]


def infer_construction(paper: Paper) -> tuple[str, str]:
    text = paper.abstract.lower()
    if re.search(r"\b(simulator|interactive environment|real-world environment)\b", text):
        return "Interactive Environment", "Unknown"
    if re.search(r"\bsynthetic|programmatically generated|procedurally generated\b", text):
        return "Original Synthetic", "Machine Generated"
    if re.search(r"\baggregate|collection of existing|combine existing\b", text):
        return "Aggregate Existing", "Mixed"
    if re.search(r"\bcurat|filter|re-annotat|post-process|derived from\b", text):
        return "Transform Existing", "Unknown"
    return "Unknown", "Unknown"


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
    reasons: list[str] = []
    score = 0.0
    named_title = has_named_benchmark_title(paper.title)
    if named_title:
        score += 0.5
        reasons.append("named benchmark or evaluation-suite title")
    elif BENCHMARK_TERMS.search(paper.abstract):
        score += 0.1
        reasons.append("benchmark term in abstract")
    same_sentence_release = has_release_evidence(paper)
    if same_sentence_release:
        score += 0.35
        reasons.append("benchmark release stated in one sentence")
    if EVALUATION_LANGUAGE.search(paper.abstract):
        score += 0.15
        reasons.append("evaluation protocol evidence")
    if URL_RE.search(f"{paper.abstract} {paper.comments}"):
        score += 0.1
        reasons.append("public artifact URL")
    if NAMED_BENCHMARK_RE.search(normalize_space(paper.abstract).replace("\\textbf{", "")):
        score += 0.15
        reasons.append("named benchmark release in abstract")
    if not named_title and not same_sentence_release:
        score = min(score, 0.55)
        reasons.append("no explicit benchmark release evidence")
    score = min(score, 1.0)
    decisive_text = f"{paper.title} {evidence_sentence(paper)}"
    if re.search(r"\b(extend|updated version|new version|successor|refresh|rebench)\b", decisive_text, re.I):
        relation = "extends"
    elif AGGREGATION_LANGUAGE.search(decisive_text):
        relation = "aggregates"
    elif same_sentence_release or named_title:
        relation = "introduces"
    else:
        relation = "unclear"
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
        by_source[source_id] = record
    return sorted(by_source.values(), key=lambda item: (item["releasedAt"], item["id"]), reverse=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index new benchmark releases from arXiv OAI-PMH.")
    parser.add_argument("--date", help="First-public-release date in YYYY-MM-DD.")
    parser.add_argument("--start-date", help="Inclusive first-public-release start date.")
    parser.add_argument("--end-date", help="Inclusive first-public-release end date.")
    parser.add_argument("--latest-with-papers", action="store_true", help="Look back to the latest non-empty arXiv date.")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = read_json(CONFIG_PATH)
    if bool(args.start_date) != bool(args.end_date):
        raise SystemExit("--start-date and --end-date must be provided together")
    if args.date and args.start_date:
        raise SystemExit("use either --date or --start-date/--end-date")
    target = args.date or args.end_date or date.today().isoformat()
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

    indexed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    publish_threshold = float(config["thresholds"]["publish"])
    review_threshold = float(config["thresholds"]["review"])
    accepted: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for paper in papers:
        score, relation, reasons = recognition(paper)
        record = to_record(paper, indexed_at, score, relation, reasons)
        if score >= publish_threshold and relation in {"introduces", "extends", "aggregates"}:
            accepted.append(record)
        elif score >= review_threshold:
            review.append(record)

    current = read_json(DATA_PATH)
    retained = [
        record
        for record in current.get("records", [])
        if not (range_start <= str(record.get("releasedAt", "")) <= range_end)
    ]
    records = upsert(retained, accepted)
    manifest = {
        "schemaVersion": config["schema_version"],
        "pipelineVersion": config["pipeline_version"],
        "generatedAt": indexed_at,
        "dataAsOf": range_end,
        "timezone": "UTC",
        "recordCount": len(records),
        "sourceCoverage": ["arXiv OAI-PMH"],
        "isDemo": False,
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
        "candidates": review,
    }
    run_payload = {
        "schemaVersion": config["schema_version"],
        "pipelineVersion": config["pipeline_version"],
        "sourceDate": target,
        "sourceWindow": {"from": range_start, "to": range_end},
        "startedFrom": "arXiv OAI-PMH",
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
    if args.dry_run:
        print(json.dumps({"manifest": manifest, "accepted": accepted, "review": review}, ensure_ascii=False, indent=2))
        return
    write_json(DATA_PATH, payload)
    write_json(REVIEW_PATH, review_payload)
    run_name = target if range_start == range_end else f"backfill_{range_start}_{range_end}"
    write_json(RUNS_PATH / f"{run_name}.json", run_payload)
    print(
        f"source_window={range_start}..{range_end} fetched={len(papers)} accepted={len(accepted)} "
        f"review={len(review)} total={len(records)}"
    )


if __name__ == "__main__":
    main()

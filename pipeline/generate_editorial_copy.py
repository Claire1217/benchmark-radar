#!/usr/bin/env python3
"""Review benchmark candidates and generate public copy with DeepSeek."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/benchmarks.json"
REVIEW_PATH = ROOT / "data/review_queue.json"
CURATED_PATH = ROOT / "data/curated_records.json"
OUTPUT_PATH = ROOT / "data/editorial_copy.json"
API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash"
COPY_POLICY_VERSION = "2026-08-21.1"
ADMISSION_POLICY_VERSION = "2026-08-23.1"
ATOM = "{http://www.w3.org/2005/Atom}"


class ProviderError(RuntimeError):
    pass


class ReviewValidationError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_abstracts(source_ids: list[str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for start in range(0, len(source_ids), 40):
        batch = source_ids[start:start + 40]
        query = ",".join(batch)
        request = Request(
            f"https://export.arxiv.org/api/query?id_list={query}&max_results={len(batch)}",
            headers={"User-Agent": "benchmark-radar/1.0 (public research index)"},
        )
        root = None
        for attempt in range(3):
            try:
                with urlopen(request, timeout=45) as response:
                    root = ET.fromstring(response.read())
                break
            except (HTTPError, URLError, TimeoutError, ET.ParseError):
                if attempt < 2:
                    time.sleep(2 ** attempt)
        if root is None:
            continue
        for entry in root.findall(f"{ATOM}entry"):
            source_id = (entry.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1].split("v", 1)[0]
            summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
            if source_id and summary:
                output[source_id] = html.unescape(summary)
        if start + 40 < len(source_ids):
            time.sleep(0.5)
    return output


def artifact_excerpt(kind: str, url: str) -> dict[str, Any]:
    """Read a small official GitHub/Hugging Face artifact excerpt."""
    parsed = urlparse(url)
    fetch_url = url
    headers = {"User-Agent": "benchmark-radar/1.0 (public research index)"}
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc == "github.com" and len(parts) >= 2:
        fetch_url = f"https://api.github.com/repos/{parts[0]}/{parts[1]}/readme"
        headers["Accept"] = "application/vnd.github.raw+json"
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    elif parsed.netloc == "huggingface.co" and len(parts) >= 3 and parts[0] == "datasets":
        fetch_url = f"https://huggingface.co/datasets/{parts[1]}/{parts[2]}/raw/main/README.md"
    try:
        with urlopen(Request(fetch_url, headers=headers), timeout=30) as response:
            raw = response.read(12000).decode("utf-8", errors="replace")
        clean = " ".join(re.sub(r"<[^>]+>", " ", raw).split())[:6000]
        return {"kind": kind, "url": url, "status": "available", "excerpt": clean}
    except (HTTPError, URLError, TimeoutError):
        return {"kind": kind, "url": url, "status": "unverified", "excerpt": ""}


def response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if choices:
        content = (choices[0].get("message") or {}).get("content")
        if isinstance(content, str) and content.strip():
            return content
    raise ProviderError("DeepSeek response did not contain message content")


def publisher_identity_is_distinct(name: str, source_url: str, benchmark_name: str = "") -> bool:
    """Reject benchmark, repository, or dataset names masquerading as teams."""
    normalize = lambda value: re.sub(r"[^a-z0-9]+", "", value.casefold())
    normalized_name = normalize(name)
    if not normalized_name:
        return False
    path_parts = [part for part in urlparse(source_url).path.split("/") if part]
    resource_name = path_parts[-1] if path_parts else ""
    return normalized_name not in {normalize(benchmark_name), normalize(resource_name)}


def call_deepseek(records: list[dict[str, Any]], model: str, api_key: str) -> list[dict[str, Any]]:
    schema = {
        "type": "object",
        "properties": {
            "records": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sourceId": {"type": "string"},
                        "decision": {"type": "string", "enum": ["publish", "defer", "exclude"]},
                        "benchmarkMode": {
                            "type": "string",
                            "enum": ["score_submission", "public_reusable", "viewpoint_probe", "uses_existing", "not_benchmark", "unclear"],
                        },
                        "stableScoringContract": {"type": "boolean"},
                        "publicReusePath": {"type": "boolean"},
                        "description": {"type": "string", "maxLength": 220},
                        "whyItMatters": {"type": "string", "maxLength": 320},
                        "decisionReason": {"type": "string", "maxLength": 320},
                        "publishers": {
                            "type": "array",
                            "maxItems": 2,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "maxLength": 80},
                                    "organizationType": {"type": "string", "enum": ["company-research-lab", "academic-lab", "benchmark-organization", "community"]},
                                    "sourceUrl": {"type": "string"},
                                },
                                "required": ["name", "organizationType", "sourceUrl"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["sourceId", "decision", "benchmarkMode", "stableScoringContract", "publicReusePath", "description", "whyItMatters", "decisionReason", "publishers"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["records"],
        "additionalProperties": False,
    }
    instructions = (
        "Act as the admission editor for Benchmark Radar. Decide from meaning, never from keyword presence. "
        "Publish only a named benchmark that defines a repeatable evaluation object and comparable scoring contract, "
        "and provides a credible public path for other teams to run or inspect it. "
        "An explicit source statement that the task suite, evaluators, scored submissions, data, or code are released counts as a public path even when the source metadata does not expose a separate project URL. "
        "A missing direct code, data, or project link lowers readiness; it must not by itself turn a released benchmark with a stable evaluation and scoring contract into defer. "
        "score_submission means an ongoing public benchmark intended for model comparison; public_reusable means a fixed public dataset/protocol usable by other teams. "
        "A viewpoint_probe primarily exists to support one paper's finding and lacks a standalone public comparison path; exclude it from the public site. "
        "uses_existing and not_benchmark must also be excluded. Defer when evidence or artifacts are unclear. "
        "Public attention, author prestige, and the word benchmark must never change this decision. "
        "Then write neutral editorial copy in third person. Description states only what is evaluated: the evaluation object, "
        "task or environment, and the main capability or scoring setup when known. It must not explain why the benchmark was created. "
        "Why it matters explains the evaluation gap and practical decision value. "
        "Publishers are the organizations or benchmark teams responsible for releasing the benchmark, not every author affiliation and not model adopters. "
        "A benchmark name, repository name, dataset name, or project-page title is not a publisher. "
        "Only return a publisher when its identity is supported by an official link supplied in the input; otherwise return an empty list. "
        "Do not write We, Our, This paper, introduces, presents, hype, rankings, or unsupported facts. "
        "Use only the supplied paper text and official links. Return one item for every sourceId."
    )
    instructions += " Return only valid json matching this schema: " + json.dumps(schema, ensure_ascii=False)
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(records, ensure_ascii=False)},
        ],
        "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "max_tokens": 8192,
        "stream": False,
    }
    request = Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=120) as response:
                parsed = json.loads(response_text(json.loads(response.read())))
                records = parsed.get("records")
                if not isinstance(records, list):
                    raise ProviderError("DeepSeek response did not contain a records array")
                return records
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise ProviderError(f"DeepSeek request failed with HTTP {exc.code}") from None
        except (TimeoutError, URLError, json.JSONDecodeError, ProviderError):
            if attempt == 2:
                raise ProviderError("DeepSeek request failed after retries") from None
        time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def validate_copy(sources: dict[str, dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    if {row.get("sourceId") for row in rows} != set(sources):
        raise ReviewValidationError("DeepSeek output did not cover the requested source IDs exactly")
    first_person = re.compile(r"\b(?:we|our|ours|us)\b", re.I)
    author_voice = re.compile(r"\b(?:this paper|we introduce|we present)\b", re.I)
    for row in rows:
        for field in ("description", "whyItMatters"):
            value = " ".join(str(row.get(field, "")).split())
            if not value or first_person.search(value) or author_voice.search(value):
                raise ReviewValidationError(f"Invalid third-person copy for {row.get('sourceId')}:{field}")
            row[field] = value
        required = {
            "decision", "benchmarkMode", "stableScoringContract", "publicReusePath", "decisionReason"
        }
        if any(field not in row for field in required):
            raise ReviewValidationError(f"Incomplete semantic decision for {row.get('sourceId')}")
        allowed_urls = {
            str(url).rstrip("/"): str(url)
            for url in (sources[row["sourceId"]].get("officialLinks") or {}).values()
        }
        supported_publishers = []
        for publisher in row.get("publishers", []):
            matched_url = allowed_urls.get(str(publisher.get("sourceUrl", "")).rstrip("/"))
            if not matched_url or not publisher_identity_is_distinct(
                str(publisher.get("name", "")), matched_url
            ):
                continue
            publisher["sourceUrl"] = matched_url
            publisher["role"] = "benchmark-publisher"
            supported_publishers.append(publisher)
        row["publishers"] = supported_publishers


def input_hash(row: dict[str, Any], policy_version: str = COPY_POLICY_VERSION) -> str:
    versioned = {"policyVersion": policy_version, "source": row}
    return hashlib.sha256(json.dumps(versioned, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def selection_fingerprint(record: dict[str, Any], policy_version: str = COPY_POLICY_VERSION) -> str:
    """Cheap local fingerprint used to resume before fetching remote artifacts."""
    source = record.get("source") or {}
    local = {
        "policyVersion": policy_version,
        "sourceId": source.get("id"),
        "sourceUpdatedAt": source.get("updatedAt") or record.get("sourceUpdatedAt"),
        "title": record.get("paperTitle") or record.get("name"),
        "links": record.get("links") or {},
        "abstract": (record.get("reviewContext") or {}).get("abstract"),
        "comments": (record.get("reviewContext") or {}).get("comments"),
    }
    return hashlib.sha256(json.dumps(local, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write_editorial_copy(payload: dict[str, Any]) -> None:
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def review_batch(batch: list[dict[str, Any]], model: str, api_key: str) -> list[dict[str, Any]]:
    """Retry malformed multi-record output one record at a time."""
    try:
        rows = call_deepseek(batch, model, api_key)
        validate_copy({item["sourceId"]: item for item in batch}, rows)
        return rows
    except ReviewValidationError:
        if len(batch) == 1:
            print(f"editorial_copy_invalid_output source={batch[0]['sourceId']} deferred=true")
            return []
        recovered: list[dict[str, Any]] = []
        for source in batch:
            try:
                rows = call_deepseek([source], model, api_key)
                validate_copy({source["sourceId"]: source}, rows)
                recovered.extend(rows)
            except ReviewValidationError:
                print(f"editorial_copy_invalid_output source={source['sourceId']} deferred=true")
        return recovered


def publishable(row: dict[str, Any]) -> bool:
    return (
        row.get("decision") == "publish"
        and row.get("benchmarkMode") in {"score_submission", "public_reusable"}
        and row.get("stableScoringContract") is True
        and row.get("publicReusePath") is True
    )


def upsert_curated(candidates: list[dict[str, Any]], decisions: list[dict[str, Any]], now: str, model: str) -> int:
    payload = read_json(CURATED_PATH) if CURATED_PATH.exists() else {"schemaVersion": "1.0", "records": []}
    by_source = {str((record.get("source") or {}).get("id") or ""): record for record in payload.get("records", [])}
    candidate_by_source = {str((record.get("source") or {}).get("id") or ""): record for record in candidates}
    published = 0
    for decision in decisions:
        if not publishable(decision):
            continue
        source_id = decision["sourceId"]
        source = candidate_by_source[source_id]
        record = {key: value for key, value in source.items() if key not in {"reviewContext", "candidatePriority"}}
        record["description"] = decision["description"]
        record["whyItMatters"] = decision["whyItMatters"]
        record["oneLine"] = decision["description"]
        record["evaluationMode"] = decision["benchmarkMode"]
        if decision.get("publishers"):
            record["publishers"] = decision["publishers"]
        record["displayEligible"] = True
        record["capabilities"] = [value for value in record.get("capabilities", []) if value != "Evaluation"]
        record["curation"] = {
            "state": "ai-reviewed",
            "reviewedAt": now,
            "model": model,
            "decisionReason": decision["decisionReason"],
        }
        by_source[source_id] = record
        published += 1
    payload["records"] = sorted(by_source.values(), key=lambda item: (item.get("releasedAt", ""), item.get("id", "")), reverse=True)
    CURATED_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return published


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Description and Why it matters with DeepSeek.")
    parser.add_argument("--ids", help="Comma-separated arXiv source IDs")
    parser.add_argument("--released-on", help="Only records released on YYYY-MM-DD")
    parser.add_argument("--review-queue", action="store_true", help="Review queued candidates and publish eligible records")
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--model", default=os.environ.get("DEEPSEEK_COPY_MODEL", DEFAULT_MODEL))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = read_json(REVIEW_PATH if args.review_queue else DATA_PATH)
    existing = read_json(OUTPUT_PATH) if OUTPUT_PATH.exists() else {"schemaVersion": "1.0", "bySourceId": {}}
    requested = {item.strip() for item in (args.ids or "").split(",") if item.strip()}
    records = [
        record for record in payload.get("candidates" if args.review_queue else "records", [])
        if (not requested or str(record["source"]["id"]) in requested)
        and (not args.released_on or record.get("releasedAt") == args.released_on)
    ]
    policy_version = ADMISSION_POLICY_VERSION if args.review_queue else COPY_POLICY_VERSION
    records = [
        record for record in records
        if existing.get("bySourceId", {}).get(str(record["source"]["id"]), {}).get("selectionFingerprint")
        != selection_fingerprint(record, policy_version)
    ]
    if args.limit > 0:
        records = records[:args.limit]
    if not records:
        print("editorial_copy_candidates=0")
        return
    source_ids = [str(record["source"]["id"]) for record in records]
    source_records = {str(record["source"]["id"]): record for record in records}
    abstracts = {
        str((record.get("source") or {}).get("id")): str((record.get("reviewContext") or {}).get("abstract") or "")
        for record in records
    }
    missing = [
        source_id for source_id in source_ids
        if not abstracts.get(source_id)
        and source_records[source_id].get("source", {}).get("type") == "arxiv"
    ]
    if missing:
        abstracts.update(fetch_abstracts(missing))
    source_rows = []
    missing_source_ids: list[str] = []
    for record in records:
        source_id = str(record["source"]["id"])
        abstract = abstracts.get(source_id)
        if not abstract:
            fallback = str(((record.get("evidence") or {}).get("snippet")) or "").strip()
            if not fallback:
                missing_source_ids.append(source_id)
                continue
            abstract = fallback
        source_rows.append({
            "sourceId": source_id,
            "title": record.get("paperTitle") or record["name"],
            "abstract": abstract,
            "comments": str((record.get("reviewContext") or {}).get("comments") or ""),
            "officialLinks": {key: value for key, value in (record.get("links") or {}).items() if value},
            "artifactEvidence": [
                artifact_excerpt(kind, url)
                for kind, url in (record.get("links") or {}).items()
                if kind in {"code", "data"} and url
            ],
        })
    if missing_source_ids:
        print(f"editorial_copy_missing_source={len(missing_source_ids)} deferred=true")
    source_rows = [
        row for row in source_rows
        if (existing.get("bySourceId", {}).get(row["sourceId"], {}).get("inputHash") != input_hash(row, policy_version))
    ]
    if not source_rows:
        print("deepseek_review_candidates=0 unchanged=true")
        return
    if args.dry_run:
        print(f"editorial_copy_candidates={len(source_rows)} dry_run=true")
        return
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")
    generated: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    source_by_id = {item["sourceId"]: item for item in source_rows}
    record_by_id = {str(record["source"]["id"]): record for record in records}
    published = 0
    for start in range(0, len(source_rows), max(1, args.batch_size)):
        batch = source_rows[start:start + max(1, args.batch_size)]
        rows = review_batch(batch, args.model, api_key)
        generated.extend(rows)
        for row in rows:
            source = source_by_id[row["sourceId"]]
            existing["bySourceId"][row["sourceId"]] = {
                "decision": row["decision"],
                "benchmarkMode": row["benchmarkMode"],
                "stableScoringContract": row["stableScoringContract"],
                "publicReusePath": row["publicReusePath"],
                "description": row["description"],
                "whyItMatters": row["whyItMatters"],
                "decisionReason": row["decisionReason"],
                "publishers": row.get("publishers", []),
                "model": args.model,
                "policyVersion": policy_version,
                "generatedAt": now,
                "inputHash": input_hash(source, policy_version),
                "selectionFingerprint": selection_fingerprint(record_by_id[row["sourceId"]], policy_version),
            }
        write_editorial_copy(existing)
        if args.review_queue:
            published += upsert_curated(records, rows, now, args.model)
    print(f"deepseek_reviewed={len(generated)} published={published} model={args.model}")


if __name__ == "__main__":
    main()

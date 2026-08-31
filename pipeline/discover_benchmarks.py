#!/usr/bin/env python3
"""Collect one dated benchmark candidate pool from public primary sources."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
import re
import time as time_module
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import index_benchmarks as arxiv


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "data" / "review_queue.json"
RUNS_PATH = ROOT / "data" / "runs"
USER_AGENT = "BenchmarkRadar/1.0 (https://github.com/Claire1217/benchmark-radar)"
BENCHMARK_WORD = re.compile(r"\b(?:benchmark|bench|evaluation suite|testbed|challenge set)\b", re.I)
AI_CONTEXT = re.compile(
    r"\b(?:AI|ML|LLM|VLM|agent|language model|machine learning|artificial intelligence|"
    r"computer vision|multimodal|reasoning|robot|humanoid|embodied|foundation model|"
    r"code generation|speech|NLP|scientific software)\b",
    re.I,
)
EVALUATION_OBJECT = re.compile(
    r"\b(?:tasks?|datasets?|instances?|questions?|environments?|scenarios?|samples?|"
    r"trajectories|test set|challenge|episodes?|repositories|cases?)\b",
    re.I,
)
SCORING_CONTRACT = re.compile(
    r"\b(?:metrics?|scores?|scoring|evaluator|judge|verifier|accuracy|pass@\d+|"
    r"f1|success rate|leaderboard|baseline|evaluation protocol)\b",
    re.I,
)
GENERIC_NAMES = {"bench", "benchmark", "benchmarks", "evaluation", "testbed"}


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    request_headers.update(headers or {})
    request = Request(url, headers=request_headers)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45) as response:
                return json.loads(response.read())
        except HTTPError as error:
            if attempt == 2 or (error.code != 429 and not 500 <= error.code <= 599):
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time_module.sleep(2**attempt)
    raise RuntimeError("JSON source retry loop ended without a response")


def fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "text/plain"}
    request_headers.update(headers or {})
    with urlopen(Request(url, headers=request_headers), timeout=30) as response:
        return response.read(24000).decode("utf-8", errors="replace")


def clean(value: Any, limit: int = 6000) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", str(value or "")).split())[:limit]


def generic_artifact_name(value: str) -> bool:
    return re.sub(r"[^a-z0-9]+", "", value.casefold()) in GENERIC_NAMES


def iso_day(value: str | int | None) -> str:
    if isinstance(value, int):
        return datetime.fromtimestamp(value / 1000, timezone.utc).date().isoformat()
    return str(value or "")[:10]


def arxiv_enabled_for_date(target: str) -> bool:
    """arXiv announces Sunday through Thursday; Friday/Saturday are external-only."""
    return date.fromisoformat(target).weekday() not in {4, 5}


def arxiv_query_dates(target: str) -> list[str]:
    """Recheck a rolling three-day window so a 09:00 run can recover late feeds."""
    source_day = date.fromisoformat(target)
    return [(source_day - timedelta(days=offset)).isoformat() for offset in (2, 1, 0)]


def publication_batch_dates(target: str) -> list[str]:
    """Monday's publication batch covers Friday, Saturday, and Sunday."""
    source_day = date.fromisoformat(target)
    offsets = (2, 1, 0) if source_day.weekday() == 6 else (0,)
    return [(source_day - timedelta(days=offset)).isoformat() for offset in offsets]


def has_reviewable_evidence(value: str) -> bool:
    """Coarse evidence gate for deterministic admission and automated audit."""
    return bool(
        BENCHMARK_WORD.search(value)
        and AI_CONTEXT.search(value)
        and EVALUATION_OBJECT.search(value)
        and SCORING_CONTRACT.search(value)
    )


def github_candidates(target: str) -> list[dict[str, Any]]:
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    queries = [
        f"benchmark in:name created:{target}",
        f"benchmark in:description created:{target} topic:machine-learning",
        f"benchmark in:description created:{target} topic:artificial-intelligence",
        f"benchmark in:description created:{target} topic:llm",
        f"benchmark in:description created:{target} topic:robotics",
    ]
    by_id: dict[str, dict[str, Any]] = {}
    for query in queries:
        url = "https://api.github.com/search/repositories?" + urlencode(
            {"q": query, "sort": "updated", "order": "desc", "per_page": 100}
        )
        for item in (fetch_json(url, headers).get("items") or []):
            source_id = str(item.get("full_name") or "")
            text = " ".join([
                str(item.get("name") or ""), str(item.get("description") or ""),
                " ".join(item.get("topics") or []),
            ])
            if (
                not source_id or generic_artifact_name(str(item.get("name") or ""))
                or item.get("fork") or item.get("archived") or item.get("disabled")
                or iso_day(item.get("created_at")) != target
                or not BENCHMARK_WORD.search(text) or not AI_CONTEXT.search(text)
            ):
                continue
            try:
                readme = clean(fetch_text(
                    f"https://api.github.com/repos/{source_id}/readme",
                    {**headers, "Accept": "application/vnd.github.raw+json"},
                ))
            except (HTTPError, URLError, TimeoutError):
                continue
            evidence = clean(f"{text} {readme}")
            if not has_reviewable_evidence(evidence):
                continue
            by_id[source_id] = {
                "type": "github",
                "id": f"github:{source_id.casefold()}",
                "title": str(item.get("name") or source_id),
                "description": evidence,
                "releasedAt": target,
                "updatedAt": str(item.get("updated_at") or item.get("created_at") or ""),
                "url": str(item.get("html_url") or f"https://github.com/{source_id}"),
                "publicSignals": {"githubStars": int(item.get("stargazers_count") or 0)},
                "links": {
                    "code": str(item.get("html_url") or f"https://github.com/{source_id}"),
                    "project": str(item.get("homepage") or "") or None,
                },
                "authors": [str((item.get("owner") or {}).get("login") or "")],
            }
    return list(by_id.values())


def huggingface_candidates(target: str) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for search in ("benchmark", "bench"):
        url = "https://huggingface.co/api/datasets?" + urlencode(
            {"search": search, "sort": "createdAt", "direction": "-1", "limit": 500, "full": "true"}
        )
        for item in fetch_json(url):
            dataset_id = str(item.get("id") or "")
            description = clean(item.get("description"))
            text = " ".join([dataset_id, description, " ".join(item.get("tags") or [])])
            if (
                not dataset_id or generic_artifact_name(dataset_id.rsplit("/", 1)[-1])
                or iso_day(item.get("createdAt")) != target
                or not has_reviewable_evidence(text)
            ):
                continue
            dataset_url = f"https://huggingface.co/datasets/{dataset_id}"
            by_id[dataset_id.casefold()] = {
                "type": "huggingface",
                "id": f"huggingface:{dataset_id.casefold()}",
                "title": dataset_id.rsplit("/", 1)[-1],
                "description": description or f"Public Hugging Face dataset artifact: {dataset_id}.",
                "releasedAt": target,
                "updatedAt": str(item.get("lastModified") or item.get("createdAt") or ""),
                "url": dataset_url,
                "publicSignals": {
                    "hfDatasetDownloads": int(item.get("downloads") or 0),
                    "hfDatasetLikes": int(item.get("likes") or 0),
                },
                "links": {"data": dataset_url},
                "authors": [str(item.get("author") or dataset_id.split("/", 1)[0])],
            }
    return list(by_id.values())


def openreview_value(content: dict[str, Any], key: str) -> Any:
    value = content.get(key)
    return value.get("value") if isinstance(value, dict) and "value" in value else value


def openreview_candidates(target: str) -> list[dict[str, Any]]:
    start = datetime.combine(date.fromisoformat(target), time.min, timezone.utc)
    end = datetime.combine(date.fromisoformat(target), time.max, timezone.utc)
    url = "https://api2.openreview.net/notes?" + urlencode({
        "mintcdate": int(start.timestamp() * 1000),
        "maxcdate": int(end.timestamp() * 1000),
        "limit": 1000,
        "sort": "cdate:desc",
    })
    headers: dict[str, str] = {}
    if os.environ.get("OPENREVIEW_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['OPENREVIEW_TOKEN']}"
    output: list[dict[str, Any]] = []
    for note in fetch_json(url, headers).get("notes", []):
        content = note.get("content") or {}
        title = clean(openreview_value(content, "title"), 500)
        abstract = clean(openreview_value(content, "abstract"))
        text = f"{title} {abstract}"
        if not title or not abstract or not has_reviewable_evidence(text):
            continue
        note_id = str(note.get("id") or "")
        forum_id = str(note.get("forum") or note_id)
        if not note_id:
            continue
        forum_url = f"https://openreview.net/forum?id={forum_id}"
        authors = openreview_value(content, "authors") or []
        output.append({
            "type": "openreview",
            "id": f"openreview:{note_id}",
            "title": title,
            "description": abstract,
            "releasedAt": target,
            "updatedAt": datetime.fromtimestamp(int(note.get("cdate") or 0) / 1000, timezone.utc).isoformat(),
            "url": forum_url,
            "links": {"report": forum_url},
            "authors": [str(author) for author in authors] if isinstance(authors, list) else [],
        })
    return output


def candidate_record(item: dict[str, Any], indexed_at: str, config: dict[str, Any]) -> dict[str, Any]:
    paper = arxiv.Paper(
        arxiv_id=item["id"],
        title=item["title"],
        authors=[author for author in item.get("authors", []) if author],
        abstract=item["description"],
        categories=["cs.AI"],
        primary_category="cs.AI",
        released_at=item["releasedAt"],
        updated_at=item["updatedAt"],
        entry_url=item["url"],
        pdf_url="",
        comments="",
    )
    score, relation, reasons = arxiv.recognition(paper)
    score = max(score, float(config["thresholds"]["review"]))
    record = arxiv.to_record(paper, indexed_at, score, relation, [f"discovered via {item['type']}", *reasons])
    record["links"].update({key: value for key, value in item.get("links", {}).items() if value})
    record["links"] = {key: value for key, value in record["links"].items() if value}
    record["readiness"] = "Runnable" if record["links"].get("code") else "Inspectable" if record["links"].get("data") else "Paper only"
    record["source"] = {
        "type": item["type"], "id": item["id"], "url": item["url"],
        "title": item["title"], "authors": paper.authors, "categories": [],
    }
    if item.get("publicSignals"):
        record["source"]["publicSignals"] = item["publicSignals"]
    record["sourceUpdatedAt"] = item["updatedAt"]
    record["reviewContext"] = {"abstract": item["description"], "comments": ""}
    record["candidatePriority"] = "normal"
    record["dataStatus"] = "primary-source-candidate"
    record["discoverySources"] = [{"type": item["type"], "id": item["id"], "url": item["url"]}]
    return record


def normalized_url(value: str | None) -> str:
    return re.sub(r"[?#].*$", "", str(value or "").rstrip("/").casefold())


def identity_urls(record: dict[str, Any]) -> set[str]:
    values = [str((record.get("source") or {}).get("url") or ""), *(record.get("links") or {}).values()]
    return {normalized_url(value) for value in values if value}


def name_key(record: dict[str, Any]) -> str:
    value = re.sub(r"[^a-z0-9]+", "", str(record.get("name") or "").casefold())
    return "" if value in GENERIC_NAMES or len(value) < 5 else value


def same_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if str((left.get("source") or {}).get("id")) == str((right.get("source") or {}).get("id")):
        return True
    if identity_urls(left) & identity_urls(right):
        return True
    return bool(name_key(left) and name_key(left) == name_key(right))


def merge_candidate(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in (source.get("links") or {}).items():
        if value and not (target.get("links") or {}).get(key):
            target.setdefault("links", {})[key] = value
    seen = {(item.get("type"), item.get("id")) for item in target.get("discoverySources", [])}
    for item in source.get("discoverySources", []):
        if (item.get("type"), item.get("id")) not in seen:
            target.setdefault("discoverySources", []).append(item)


def merge_review_queue(
    incoming: list[dict[str, Any]], target: str, range_start: str,
    failures: dict[str, str],
) -> tuple[int, int]:
    queue = read_json(REVIEW_PATH, {"candidates": []})
    candidates = list(queue.get("candidates", []))
    known = read_json(arxiv.DATA_PATH, {"records": []}).get("records", [])
    known += arxiv.curated_records()
    added = duplicates = 0
    for record in incoming:
        match = next((item for item in candidates if same_identity(item, record)), None)
        if match:
            merge_candidate(match, record)
            duplicates += 1
            continue
        if any(same_identity(item, record) for item in known):
            duplicates += 1
            continue
        candidates.append(record)
        added += 1
    candidates.sort(key=lambda item: (item.get("releasedAt", ""), item.get("id", "")), reverse=True)
    queue.update({
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sourceDate": target,
        "sourceWindow": {"from": range_start, "to": target},
        "queueMode": "persistent-multi-source-upsert",
        "candidateCount": len(candidates),
        "sourceCoverage": ["arxiv", "github", "huggingface", "openreview"],
        "sourceFailures": failures,
        "candidates": candidates,
    })
    arxiv.write_json(REVIEW_PATH, queue)
    return added, duplicates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover one dated multi-source benchmark candidate pool.")
    parser.add_argument("--date", required=True, help="Source first-public date in YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target = date.fromisoformat(args.date).isoformat()
    config = arxiv.read_json(arxiv.CONFIG_PATH)
    failures: dict[str, str] = {}
    arxiv_count = 0
    arxiv_mode = "oai"
    query_dates = arxiv_query_dates(target)
    batch_dates = publication_batch_dates(target)
    batch_start = batch_dates[0]
    if query_dates:
        try:
            # One range request per arXiv category is materially faster and
            # less failure-prone than repeating every category for each day.
            papers = arxiv.fetch_for_range(query_dates[0], query_dates[-1], config)
            arxiv_count = len(papers)
            if not args.dry_run:
                arxiv.index_papers(
                    papers, batch_start, target, target, config,
                    started_from="unified discovery",
                )
        except (HTTPError, URLError, TimeoutError, RuntimeError):
            try:
                papers = arxiv.fetch_for_range_atom(query_dates[0], query_dates[-1], config)
                arxiv_count = len(papers)
                arxiv_mode = "atom-fallback"
                if not args.dry_run:
                    arxiv.index_papers(
                        papers, batch_start, target, target, config,
                        started_from="arXiv Atom API fallback",
                    )
            except (HTTPError, URLError, TimeoutError, RuntimeError) as fallback_error:
                failures["arxiv"] = type(fallback_error).__name__
                if not args.dry_run:
                    # External sources can still publish a valid dated batch. Keep
                    # the failed arXiv source explicit instead of leaving an old
                    # source window in the canonical manifest.
                    arxiv.index_papers(
                        [], batch_start, target, target, config,
                        started_from="arXiv unavailable; external sources only",
                    )
    elif not args.dry_run:
        arxiv.index_papers(
            [], batch_start, target, target, config,
            started_from="external-only source day",
        )

    indexed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    adapters: list[tuple[str, Callable[[str], list[dict[str, Any]]]]] = [
        ("github", github_candidates), ("huggingface", huggingface_candidates),
        ("openreview", openreview_candidates),
    ]
    raw: list[dict[str, Any]] = []
    counts: dict[str, Any] = {
        "arxiv": arxiv_count,
        "arxivMode": arxiv_mode,
        "arxivQueryDates": query_dates,
        "publicationBatchDates": batch_dates,
    }
    for name, adapter in adapters:
        try:
            rows = [record for source_day in batch_dates for record in adapter(source_day)]
            counts[name] = len(rows)
            raw.extend(rows)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            failures[name] = type(error).__name__
            counts[name] = 0
    records = [candidate_record(item, indexed_at, config) for item in raw]
    if args.dry_run:
        print(json.dumps({
            "sourceDate": target,
            "counts": counts,
            "failures": failures,
            "candidateCount": len(records),
            "candidates": [
                {"name": record["name"], "source": record["source"]["type"], "url": record["source"]["url"]}
                for record in records[:25]
            ],
        }, ensure_ascii=False, indent=2))
        return
    added, duplicates = merge_review_queue(records, target, batch_start, failures)
    run_path = RUNS_PATH / f"{target}.json"
    run = read_json(run_path, {"sourceDate": target, "generatedAt": indexed_at, "counts": {}})
    run["externalDiscovery"] = {"counts": counts, "failures": failures, "added": added, "duplicates": duplicates}
    arxiv.write_json(run_path, run)
    print(f"source_date={target} counts={counts} added={added} duplicates={duplicates} failures={failures}")


if __name__ == "__main__":
    main()

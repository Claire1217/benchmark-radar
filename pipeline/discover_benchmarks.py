#!/usr/bin/env python3
"""Collect one dated benchmark candidate pool from public primary sources."""

from __future__ import annotations

import argparse
import copy
from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
import re
import time as time_module
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import index_benchmarks as arxiv
import source_coverage


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "data" / "review_queue.json"
RUNS_PATH = ROOT / "data" / "runs"
COVERAGE_PATH = ROOT / "data" / "source_coverage.json"
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


def homepage_url(value: Any) -> str | None:
    """A GitHub homepage is free text; keep it only when it is a web URL.

    Owners type topics or bare domains there, and one non-URL link fails
    validate_data.py for the whole daily publish.
    """
    text = str(value or "").strip()
    if text and "://" not in text and re.fullmatch(r"[\w.-]+\.[a-z]{2,}(?:/\S*)?", text, re.I):
        text = "https://" + text
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc and not re.search(r"\s", text) else None


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
        items = []
        for page in range(1, 11):
            url = "https://api.github.com/search/repositories?" + urlencode(
                {"q": query, "sort": "updated", "order": "desc", "per_page": 100, "page": page}
            )
            result = fetch_json(url, headers)
            total = result.get("total_count")
            if result.get("incomplete_results") or not isinstance(total, int) or total > 1000:
                raise arxiv.IncompleteHarvestError("GitHub search incomplete, missing total, or exceeds 1000 results")
            rows = result.get("items") or []
            items.extend(rows)
            if len(items) >= total:
                break
            if not rows:
                raise arxiv.IncompleteHarvestError("GitHub pagination ended before total_count")
        for item in items:
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
            except (HTTPError, URLError, TimeoutError) as error:
                raise arxiv.IncompleteHarvestError(f"GitHub README unavailable: {source_id}") from error
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
                    "project": homepage_url(item.get("homepage")),
                },
                "authors": [str((item.get("owner") or {}).get("login") or "")],
            }
    return list(by_id.values())


def fetch_json_page(url: str) -> tuple[Any, str | None]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=45) as response:
        payload = json.loads(response.read())
        link = response.headers.get("Link", "")
    match = re.search(r'<([^>]+)>;\s*rel="?next"?', link)
    return payload, match.group(1) if match else None


def huggingface_pages(url: str, target: str):
    seen = set()
    for _ in range(40):
        if url in seen or urlparse(url).netloc != "huggingface.co":
            raise arxiv.IncompleteHarvestError("Invalid or repeated Hugging Face pagination URL")
        seen.add(url)
        rows, next_url = fetch_json_page(url)
        if not isinstance(rows, list):
            raise arxiv.IncompleteHarvestError("Hugging Face response is not a dataset list")
        yield from rows
        # The API sorts by creation descending. Once strictly older than this
        # day, all results on the target day have been traversed.
        dates = [iso_day(row.get("createdAt")) for row in rows]
        if dates and all(dates) and min(dates) < target:
            return
        if not next_url:
            if len(rows) >= 500:
                raise arxiv.IncompleteHarvestError("Hugging Face limit reached without next-page link")
            return
        if not rows:
            raise arxiv.IncompleteHarvestError("Empty Hugging Face page with continuation")
        url = next_url
    raise arxiv.IncompleteHarvestError("Hugging Face pagination budget exhausted")


def huggingface_candidates(target: str) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for search in ("benchmark", "bench"):
        url = "https://huggingface.co/api/datasets?" + urlencode(
            {"search": search, "sort": "createdAt", "direction": "-1", "limit": 500, "full": "true"}
        )
        for item in huggingface_pages(url, target):
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
    params = {
        "mintcdate": int(start.timestamp() * 1000),
        "maxcdate": int(end.timestamp() * 1000), "limit": 1000, "sort": "cdate:desc",
    }
    headers: dict[str, str] = {}
    if os.environ.get("OPENREVIEW_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['OPENREVIEW_TOKEN']}"
    notes, seen = [], set()
    for offset in range(0, 20000, 1000):
        result = fetch_json("https://api2.openreview.net/notes?" + urlencode({**params, "offset": offset}), headers)
        page = result.get("notes", [])
        for note in page:
            if not note.get("id") or note["id"] in seen:
                raise arxiv.IncompleteHarvestError("OpenReview pagination repeated or missing note ID")
            seen.add(note["id"])
        notes.extend(page)
        total = result.get("count")
        if (isinstance(total, int) and len(notes) >= total) or (total is None and len(page) < 1000):
            break
        if not page:
            raise arxiv.IncompleteHarvestError("OpenReview page ended before advertised count")
    else:
        raise arxiv.IncompleteHarvestError("OpenReview pagination budget exhausted")
    output: list[dict[str, Any]] = []
    for note in notes:
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
    if item["type"] in {"github", "huggingface"}:
        # `to_record` starts from an arXiv-shaped record and otherwise treats
        # the discovery URL as a paper. Repository and dataset discoveries do
        # not become papers merely because they are the primary source.
        for key in ("report", "paper", "pdf"):
            record["links"].pop(key, None)
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
    source_coverage.save(REVIEW_PATH, queue)
    return added, duplicates


def paper_candidate(paper: arxiv.Paper, config: dict[str, Any], now: str) -> dict | None:
    score, relation, reasons = arxiv.recognition(paper)
    if score < float(config["thresholds"]["review"]):
        return None
    record = arxiv.to_record(paper, now, score, relation, reasons)
    record["reviewContext"] = {"abstract": paper.abstract, "comments": paper.comments}
    record["candidatePriority"] = "high" if score >= float(config["thresholds"]["publish"]) else "normal"
    return record


def discover(target: str, config: dict, *, dry_run: bool = False, max_seconds: int = 600,
             max_windows: int = 80, start_date: str | None = None,
             sources: set[str] | None = None) -> dict:
    """Run scoped work units; a failed adapter never publishes an empty replacement.

    Coverage certifies only these queries and the first-release window, not all
    benchmarks on the platform or historical source updates.
    """
    started = time_module.monotonic()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ledger = source_coverage.load(COVERAGE_PATH)
    sources = sources or {"arxiv", "github", "huggingface", "openreview"}
    if sources - {"arxiv", "github", "huggingface", "openreview"}:
        raise ValueError("Unsupported discovery source")
    first = start_date or arxiv_query_dates(target)[0]
    start, end = date.fromisoformat(first), date.fromisoformat(target)
    if end < start:
        raise ValueError("start date must precede target date")
    if "arxiv" in sources:
        day = start
        while day <= end:
            last = min(day + timedelta(days=6), end)
            for category in config["arxiv"]["categories"]:
                source_coverage.enqueue(ledger, "arxiv", category, day.isoformat(), last.isoformat())
            day = last + timedelta(days=1)
    external_days = ([ (start + timedelta(days=i)).isoformat() for i in range((end-start).days + 1)]
                     if start_date else publication_batch_dates(target))
    for name in sources - {"arxiv"}:
        for day in external_days:
            source_coverage.enqueue(ledger, name, "created-benchmark-v2", day, day)
    if not start_date:
        # A completed early morning query can precede a late source announcement.
        # Revisit recent windows on the scheduled later retry without reopening
        # historical backfills or discarding their completion receipts.
        refresh_before = (datetime.fromisoformat(now.replace('Z', '+00:00')) - timedelta(hours=2)).isoformat().replace('+00:00', 'Z')
        for window in ledger['windows'].values():
            if (window['source'] in sources and window['status'] == 'complete'
                    and first <= window['to'] <= target and window.get('lastAttemptAt', '') <= refresh_before):
                window['status'] = 'pending'
    if not dry_run:
        # Persist debt before the first request so process death is recoverable.
        source_coverage.save(COVERAGE_PATH, ledger)
    adapters = {"github": github_candidates, "huggingface": huggingface_candidates, "openreview": openreview_candidates}
    stats = {"attempted": 0, "complete": 0, "failed": 0, "fetched": 0, "candidates": 0,
             "dryRun": dry_run, "sourceDate": target, "windows": []}
    for identifier, window in source_coverage.pending(ledger, now):
        if window['source'] not in sources:
            continue
        if stats['attempted'] >= max_windows or time_module.monotonic() - started >= max_seconds:
            break
        stats['attempted'] += 1
        name = window['source']
        try:
            if name == 'arxiv':
                scoped = copy.deepcopy(config)
                scoped['arxiv']['categories'] = [window['scope']]
                try:
                    papers = arxiv.fetch_for_range(window['from'], window['to'], scoped)
                except (HTTPError, URLError, TimeoutError, RuntimeError):
                    papers = arxiv.fetch_for_range_atom(window['from'], window['to'], scoped)
                fetched = len(papers)
                records = [r for paper in papers if (r := paper_candidate(paper, config, now)) is not None]
            else:
                rows = adapters[name](window['from'])
                fetched = len(rows)
                records = [candidate_record(item, now, config) for item in rows]
            stats['fetched'] += fetched
            stats['candidates'] += len(records)
            if not dry_run:
                merge_review_queue(records, target, first, {})
                source_coverage.attempt(ledger, identifier, now=now, status='complete', count=fetched,
                                        candidate_hash=source_coverage.receipt(REVIEW_PATH))
            stats['complete'] += 1
            stats['windows'].append({'key': identifier, 'status': 'complete', 'fetched': fetched, 'candidates': len(records)})
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as error:
            stats['failed'] += 1
            stats['windows'].append({'key': identifier, 'status': 'failed', 'error': type(error).__name__})
            if not dry_run:
                source_coverage.attempt(ledger, identifier, now=now, status='failed', error=str(error))
        if not dry_run:
            source_coverage.save(COVERAGE_PATH, ledger)
    stats['outstandingWindows'] = sum(w['status'] != 'complete' for w in ledger['windows'].values())
    if not dry_run:
        # Expose the current processing date even when all adapters fail; this is
        # not a source completion certificate. The ledger retains those failures.
        failures = {w['key']: w['error'] for w in stats['windows'] if w['status'] == 'failed'}
        merge_review_queue([], target, first, failures)
        source_coverage.save(RUNS_PATH / f"{target}.json", {'sourceDate': target, 'generatedAt': now,
            'externalDiscovery': stats, 'coverageLedger': 'data/source_coverage.json'})
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover candidates with durable scoped gap recovery.")
    parser.add_argument("--date", required=True, help="Inclusive first-public date / end date")
    parser.add_argument("--start-date", help="Explicit historical backfill start; enqueues bounded windows")
    parser.add_argument("--sources", help="Comma-separated source names (default all)")
    parser.add_argument("--max-seconds", type=int)
    parser.add_argument("--max-windows", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = arxiv.read_json(arxiv.CONFIG_PATH)
    settings = config.get('discovery', {})
    result = discover(date.fromisoformat(args.date).isoformat(), config, dry_run=args.dry_run,
        max_seconds=args.max_seconds if args.max_seconds is not None else settings.get('max_runtime_seconds', 600),
        max_windows=args.max_windows if args.max_windows is not None else settings.get('max_windows_per_run', 80),
        start_date=args.start_date, sources=set(args.sources.split(',')) if args.sources else None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

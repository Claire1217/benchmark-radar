#!/usr/bin/env python3
"""Snapshot public attention signals and compute transparent window rankings."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "benchmarks.json"
METRICS_DIR = ROOT / "data" / "metrics"
USER_AGENT = "BenchmarkRadar/1.0 (https://github.com/Claire1217/benchmark-radar)"
METHOD_VERSION = "attention-ranking-v1"
WINDOW_DAYS = {"today": 0, "30d": 30, "90d": 90}
WINDOW_WEIGHTS = {
    "today": {"hfPaperUpvotes": 0.60, "githubStars": 0.25, "hfDatasetDownloads": 0.15},
    "30d": {"hfPaperUpvotes": 0.40, "githubStars": 0.30, "hfDatasetDownloads": 0.30},
    "90d": {"hfPaperUpvotes": 0.30, "githubStars": 0.30, "hfDatasetDownloads": 0.40},
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any] | None:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    request_headers.update(headers or {})
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=request_headers), timeout=45) as response:
                return json.loads(response.read())
        except HTTPError as error:
            if error.code in {403, 404, 429}:
                if error.code == 429 and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return None
            raise
        except URLError:
            if attempt == 2:
                return None
            time.sleep(2 ** attempt)
    return None


def github_slug(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"github\.com/([^/]+)/([^/#?]+)", url, re.I)
    return f"{match.group(1)}/{match.group(2).removesuffix('.git')}" if match else None


def dataset_slug(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"huggingface\.co/datasets/([^/]+)/([^/#?]+)", url, re.I)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def enrich_one(record: dict[str, Any], github_token: str | None, allow_github: bool) -> dict[str, Any]:
    arxiv_id = str(record.get("source", {}).get("id", ""))
    paper = get_json(f"https://huggingface.co/api/papers/{quote(arxiv_id)}") if arxiv_id else None
    paper = paper or {}
    github_url = paper.get("githubRepo") or record.get("links", {}).get("code")
    repo = github_slug(github_url)
    github_stars = paper.get("githubStars")
    github_source = "huggingface-paper" if github_stars is not None else None
    if repo and allow_github:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"
        repo_info = get_json(f"https://api.github.com/repos/{repo}", headers)
        if repo_info and repo_info.get("stargazers_count") is not None:
            github_stars = repo_info["stargazers_count"]
            github_source = "github-rest"

    data_url = record.get("links", {}).get("data")
    dataset = dataset_slug(data_url)
    dataset_info = get_json(f"https://huggingface.co/api/datasets/{dataset}") if dataset else None
    dataset_info = dataset_info or {}
    return {
        "benchmarkId": record["id"],
        "hfPaperUpvotes": paper.get("upvotes"),
        "hfDailySubmittedAt": paper.get("submittedOnDailyAt"),
        "hfPaperUrl": f"https://huggingface.co/papers/{arxiv_id}" if paper else None,
        "githubRepo": f"https://github.com/{repo}" if repo else None,
        "githubStars": github_stars,
        "githubStarsSource": github_source,
        "hfDataset": dataset,
        "hfDatasetDownloads": dataset_info.get("downloads"),
        "hfDatasetLikes": dataset_info.get("likes"),
    }


def percentile(value: int | float | None, population: list[int | float]) -> float | None:
    if value is None or not population:
        return None
    transformed = [math.log1p(max(float(item), 0.0)) for item in population]
    target = math.log1p(max(float(value), 0.0))
    below = sum(item < target for item in transformed)
    equal = sum(item == target for item in transformed)
    return (below + 0.5 * equal) / len(transformed)


def closest_history(as_of: date, days: int) -> dict[str, Any] | None:
    if days <= 0:
        days = 1
    cutoff = as_of - timedelta(days=days)
    candidates = sorted(path for path in METRICS_DIR.glob("*.json") if path.stem <= cutoff.isoformat())
    return read_json(candidates[-1]) if candidates else None


def rank_records(
    records: list[dict[str, Any]],
    raw_by_id: dict[str, dict[str, Any]],
    as_of: date,
    latest_source_date: str,
) -> None:
    for window, max_age in WINDOW_DAYS.items():
        if window == "today":
            candidates = [
                record
                for record in records
                if record["releasedAt"] == latest_source_date
                or str(raw_by_id[record["id"]].get("hfDailySubmittedAt", ""))[:10] == as_of.isoformat()
            ]
        else:
            candidates = [
                record
                for record in records
                if 0 <= (as_of - date.fromisoformat(record["releasedAt"])).days <= max_age
            ]
        previous = closest_history(as_of, max_age)
        previous_by_id = {item["benchmarkId"]: item for item in (previous or {}).get("records", [])}
        signal_values: dict[str, dict[str, int | float | None]] = {}
        signal_modes: dict[str, str] = {}
        for signal in WINDOW_WEIGHTS[window]:
            current_values: dict[str, int | float | None] = {}
            used_delta = False
            for record in candidates:
                current = raw_by_id[record["id"]].get(signal)
                old = previous_by_id.get(record["id"], {}).get(signal)
                if current is not None and old is not None:
                    current_values[record["id"]] = max(float(current) - float(old), 0.0)
                    used_delta = True
                else:
                    current_values[record["id"]] = current
            signal_values[signal] = current_values
            signal_modes[signal] = "window delta" if used_delta else "current level"

        scored: list[tuple[float, dict[str, Any]]] = []
        for record in candidates:
            weighted = 0.0
            coverage = 0.0
            components: dict[str, Any] = {}
            observed = 0
            for signal, weight in WINDOW_WEIGHTS[window].items():
                value = signal_values[signal][record["id"]]
                population = [item for item in signal_values[signal].values() if item is not None]
                pct = percentile(value, population)
                components[signal] = {"value": value, "percentile": pct, "mode": signal_modes[signal]}
                if pct is not None:
                    weighted += weight * pct
                    coverage += weight
                    observed += 1
            score = round(100 * weighted / coverage) if coverage else None
            confidence = "High" if coverage >= 0.75 and observed >= 2 else "Medium" if coverage >= 0.4 else "Low"
            record.setdefault("ranking", {})[window] = {
                "score": score,
                "rank": None,
                "coverage": round(coverage, 2),
                "confidence": confidence,
                "method": METHOD_VERSION,
                "components": components,
            }
            # A leaderboard position requires corroboration from at least two
            # independent signal families. Single-source records stay visible
            # but are not called "ranked".
            if score is not None and observed >= 2:
                scored.append((score, record))
        scored.sort(key=lambda item: (item[0], item[1]["releasedAt"]), reverse=True)
        for position, (_, record) in enumerate(scored, 1):
            record["ranking"][window]["rank"] = position

        datasets = [record for record in candidates if raw_by_id[record["id"]].get("hfDatasetDownloads") is not None]
        datasets.sort(key=lambda record: raw_by_id[record["id"]]["hfDatasetDownloads"], reverse=True)
        for position, record in enumerate(datasets, 1):
            record["ranking"][window]["datasetDownloadRank"] = position
            record["ranking"][window]["datasetRankPopulation"] = len(datasets)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Snapshot HF/GitHub attention signals and rank benchmarks.")
    parser.add_argument("--date", help="Observation date in YYYY-MM-DD; defaults to manifest dataAsOf.")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--github-limit", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = read_json(DATA_PATH)
    records = payload.get("records", [])
    latest_source_date = payload["manifest"].get("latestSourceDate", payload["manifest"]["dataAsOf"])
    as_of = date.fromisoformat(args.date or date.today().isoformat())
    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    github_token = os.environ.get("GITHUB_TOKEN")
    github_slots = set(
        record["id"]
        for record in records
        if github_slug(record.get("links", {}).get("code"))
    )
    if not github_token:
        github_slots = set(list(github_slots)[: max(args.github_limit, 0)])

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(enrich_one, record, github_token, record["id"] in github_slots): record["id"]
            for record in records
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["benchmarkId"])
    raw_by_id = {item["benchmarkId"]: item for item in results}
    for record in records:
        raw = raw_by_id[record["id"]]
        record["attention"] = {
            "asOf": as_of.isoformat(),
            "hfPaperUpvotes": raw["hfPaperUpvotes"],
            "hfDailySubmittedAt": raw["hfDailySubmittedAt"],
            "hfPaperUrl": raw["hfPaperUrl"],
            "githubStars": raw["githubStars"],
            "githubRepo": raw["githubRepo"],
            "hfDatasetDownloads": raw["hfDatasetDownloads"],
            "hfDatasetLikes": raw["hfDatasetLikes"],
            "hfDataset": raw["hfDataset"],
        }
        if raw["githubRepo"] and not record.get("links", {}).get("code"):
            record["links"]["code"] = raw["githubRepo"]
        if raw["hfPaperUrl"]:
            record["links"]["hfPaper"] = raw["hfPaperUrl"]

    rank_records(records, raw_by_id, as_of, latest_source_date)
    snapshot = {
        "schemaVersion": "1.0",
        "methodVersion": METHOD_VERSION,
        "date": as_of.isoformat(),
        "observedAt": observed_at,
        "records": results,
    }
    write_json(METRICS_DIR / f"{as_of.isoformat()}.json", snapshot)
    payload["manifest"]["metrics"] = {
        "observedAt": observed_at,
        "methodVersion": METHOD_VERSION,
        "windows": ["today", "30d", "90d"],
        "note": "Window deltas are used when historical snapshots exist; otherwise rankings use current levels and say so.",
    }
    payload["manifest"]["latestSourceDate"] = latest_source_date
    payload["manifest"]["dataAsOf"] = as_of.isoformat()
    payload["manifest"]["sourceCoverage"] = list(
        dict.fromkeys(payload["manifest"].get("sourceCoverage", []) + ["Hugging Face Hub", "GitHub REST"])
    )
    write_json(DATA_PATH, payload)
    print(f"observed={len(results)} as_of={as_of.isoformat()} metrics={METRICS_DIR / (as_of.isoformat() + '.json')}")


if __name__ == "__main__":
    main()

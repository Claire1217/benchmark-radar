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
from zoneinfo import ZoneInfo

try:
    from generate_public_index import effective_latest_batch
except ModuleNotFoundError:  # Imported as pipeline.enrich_metrics in tests.
    from pipeline.generate_public_index import effective_latest_batch


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "benchmarks.json"
OVERRIDES_PATH = ROOT / "data" / "curated_overrides.json"
METRICS_DIR = ROOT / "data" / "metrics"
USER_AGENT = "BenchmarkRadar/1.0 (https://github.com/Claire1217/benchmark-radar)"
METHOD_VERSION = "attention-ranking-v13"
MISSING_SIGNAL_PRIOR = 0.50
WINDOW_DAYS = {"today": 0, "30d": 30, "90d": 90}
WINDOW_WEIGHTS = {
    "today": {"hfPaperUpvotes": 0.45, "githubStars": 0.25, "hfDatasetDownloads": 0.05},
    "30d": {"hfPaperUpvotes": 0.30, "githubStars": 0.55, "hfDatasetDownloads": 0.15},
    "90d": {"hfPaperUpvotes": 0.15, "githubStars": 0.55, "hfDatasetDownloads": 0.30},
}
TODAY_FORECAST_BONUS_WEIGHT = 0.25
TRACKED_SIGNALS = ("hfPaperUpvotes", "githubStars", "hfDatasetDownloads", "hfDatasetLikes")
PUBLICATION_TIMEZONE = ZoneInfo("Australia/Brisbane")


def publication_today() -> date:
    return datetime.now(PUBLICATION_TIMEZONE).date()


def github_scope(url: str | None) -> str | None:
    """Distinguish a dedicated benchmark repo from a subdirectory in a hosting repo."""
    if not url or not github_slug(url):
        return None
    return "hosting_repo" if re.search(r"github\.com/[^/]+/[^/]+/(?:tree|blob)/", url, re.I) else "benchmark_repo"


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
            # A public artifact can later become private or gated. Treat that
            # single signal as unavailable so preserve_last_known() can retain
            # its previous observation instead of aborting the daily update.
            if error.code in {401, 403, 404, 429}:
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


def github_stars_from_public_page(repo: str) -> int | None:
    """Read the public counter when the unauthenticated REST quota is exhausted."""
    try:
        request = Request(f"https://github.com/{repo}", headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=45) as response:
            html = response.read().decode("utf-8", "ignore")
    except (HTTPError, URLError):
        return None
    match = re.search(r'aria-label="([0-9,]+) users starred this repository"', html, re.I)
    return int(match.group(1).replace(",", "")) if match else None


def get_public_html(url: str) -> str:
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=45) as response:
            return response.read().decode("utf-8", "ignore")
    except (HTTPError, URLError):
        return ""


def hf_public_page_counts(url: str, fields: tuple[str, ...]) -> dict[str, int | None]:
    """Extract server-rendered public counters when a Hub API route is unavailable."""
    html = get_public_html(url)
    output: dict[str, int | None] = {}
    for field in fields:
        match = re.search(rf'(?:&quot;|"){re.escape(field)}(?:&quot;|")\s*:\s*(\d+)', html)
        output[field] = int(match.group(1)) if match else None
    return output


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


def readiness_from_links(links: dict[str, Any]) -> str:
    if links.get("code"):
        return "Runnable"
    if links.get("data") or links.get("project"):
        return "Inspectable"
    return "Paper only"


def enrich_one(record: dict[str, Any], github_token: str | None, allow_github: bool) -> dict[str, Any]:
    source = record.get("source", {})
    arxiv_id = str(source.get("id", "")) if source.get("type") == "arxiv" else ""
    paper = get_json(f"https://huggingface.co/api/papers/{quote(arxiv_id)}") if arxiv_id else None
    paper = paper or {}
    if arxiv_id and paper.get("upvotes") is None:
        paper.update(hf_public_page_counts(f"https://huggingface.co/papers/{quote(arxiv_id)}", ("upvotes",)))
    # The canonical code URL carries benchmark scope (for example a subfolder in
    # a monorepo); prefer it over HF's repo-level association.
    github_url = record.get("links", {}).get("code") or paper.get("githubRepo")
    github_signal_scope = github_scope(github_url)
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
        elif github_stars is None:
            github_stars = github_stars_from_public_page(repo)
            github_source = "github-public-page" if github_stars is not None else None

    data_url = record.get("links", {}).get("data")
    dataset = dataset_slug(data_url)
    dataset_info = get_json(f"https://huggingface.co/api/datasets/{dataset}") if dataset else None
    dataset_info = dataset_info or {}
    if dataset and dataset_info.get("downloads") is None:
        dataset_info.update(
            hf_public_page_counts(
                f"https://huggingface.co/datasets/{dataset}", ("downloads", "likes")
            )
        )
    signal_status = {
        "hfPaperUpvotes": {
            "state": "fresh" if paper.get("upvotes") is not None else "unavailable" if arxiv_id else "not_applicable"
        },
        "githubStars": {
            "state": "fresh" if github_stars is not None else "not_refreshed" if repo and not allow_github else "unavailable" if repo else "not_applicable"
        },
        "hfDatasetDownloads": {
            "state": "fresh" if dataset_info.get("downloads") is not None else "unavailable" if dataset else "not_applicable"
        },
        "hfDatasetLikes": {
            "state": "fresh" if dataset_info.get("likes") is not None else "unavailable" if dataset else "not_applicable"
        },
    }
    return {
        "benchmarkId": record["id"],
        "hfPaperUpvotes": paper.get("upvotes"),
        "hfDailySubmittedAt": paper.get("submittedOnDailyAt"),
        "hfPaperUrl": f"https://huggingface.co/papers/{arxiv_id}" if paper else None,
        "githubRepo": f"https://github.com/{repo}" if repo else None,
        "githubStars": github_stars,
        "githubScope": github_signal_scope,
        "githubStarsSource": github_source,
        "hfDataset": dataset,
        "hfDatasetDownloads": dataset_info.get("downloads"),
        "hfDatasetLikes": dataset_info.get("likes"),
        "signalStatus": signal_status,
    }


def preserve_last_known(
    results: list[dict[str, Any]],
    records: list[dict[str, Any]],
    previous_snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Keep the last successful value on provider failure and mark it stale."""
    previous_by_id = {
        item["benchmarkId"]: item for item in (previous_snapshot or {}).get("records", [])
    }
    canonical_by_id = {record["id"]: record.get("attention", {}) for record in records}
    for item in results:
        benchmark_id = item["benchmarkId"]
        previous = previous_by_id.get(benchmark_id, {})
        canonical = canonical_by_id.get(benchmark_id, {})
        statuses = item.setdefault("signalStatus", {})
        for signal in TRACKED_SIGNALS:
            status = statuses.setdefault(
                signal, {"state": "retained" if item.get(signal) is not None else "unavailable"}
            )
            if item.get(signal) is not None:
                continue
            if status.get("state") == "not_applicable":
                continue
            fallback = previous.get(signal)
            fallback_date = (
                (previous.get("signalStatus", {}).get(signal) or {}).get("lastSuccessfulDate")
                or (previous_snapshot or {}).get("date")
            )
            if fallback is None:
                fallback = canonical.get(signal)
                fallback_date = (
                    (canonical.get("signalStatus", {}).get(signal) or {}).get("lastSuccessfulDate")
                    or canonical.get("asOf")
                )
            if fallback is not None:
                item[signal] = fallback
                status["state"] = "stale"
                status["lastSuccessfulDate"] = fallback_date
        for identity_field in ("hfPaperUrl", "githubRepo", "githubScope", "hfDataset"):
            if item.get(identity_field) is None:
                item[identity_field] = previous.get(identity_field)
    return results


def summarize_observation(
    results: list[dict[str, Any]],
    attempted_at: str,
    previous_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """Describe retrieval freshness without presenting a failed attempt as observation time."""
    counts = {
        state: sum(
            status.get("state") == state
            for item in results
            for status in item.get("signalStatus", {}).values()
        )
        for state in (
            "fresh", "stale", "unavailable", "not_refreshed", "not_applicable", "retained"
        )
    }
    for item in results:
        for status in item.get("signalStatus", {}).values():
            if status.get("state") == "fresh":
                status["observedAt"] = attempted_at
            elif status.get("state") not in {"not_applicable", "retained"}:
                status["checkedAt"] = attempted_at

    failures = counts["stale"] + counts["unavailable"] + counts["not_refreshed"]
    if counts["fresh"]:
        state = "partial" if failures else "fresh"
        observed_at = attempted_at
    elif counts["stale"] or counts["retained"]:
        state = "stale"
        observed_at = (previous_snapshot or {}).get("observedAt")
    else:
        state = "unavailable"
        observed_at = None
    return {
        "status": state,
        "observedAt": observed_at,
        "attemptedAt": attempted_at,
        "providerStatus": counts,
    }


def percentile(
    value: int | float | None, population: list[int | float], *, signed: bool = False
) -> float | None:
    if value is None or not population:
        return None
    # Percentile ranks are invariant under monotonic log transforms. Keeping raw
    # values here makes the method easier to audit without changing rank order.
    transformed = [float(item) for item in population]
    target = float(value)
    below = sum(item < target for item in transformed)
    equal = sum(item == target for item in transformed)
    return (below + 0.5 * equal) / len(transformed)


def log_max_normalized(
    value: int | float | None, population: list[int | float]
) -> float | None:
    """Keep magnitude differences while damping heavy-tailed public counts."""
    if value is None or not population:
        return None
    maximum = max(max(0.0, float(item)) for item in population)
    target = max(0.0, float(value))
    if maximum == 0:
        return 0.0
    return min(1.0, math.log1p(target) / math.log1p(maximum))


def weighted_attention(
    normalized_values: dict[str, float | None], weights: dict[str, float]
) -> float | None:
    """Blend fixed signal weights, shrinking missing observations to neutral."""
    if not any(normalized_values.get(signal) is not None for signal in weights):
        return None
    return sum(
        (
            normalized_values.get(signal)
            if normalized_values.get(signal) is not None
            else MISSING_SIGNAL_PRIOR
        )
        * weight
        for signal, weight in weights.items()
    ) / sum(weights.values())


def closest_history(as_of: date, days: int) -> dict[str, Any] | None:
    if days <= 0:
        days = 1
    cutoff = as_of - timedelta(days=days)
    candidates = sorted(path for path in METRICS_DIR.glob("*.json") if path.stem <= cutoff.isoformat())
    return read_json(candidates[-1]) if candidates else None


def latest_snapshot_before(as_of: date) -> dict[str, Any] | None:
    candidates = sorted(path for path in METRICS_DIR.glob("*.json") if path.stem < as_of.isoformat())
    return read_json(candidates[-1]) if candidates else None


def rank_records(
    records: list[dict[str, Any]],
    raw_by_id: dict[str, dict[str, Any]],
    as_of: date,
    latest_source_date: str,
    latest_batch_start: str | None = None,
    windows: tuple[str, ...] | None = None,
) -> None:
    def score_dimension(
        candidates: list[dict[str, Any]],
        values: dict[str, dict[str, int | float | None]],
        weights: dict[str, float],
        *,
        signed: bool,
        allow_hf_only_rank: bool,
        forecast_bonus_weight: float = 0.0,
        normalization: str = "percentile",
    ) -> tuple[dict[str, dict[str, Any]], list[tuple[float, dict[str, Any]]]]:
        output: dict[str, dict[str, Any]] = {}
        scored: list[tuple[float, dict[str, Any]]] = []
        populations: dict[str, list[int | float]] = {}
        for signal in weights:
            for record in candidates:
                value = values[signal][record["id"]]
                if value is not None:
                    populations.setdefault(signal, []).append(value)
        for record in candidates:
            coverage = 0.0
            observed = 0
            observed_normalized: dict[str, float | None] = {}
            components: dict[str, Any] = {}
            for signal, weight in weights.items():
                value = values[signal][record["id"]]
                population = populations.get(signal, [])
                normalized = (
                    log_max_normalized(value, population)
                    if normalization == "log-max"
                    else percentile(value, population, signed=signed)
                )
                components[signal] = {
                    "value": value,
                    "normalized": normalized,
                    "normalization": normalization,
                }
                if normalization == "percentile":
                    components[signal]["percentile"] = normalized
                observed_normalized[signal] = normalized
                if normalized is not None:
                    coverage += weight
                    observed += 1
            # Fixed signal-type weights make the score interpretable. Missing
            # observations shrink to neutral instead of gaining redistributed weight.
            observed_composite = weighted_attention(observed_normalized, weights)
            composite = observed_composite
            if forecast_bonus_weight and observed_composite is not None:
                forecast_value = (record.get("attentionForecast") or {}).get("score")
                forecast_percentile = (
                    max(0.0, min(1.0, float(forecast_value) / 100.0))
                    if forecast_value is not None
                    else 0.0
                )
                components["llmAttentionForecast"] = {
                    "value": forecast_value,
                    "percentile": forecast_percentile,
                    "role": "bonus",
                    "maxContribution": forecast_bonus_weight,
                }
                composite = (
                    observed_composite * (1.0 - forecast_bonus_weight)
                    + forecast_percentile * forecast_bonus_weight
                )
            score = round(100 * composite + 1e-9) if composite is not None else None
            confidence = (
                "High" if coverage >= 0.75 and observed >= 2
                else "Medium" if coverage >= 0.4 and observed >= 2
                else "Low"
            )
            result = {
                "score": score, "rank": None, "coverage": round(coverage, 2),
                "confidence": confidence, "components": components,
            }
            output[record["id"]] = result
            # HF votes can rank a launch batch, where community discovery is the
            # decision context. In longer windows they still produce a visible
            # score, but a formal rank requires a repository or dataset signal.
            has_durable_signal = any(
                components[signal]["normalized"] is not None
                for signal in ("githubStars", "hfDatasetDownloads")
            )
            if composite is not None and (allow_hf_only_rank or has_durable_signal):
                scored.append((composite, record))
        scored.sort(key=lambda item: (item[0], item[1]["releasedAt"]), reverse=True)
        for position, (_, record) in enumerate(scored, 1):
            output[record["id"]]["rank"] = position
        return output, scored

    selected_windows = windows or tuple(WINDOW_DAYS)
    batch_start = latest_batch_start or latest_source_date
    for window in selected_windows:
        max_age = WINDOW_DAYS[window]
        # A window is a derived view. Rebuild it from scratch so yesterday's
        # Today rank cannot survive after the release/surfacing date rolls on.
        for record in records:
            record.setdefault("ranking", {}).pop(window, None)
        if window == "today":
            candidates = [
                record
                for record in records
                if batch_start <= record["releasedAt"] <= latest_source_date
            ]
        else:
            candidates = [
                record
                for record in records
                if 0 <= (as_of - date.fromisoformat(record["releasedAt"])).days <= max_age
            ]
        previous = closest_history(as_of, max_age)
        previous_by_id = {item["benchmarkId"]: item for item in (previous or {}).get("records", [])}
        history_date = (previous or {}).get("date")
        level_values: dict[str, dict[str, int | float | None]] = {}
        growth_values: dict[str, dict[str, int | float | None]] = {}
        for signal in WINDOW_WEIGHTS[window]:
            current_values: dict[str, int | float | None] = {}
            delta_values: dict[str, int | float | None] = {}
            for record in candidates:
                current_row = raw_by_id[record["id"]]
                current = (
                    (record.get("attentionForecast") or {}).get("score")
                    if signal == "llmAttentionForecast"
                    else current_row.get(signal)
                )
                current_scope = current_row.get("githubScope") or github_scope(record.get("links", {}).get("code"))
                if signal == "githubStars" and current_scope == "hosting_repo":
                    current = None
                old_row = previous_by_id.get(record["id"], {})
                old = old_row.get(signal)
                if signal == "githubStars" and old_row.get("githubScope") == "hosting_repo":
                    old = None
                current_state = (current_row.get("signalStatus", {}).get(signal) or {}).get("state")
                old_state = (old_row.get("signalStatus", {}).get(signal) or {}).get("state")
                usable_delta = current_state not in {"stale", "unavailable", "not_refreshed", "not_applicable"}
                usable_delta = usable_delta and old_state not in {"stale", "unavailable", "not_refreshed", "not_applicable"}
                current_values[record["id"]] = current
                delta_values[record["id"]] = (
                    float(current) - float(old)
                    if current is not None and old is not None and usable_delta
                    else None
                )
            level_values[signal] = current_values
            growth_values[signal] = delta_values

        levels, _ = score_dimension(
            candidates, level_values, WINDOW_WEIGHTS[window], signed=False,
            allow_hf_only_rank=window == "today",
            forecast_bonus_weight=TODAY_FORECAST_BONUS_WEIGHT if window == "today" else 0.0,
            normalization="percentile" if window == "today" else "log-max",
        )
        growth, _ = score_dimension(
            candidates, growth_values, WINDOW_WEIGHTS[window], signed=True,
            allow_hf_only_rank=window == "today",
        )
        for record in candidates:
            level = levels[record["id"]]
            growth_result = growth[record["id"]]
            record.setdefault("ranking", {})[window] = {
                # Backward-compatible aliases now always mean current level.
                "score": level["score"], "rank": level["rank"],
                "coverage": level["coverage"], "confidence": level["confidence"],
                "method": METHOD_VERSION,
                "level": level,
                "growth": {
                    **growth_result,
                    "historyDate": history_date,
                    "windowDays": max(max_age, 1),
                    "elapsedDays": (
                        (as_of - date.fromisoformat(history_date)).days if history_date else None
                    ),
                },
            }

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
    parser.add_argument(
        "--rerank-only",
        action="store_true",
        help="Recompute derived rankings from an existing real snapshot without network access.",
    )
    parser.add_argument(
        "--only-ids",
        help="Comma-separated benchmark ids to refresh; other rows are retained from today's snapshot.",
    )
    parser.add_argument(
        "--today-only",
        action="store_true",
        help="Refresh the latest public batch and recompute only the Today ranking.",
    )
    return parser.parse_args()


def observation_mode(as_of: date, today: date, explicit_date: bool, snapshot_exists: bool) -> str:
    if as_of > today:
        raise RuntimeError("Observation date cannot be in the future.")
    if explicit_date and as_of < today:
        if not snapshot_exists:
            raise RuntimeError(
                "Historical observation dates are read-only and require an existing real snapshot; "
                "current provider values will never be written into the past."
            )
        return "historical-read-only"
    return "live"


def main() -> None:
    args = parse_args()
    if args.rerank_only and args.today_only:
        raise RuntimeError("--rerank-only and --today-only cannot be combined.")
    payload = read_json(DATA_PATH)
    records = payload.get("records", [])
    today = publication_today()
    as_of = date.fromisoformat(args.date or today.isoformat())
    latest_batch = effective_latest_batch(
        records,
        as_of.isoformat(),
        (payload.get("manifest", {}).get("run") or {}).get("sourceWindow"),
        payload.get("manifest", {}).get("latestReportDate") or payload.get("manifest", {}).get("latestSourceDate"),
    )
    latest_source_date = latest_batch["to"]
    latest_batch_start = latest_batch["from"]
    snapshot_path = METRICS_DIR / f"{as_of.isoformat()}.json"
    if args.rerank_only:
        if not snapshot_path.exists():
            raise RuntimeError("--rerank-only requires an existing real snapshot for --date.")
        snapshot = read_json(snapshot_path)
        raw_by_id = {item["benchmarkId"]: item for item in snapshot.get("records", [])}
        if not all(record["id"] in raw_by_id for record in records):
            raise RuntimeError("Snapshot does not cover every canonical benchmark.")
        for record in records:
            scope = raw_by_id[record["id"]].get("githubScope") or github_scope(record.get("links", {}).get("code"))
            if scope:
                record.setdefault("attention", {})["githubScope"] = scope
        rank_records(records, raw_by_id, as_of, latest_source_date, latest_batch_start)
        payload["manifest"].setdefault("metrics", {})["methodVersion"] = METHOD_VERSION
        payload["manifest"]["metrics"]["rerankedFromSnapshot"] = as_of.isoformat()
        write_json(DATA_PATH, payload)
        print(f"reranked_records={len(records)} snapshot={snapshot_path.name} method={METHOD_VERSION}")
        return
    if observation_mode(as_of, today, bool(args.date), snapshot_path.exists()) == "historical-read-only":
        print(f"historical snapshot preserved without network access: {snapshot_path}")
        return
    attempted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    only_ids = {item.strip() for item in (args.only_ids or "").split(",") if item.strip()}
    if args.today_only:
        only_ids.update(
            record["id"] for record in records
            if latest_batch_start <= record.get("releasedAt", "") <= latest_source_date
        )
        if not only_ids:
            print(f"no Today records for latest release {latest_source_date}")
            return
    selected_records = [record for record in records if not only_ids or record["id"] in only_ids]
    github_token = os.environ.get("GITHUB_TOKEN")
    github_candidates = [
        record for record in records if github_slug(record.get("links", {}).get("code"))
    ]
    github_slots = {record["id"] for record in github_candidates}
    if not github_token:
        override_ids = set()
        if OVERRIDES_PATH.exists():
            override_payload = read_json(OVERRIDES_PATH)
            override_ids = set(override_payload.get("byArxivId", {}))
        github_candidates.sort(
            key=lambda record: (
                record.get("source", {}).get("id") in override_ids,
                record.get("source", {}).get("type") == "official-project",
                record.get("releasedAt", ""),
                record["id"],
            ),
            reverse=True,
        )
        github_slots = {
            record["id"] for record in github_candidates[: max(args.github_limit, 0)]
        }

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(enrich_one, record, github_token, record["id"] in github_slots): record["id"]
            for record in selected_records
        }
        for future in as_completed(futures):
            results.append(future.result())
    if only_ids:
        if not snapshot_path.exists():
            raise RuntimeError("--only-ids requires an existing snapshot for the observation date.")
        retained = {
            item["benchmarkId"]: item for item in read_json(snapshot_path).get("records", [])
        }
        retained.update({item["benchmarkId"]: item for item in results})
        results = list(retained.values())
    results.sort(key=lambda item: item["benchmarkId"])
    previous_snapshot = latest_snapshot_before(as_of)
    results = preserve_last_known(results, records, previous_snapshot)
    observation = summarize_observation(results, attempted_at, previous_snapshot)
    raw_by_id = {item["benchmarkId"]: item for item in results}
    for record in records:
        if only_ids and record["id"] not in only_ids:
            continue
        raw = raw_by_id[record["id"]]
        record["attention"] = {
            "asOf": as_of.isoformat(),
            "hfPaperUpvotes": raw["hfPaperUpvotes"],
            "hfDailySubmittedAt": raw["hfDailySubmittedAt"],
            "hfPaperUrl": raw["hfPaperUrl"],
            "githubStars": raw["githubStars"],
            "githubRepo": raw["githubRepo"],
            "githubScope": raw.get("githubScope"),
            "hfDatasetDownloads": raw["hfDatasetDownloads"],
            "hfDatasetLikes": raw["hfDatasetLikes"],
            "hfDataset": raw["hfDataset"],
            "observedAt": (
                attempted_at
                if any(status.get("state") == "fresh" for status in raw.get("signalStatus", {}).values())
                else (previous_snapshot or {}).get("observedAt")
            ),
            "attemptedAt": attempted_at,
            "status": (
                "fresh"
                if any(status.get("state") == "fresh" for status in raw.get("signalStatus", {}).values())
                else "stale"
                if any(status.get("state") == "stale" for status in raw.get("signalStatus", {}).values())
                else "unavailable"
            ),
            "signalStatus": raw.get("signalStatus", {}),
        }
        if raw["githubRepo"] and not record.get("links", {}).get("code"):
            record["links"]["code"] = raw["githubRepo"]
        if raw["hfPaperUrl"]:
            record["links"]["hfPaper"] = raw["hfPaperUrl"]
        links = record.get("links", {})
        record["readiness"] = readiness_from_links(links)

    rank_records(
        records,
        raw_by_id,
        as_of,
        latest_source_date,
        latest_batch_start,
        windows=("today",) if args.today_only else None,
    )
    snapshot = {
        "schemaVersion": "1.0",
        "methodVersion": METHOD_VERSION,
        "date": as_of.isoformat(),
        "observedAt": observation["observedAt"],
        "attemptedAt": observation["attemptedAt"],
        "status": observation["status"],
        "providerStatus": observation["providerStatus"],
        "records": results,
    }
    write_json(METRICS_DIR / f"{as_of.isoformat()}.json", snapshot)
    if args.today_only:
        metrics = payload["manifest"].setdefault("metrics", {})
        metrics.update({
            "todayObservedAt": observation["observedAt"],
            "todayAttemptedAt": observation["attemptedAt"],
            "todayStatus": observation["status"],
            "methodVersion": METHOD_VERSION,
        })
    else:
        payload["manifest"]["metrics"] = {
            "observedAt": observation["observedAt"],
            "attemptedAt": observation["attemptedAt"],
            "status": observation["status"],
            "methodVersion": METHOD_VERSION,
            "windows": ["today", "30d", "90d"],
            "note": "Current-level and growth rankings are separate. Growth is missing without a real prior snapshot; negative deltas are preserved.",
        }
    payload["manifest"]["latestSourceDate"] = latest_source_date
    payload["manifest"]["latestReportDate"] = latest_source_date
    payload["manifest"]["latestBatch"] = latest_batch
    payload["manifest"]["dataAsOf"] = as_of.isoformat()
    payload["manifest"]["sourceCoverage"] = list(
        dict.fromkeys(payload["manifest"].get("sourceCoverage", []) + ["Hugging Face Hub", "GitHub REST"])
    )
    write_json(DATA_PATH, payload)
    print(f"observed={len(results)} as_of={as_of.isoformat()} metrics={METRICS_DIR / (as_of.isoformat() + '.json')}")


if __name__ == "__main__":
    main()

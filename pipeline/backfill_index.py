#!/usr/bin/env python3
"""Run a resumable arXiv backfill with one checkpoint per category."""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable

from index_benchmarks import CONFIG_PATH, Paper, fetch_for_range, index_papers, read_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_ROOT = ROOT / "data" / "cache" / "backfill"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Replace a JSON file atomically after flushing it to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def paper_hash(papers: list[dict[str, Any]]) -> str:
    serialized = json.dumps(
        papers, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def checkpoint_path(cache_dir: Path, category: str) -> Path:
    return cache_dir / f"{category}.json"


def checkpoint_payload(
    category: str, start_date: str, end_date: str, papers: list[Paper]
) -> dict[str, Any]:
    serialized = [asdict(paper) for paper in papers]
    return {
        "manifest": {
            "category": category,
            "sourceWindow": {"from": start_date, "to": end_date},
            "paperCount": len(serialized),
            "completedAt": utc_now(),
            "sha256": paper_hash(serialized),
        },
        "papers": serialized,
    }


def load_checkpoint(
    path: Path, category: str, start_date: str, end_date: str
) -> tuple[list[Paper], dict[str, Any]] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifest = payload["manifest"]
        serialized = payload["papers"]
        if manifest.get("category") != category:
            return None
        if manifest.get("sourceWindow") != {"from": start_date, "to": end_date}:
            return None
        if manifest.get("paperCount") != len(serialized):
            return None
        if manifest.get("sha256") != paper_hash(serialized):
            return None
        return [Paper(**item) for item in serialized], manifest
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
        return None


def merge_papers(category_papers: list[list[Paper]]) -> list[Paper]:
    """Deduplicate cross-listed papers, keeping the newest source version."""
    merged: dict[str, Paper] = {}
    for papers in category_papers:
        for paper in papers:
            previous = merged.get(paper.arxiv_id)
            if previous is None or paper.updated_at > previous.updated_at:
                merged[paper.arxiv_id] = paper
    return sorted(merged.values(), key=lambda paper: paper.arxiv_id)


def write_window_manifest(
    cache_dir: Path,
    start_date: str,
    end_date: str,
    category_manifests: dict[str, dict[str, Any]],
) -> None:
    atomic_write_json(
        cache_dir / "manifest.json",
        {
            "sourceWindow": {"from": start_date, "to": end_date},
            "updatedAt": utc_now(),
            "categories": category_manifests,
        },
    )


def run_backfill(
    start_date: str,
    end_date: str,
    config: dict[str, Any],
    cache_root: Path = DEFAULT_CACHE_ROOT,
    *,
    resume: bool = False,
    force_categories: set[str] | None = None,
    finalize: Callable[..., dict[str, Any]] = index_papers,
) -> dict[str, Any]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end date must be on or after start date")
    categories = list(config["arxiv"]["categories"])
    forced = force_categories or set()
    unknown = forced - set(categories)
    if unknown:
        raise ValueError(f"unknown forced category: {', '.join(sorted(unknown))}")
    cache_dir = cache_root / f"{start_date}_{end_date}"
    all_papers: list[list[Paper]] = []
    category_manifests: dict[str, dict[str, Any]] = {}

    for category in categories:
        checkpoint = checkpoint_path(cache_dir, category)
        cached = None
        if resume and category not in forced and checkpoint.exists():
            cached = load_checkpoint(checkpoint, category, start_date, end_date)
        if cached is not None:
            papers, manifest = cached
        else:
            category_config = copy.deepcopy(config)
            category_config["arxiv"]["categories"] = [category]
            # If this raises, completed category checkpoints remain reusable and
            # finalize has not run, so the canonical database is untouched.
            papers = fetch_for_range(start_date, end_date, category_config)
            payload = checkpoint_payload(category, start_date, end_date, papers)
            atomic_write_json(checkpoint, payload)
            manifest = payload["manifest"]
        all_papers.append(papers)
        category_manifests[category] = manifest
        write_window_manifest(
            cache_dir, start_date, end_date, category_manifests
        )

    papers = merge_papers(all_papers)
    result = finalize(
        papers,
        start_date,
        end_date,
        end_date,
        config,
        started_from="resumable arXiv OAI-PMH category backfill",
    )
    return {
        "categories": category_manifests,
        "papersFetchedBeforeDedup": sum(len(items) for items in all_papers),
        "papersAfterDedup": len(papers),
        "index": result,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resumable category-by-category arXiv backfill.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument(
        "--resume", action="store_true", help="Reuse valid category checkpoints."
    )
    parser.add_argument(
        "--force-category",
        action="append",
        default=[],
        help="Refetch this category even when --resume is enabled; repeatable.",
    )
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_backfill(
        args.start_date,
        args.end_date,
        read_json(CONFIG_PATH),
        args.cache_root,
        resume=args.resume,
        force_categories=set(args.force_category),
    )
    print(
        f"categories={len(result['categories'])} "
        f"before_dedup={result['papersFetchedBeforeDedup']} "
        f"after_dedup={result['papersAfterDedup']}"
    )


if __name__ == "__main__":
    main()

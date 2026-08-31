#!/usr/bin/env python3
"""Automatically admit high-confidence benchmark releases without an AI gate."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import index_benchmarks as index


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "benchmarks.json"
REVIEW_PATH = ROOT / "data" / "review_queue.json"
CONFIG_PATH = ROOT / "pipeline" / "config.json"

IDENTITY_EVIDENCE = {
    "exact named benchmark artifact released in abstract",
    "coined title prefix ending in Bench or Benchmark",
    "exact coined title identity tied to benchmark evidence",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def public_release_ready(record: dict[str, Any]) -> bool:
    """Require a primary paper/review source or strong public artifact usage."""
    source = record.get("source") or {}
    source_type = str(source.get("type") or "")
    if source_type in {"arxiv", "openreview"}:
        return True

    links = record.get("links") or {}
    paper_hosts = {"arxiv.org", "www.arxiv.org", "openreview.net"}
    if any(
        urlparse(str(links.get(key) or "")).netloc.casefold() in paper_hosts
        for key in ("report", "paper", "project")
    ):
        return True

    source_signals = source.get("publicSignals") or {}
    attention = record.get("attention") or {}
    stars = max(
        int(source_signals.get("githubStars") or 0),
        int(attention.get("githubStars") or 0),
    )
    downloads = max(
        int(source_signals.get("hfDatasetDownloads") or 0),
        int(attention.get("hfDatasetDownloads") or 0),
    )
    likes = max(
        int(source_signals.get("hfDatasetLikes") or 0),
        int(attention.get("hfDatasetLikes") or 0),
    )
    return stars >= 25 or downloads >= 1000 or likes >= 10


def automatically_publishable(record: dict[str, Any], threshold: float) -> bool:
    """Use source-grounded deterministic evidence for automatic admission."""
    reasons = set((record.get("evidence") or {}).get("reasonCodes") or [])
    return (
        record.get("relation") == "introduces"
        and float(record.get("recognitionConfidence") or 0) >= threshold
        and bool(reasons & IDENTITY_EVIDENCE)
        and "evaluation protocol evidence" in reasons
        and public_release_ready(record)
    )


def promoted_record(candidate: dict[str, Any], now: str) -> dict[str, Any]:
    record = {
        key: value
        for key, value in candidate.items()
        if key not in {"reviewContext", "candidatePriority", "autoAdmission"}
    }
    record["dataStatus"] = "primary-source-indexed"
    record["displayEligible"] = True
    record.setdefault("evaluationMode", "public_reusable")
    record["capabilities"] = [
        value for value in record.get("capabilities", []) if value != "Evaluation"
    ]
    record["curation"] = {
        **(record.get("curation") or {}),
        "state": "rule-auto-admitted",
        "reviewedAt": now,
        "policy": "source-evidence-v2",
        "decisionReason": (
            "Automatically admitted from an explicit named benchmark release "
            "with evaluation-protocol evidence at or above the configured "
            "publication-confidence threshold."
        ),
    }
    return record


def admit_candidates(
    data: dict[str, Any], queue: dict[str, Any], threshold: float, now: str
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    promoted = [
        promoted_record(candidate, now)
        for candidate in queue.get("candidates", [])
        if automatically_publishable(candidate, threshold)
    ]
    promoted_sources = {
        str((record.get("source") or {}).get("id") or "") for record in promoted
    }
    records = index.upsert(data.get("records", []), promoted)
    data["records"] = records
    manifest = data.setdefault("manifest", {})
    manifest["recordCount"] = len(records)
    manifest["generatedAt"] = now

    remaining = [
        candidate
        for candidate in queue.get("candidates", [])
        if str((candidate.get("source") or {}).get("id") or "") not in promoted_sources
    ]
    queue["candidates"] = remaining
    queue["candidateCount"] = len(remaining)
    queue["queueMode"] = "automatic-admission-audit"
    queue["automaticAdmission"] = {
        "policy": "source-evidence-v2",
        "evaluatedAt": now,
        "publishThreshold": threshold,
        "promoted": len(promoted),
        "remainingForAudit": len(remaining),
    }
    return data, queue, promoted


def main() -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    config = read_json(CONFIG_PATH)
    data = read_json(DATA_PATH)
    queue = read_json(REVIEW_PATH)
    data, queue, promoted = admit_candidates(
        data, queue, float(config["thresholds"]["publish"]), now
    )
    write_json(DATA_PATH, data)
    write_json(REVIEW_PATH, queue)
    print(
        f"auto_admission_evaluated={queue.get('candidateCount', 0) + len(promoted)} "
        f"promoted={len(promoted)} remaining={queue.get('candidateCount', 0)}"
    )


if __name__ == "__main__":
    main()

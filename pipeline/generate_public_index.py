#!/usr/bin/env python3
"""Generate the compact, UI-facing view from the auditable canonical dataset."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "benchmarks.json"
OUTPUT = ROOT / "data" / "benchmarks_index.json"


def project_record(source: dict) -> dict:
    """Return the browser-safe subset shared by Radar and Library."""
    ranking = {}
    for window, value in source.get("ranking", {}).items():
        ranking[window] = {
                key: value.get(key)
                for key in ("score", "rank", "coverage", "confidence", "datasetDownloadRank", "datasetRankPopulation")
                if key in value
            }
    record = {
        key: source.get(key)
        for key in (
            "id", "familyId", "name", "oneLine", "area", "applicationDomains", "primaryDomain",
            "industrySectors", "capabilities", "topics", "construction", "annotation", "readiness",
            "releasedAt", "firstSeenAt", "recognitionConfidence", "links", "evidence", "dataStatus", "demo"
        )
    }
    record["links"] = {key: source["links"].get(key) for key in ("report", "pdf", "project", "code", "data", "hfPaper")}
    attention = source.get("attention") or {}
    record["attention"] = {
        key: attention.get(key)
        for key in ("asOf", "hfPaperUpvotes", "hfDailySubmittedAt", "githubStars", "hfDatasetDownloads", "hfDatasetLikes")
    }
    record["evidence"] = {
        "snippet": source.get("evidence", {}).get("snippet", ""),
        "reasonCodes": source.get("evidence", {}).get("reasonCodes", []),
    }
    record["source"] = {key: source["source"][key] for key in ("type", "id")}
    record["ranking"] = ranking
    for optional_key in ("motivation", "constructionDetail", "metrics", "curation", "publication", "venueAttempts", "publications", "watch", "releaseDates", "usageObservations"):
        if source.get(optional_key):
            record[optional_key] = source[optional_key]
    return record


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = [project_record(source) for source in payload.get("records", [])]
    OUTPUT.write_text(json.dumps({"manifest": payload["manifest"], "records": records}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"records={len(records)} output={OUTPUT}")


if __name__ == "__main__":
    main()

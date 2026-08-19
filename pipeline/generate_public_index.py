#!/usr/bin/env python3
"""Generate the compact, UI-facing view from the auditable canonical dataset."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "benchmarks.json"
OUTPUT = ROOT / "data" / "benchmarks_index.json"


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = []
    for source in payload.get("records", []):
        ranking = {}
        for window, value in source.get("ranking", {}).items():
            ranking[window] = {
                key: value.get(key)
                for key in ("score", "rank", "coverage", "confidence", "datasetDownloadRank", "datasetRankPopulation")
                if key in value
            }
        records.append({
            key: source.get(key)
            for key in (
                "id", "familyId", "name", "oneLine", "area", "applicationDomains", "primaryDomain",
                "industrySectors", "capabilities", "topics", "construction", "annotation", "readiness",
                "releasedAt", "firstSeenAt", "recognitionConfidence", "links", "evidence", "dataStatus", "demo"
            )
        })
        records[-1]["links"] = {key: source["links"].get(key) for key in ("report", "pdf", "project", "code", "data", "hfPaper")}
        attention = source.get("attention") or {}
        records[-1]["attention"] = {
            key: attention.get(key)
            for key in ("asOf", "hfPaperUpvotes", "hfDailySubmittedAt", "githubStars", "hfDatasetDownloads", "hfDatasetLikes")
        }
        records[-1]["evidence"] = {
            "snippet": source.get("evidence", {}).get("snippet", ""),
            "reasonCodes": source.get("evidence", {}).get("reasonCodes", []),
        }
        records[-1]["source"] = {key: source["source"][key] for key in ("type", "id")}
        records[-1]["ranking"] = ranking
        for optional_key in ("motivation", "constructionDetail", "metrics", "curation", "publication", "venueAttempts", "publications"):
            if source.get(optional_key):
                records[-1][optional_key] = source[optional_key]
    OUTPUT.write_text(json.dumps({"manifest": payload["manifest"], "records": records}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"records={len(records)} output={OUTPUT}")


if __name__ == "__main__":
    main()

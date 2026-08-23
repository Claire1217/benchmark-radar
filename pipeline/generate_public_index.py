#!/usr/bin/env python3
"""Generate the compact, UI-facing view from the auditable canonical dataset."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from taxonomy import normalize_taxonomy
except ModuleNotFoundError:  # Imported as pipeline.generate_public_index in tests.
    from pipeline.taxonomy import normalize_taxonomy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "benchmarks.json"
OUTPUT = ROOT / "data" / "benchmarks_index.json"

NON_PUBLISHER_NAMES = {"arxiv", "github", "hugging face", "hf"}


def public_publishers(source: dict) -> list[dict]:
    """Remove hosting platforms and self-named artifacts from team labels."""
    benchmark_name = str(source.get("name") or "").strip().casefold()
    return [
        publisher for publisher in (source.get("publishers") or [])
        if str(publisher.get("name") or "").strip().casefold()
        not in NON_PUBLISHER_NAMES | {benchmark_name}
    ]


def effective_latest_release(records: list[dict], claimed_date: str) -> str:
    """Keep Today on the latest non-empty public release date."""
    candidates = [
        str(record.get("releasedAt"))
        for record in records
        if record.get("releasedAt")
        and str(record["releasedAt"]) <= claimed_date
        and record.get("displayEligible", True) is not False
        and record.get("evaluationMode") != "viewpoint_probe"
    ]
    return max(candidates, default=claimed_date)


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
        for key in ("asOf", "hfPaperUpvotes", "hfDailySubmittedAt", "githubStars", "githubScope", "hfDatasetDownloads", "hfDatasetLikes")
    }
    record["evidence"] = {
        "snippet": source.get("evidence", {}).get("snippet", ""),
        "reasonCodes": source.get("evidence", {}).get("reasonCodes", []),
    }
    record["source"] = {key: source["source"][key] for key in ("type", "id")}
    record["ranking"] = ranking
    for optional_key in ("description", "whyItMatters", "copyGeneration", "motivation", "constructionDetail", "metrics", "detail", "curation", "publication", "venueAttempts", "publications", "watch", "releaseDates", "usageObservations", "evaluationMode", "availability"):
        if source.get(optional_key):
            record[optional_key] = source[optional_key]
    publishers = public_publishers(source)
    if publishers:
        record["publishers"] = publishers
    if "displayEligible" in source:
        record["displayEligible"] = source["displayEligible"]
    record.update(normalize_taxonomy(record))
    return record


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = [project_record(source) for source in payload.get("records", [])]
    manifest = dict(payload["manifest"])
    manifest["latestSourceDate"] = effective_latest_release(records, manifest["dataAsOf"])
    OUTPUT.write_text(json.dumps({"manifest": manifest, "records": records}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"records={len(records)} output={OUTPUT}")


if __name__ == "__main__":
    main()

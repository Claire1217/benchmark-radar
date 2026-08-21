#!/usr/bin/env python3
"""Build a small, honest view of benchmark activity and current tracked use."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RADAR_SOURCE = ROOT / "data" / "benchmarks.json"
LIBRARY_SOURCE = ROOT / "data" / "library_index.json"
OUTPUT = ROOT / "data" / "domain_trends.json"


def tracked_use_score(provider_count: int, tracked_models: int) -> float | None:
    """Combine independent lab breadth with catalog model breadth.

    A provider multiplies rather than merely breaks ties, while log scaling stops
    very large catalog counts from overwhelming broad official-report coverage.
    Missing model coverage stays missing instead of being treated as zero.
    """
    if tracked_models <= 0:
        return None
    breadth = max(provider_count, 1)
    return round(breadth * math.log2(tracked_models + 1), 2)


def month_start(value: date) -> date:
    return value.replace(day=1)


def previous_month(value: date) -> date:
    return (value.replace(day=1) - timedelta(days=1)).replace(day=1)


def month_range(start: date, end: date) -> list[date]:
    months = []
    cursor = month_start(start)
    while cursor <= end:
        months.append(cursor)
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return months


def main() -> None:
    radar_payload = json.loads(RADAR_SOURCE.read_text(encoding="utf-8"))
    radar_records = radar_payload.get("records", [])
    library_records = json.loads(LIBRARY_SOURCE.read_text(encoding="utf-8")).get("records", [])
    manifest = radar_payload["manifest"]
    as_of = date.fromisoformat(manifest.get("latestSourceDate", manifest["dataAsOf"]))
    start = as_of - timedelta(days=89)
    months = month_range(start, as_of)
    current_month = month_start(as_of)
    prior_month = previous_month(as_of)
    domains = sorted({record.get("primaryDomain") for record in radar_records + library_records if record.get("primaryDomain")})

    series = []
    for domain in domains:
        domain_releases = [record for record in radar_records if record.get("primaryDomain") == domain]
        monthly_families: dict[str, set[str]] = {month.isoformat(): set() for month in months}
        for record in domain_releases:
            released = date.fromisoformat(record["releasedAt"])
            if start <= released <= as_of:
                monthly_families.setdefault(month_start(released).isoformat(), set()).add(record.get("familyId") or record["id"])
        monthly = [
            {"month": month.isoformat(), "count": len(monthly_families.get(month.isoformat(), set()))}
            for month in months
        ]

        domain_library = [
            record for record in library_records
            if record.get("primaryDomain") == domain
            and record.get("displayEligible", True) is not False
            and record.get("dataStatus") != "catalog-listed-unverified"
        ]
        landmarks = []
        for record in domain_library:
            reports = record.get("modelReportReferences") or []
            providers = sorted({item.get("provider") for item in reports if item.get("provider")})
            tracked_models = int(record.get("catalogModelCount") or 0)
            if tracked_models or providers:
                score = tracked_use_score(len(providers), tracked_models)
                landmarks.append({
                    "id": record["id"],
                    "name": record["name"],
                    "trackedModels": tracked_models,
                    "providers": providers,
                    "providerCount": len(providers),
                    "trackedUseScore": score,
                    "modelCoverageAvailable": tracked_models > 0,
                    "readiness": record.get("readiness"),
                })
        landmarks.sort(
            key=lambda item: (
                item["modelCoverageAvailable"],
                item["trackedUseScore"] or 0,
                item["providerCount"],
                item["trackedModels"],
            ),
            reverse=True,
        )
        tracked_total = sum(item["trackedModels"] for item in landmarks)
        top_five_total = sum(item["trackedModels"] for item in sorted(landmarks, key=lambda item: item["trackedModels"], reverse=True)[:5])
        concentration = round(100 * top_five_total / tracked_total) if tracked_total else None
        counts = Counter({item["month"]: item["count"] for item in monthly})
        series.append({
            "domain": domain,
            "monthlyNewFamilies": monthly,
            "currentMonthReleases": counts[current_month.isoformat()],
            "previousMonthReleases": counts[prior_month.isoformat()],
            "trackedBenchmarkCount": len(landmarks),
            "trackedModelEntries": tracked_total,
            "topFiveShare": concentration,
            "topBenchmarks": landmarks[:8],
        })

    series.sort(key=lambda item: (item["trackedModelEntries"], item["currentMonthReleases"]), reverse=True)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": "2.0",
        "asOf": as_of.isoformat(),
        "releaseCoverageStart": start.isoformat(),
        "releaseMetric": "new reusable benchmark families by first public release month",
        "currentUseMetric": "current catalog model coverage plus source-linked official model-report references",
        "currentUseRanking": "official provider breadth multiplied by log2(1 + tracked catalog models); missing model coverage ranks after comparable records",
        "interpretation": "Release volume measures evaluation activity, not deployment or technical progress. Current tracked use is a snapshot, not a historical adoption series.",
        "domains": series,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"domains={len(series)} output={OUTPUT}")


if __name__ == "__main__":
    main()

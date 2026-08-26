#!/usr/bin/env python3
"""Build a small, honest view of benchmark activity and current tracked use."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
import json
import math
from pathlib import Path
import re

try:
    from taxonomy import CAPABILITY_GROUP_ORDER, normalize_taxonomy
except ModuleNotFoundError:  # Imported as pipeline.generate_domain_trends in tests.
    from pipeline.taxonomy import CAPABILITY_GROUP_ORDER, normalize_taxonomy


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


def trend_key(kind: str, label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-")
    return f"{kind}:{slug}"


def matches_trend(record: dict, kind: str, label: str) -> bool:
    """Match both release history and current use against the same taxonomy axis."""
    if kind == "overview":
        return record.get("domainScope") == "general"
    if kind == "capability":
        return label in (record.get("capabilityGroups") or [])
    if kind == "application":
        return label in (record.get("applicationDomains") or [])
    raise ValueError(f"unknown trend kind: {kind}")


def trend_definitions(records: list[dict]) -> list[tuple[str, str, str]]:
    present_capabilities = {
        value for record in records for value in (record.get("capabilityGroups") or [])
    }
    application_domains = sorted({
        value for record in records for value in (record.get("applicationDomains") or [])
    })
    definitions = [("overview", "General AI", "General AI")]
    definitions.extend(
        ("capability", label, "General AI capabilities")
        for label in CAPABILITY_GROUP_ORDER
        if label in present_capabilities
    )
    definitions.extend(("application", label, "Application fields") for label in application_domains)
    return definitions


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
    radar_records = [{**record, **normalize_taxonomy(record)} for record in radar_payload.get("records", [])]
    library_records = [
        {**record, **normalize_taxonomy(record)}
        for record in json.loads(LIBRARY_SOURCE.read_text(encoding="utf-8")).get("records", [])
    ]
    manifest = radar_payload["manifest"]
    as_of = date.fromisoformat(manifest.get("latestSourceDate", manifest["dataAsOf"]))
    start = as_of - timedelta(days=89)
    months = month_range(start, as_of)
    current_month = month_start(as_of)
    prior_month = previous_month(as_of)
    series = []
    for kind, label, section in trend_definitions(radar_records + library_records):
        domain_releases = [record for record in radar_records if matches_trend(record, kind, label)]
        monthly_families: dict[str, dict[str, dict]] = {
            month.isoformat(): {} for month in months
        }
        for record in domain_releases:
            released = date.fromisoformat(record["releasedAt"])
            if start <= released <= as_of:
                month_key = month_start(released).isoformat()
                family_key = record.get("familyId") or record["id"]
                monthly_families.setdefault(month_key, {}).setdefault(family_key, record)
        monthly = [
            {
                "month": month.isoformat(),
                "count": len(monthly_families.get(month.isoformat(), {})),
                "benchmarkIds": [
                    record["id"]
                    for record in sorted(
                        monthly_families.get(month.isoformat(), {}).values(),
                        key=lambda item: item["name"].casefold(),
                    )
                ],
            }
            for month in months
        ]

        domain_library = [
            record for record in library_records
            if matches_trend(record, kind, label)
            and record.get("displayEligible", True) is not False
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
                    "dataStatus": record.get("dataStatus"),
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
            "key": trend_key(kind, label),
            "label": label,
            "section": section,
            "kind": kind,
            # Kept for older clients while the site migrates to key/label.
            "domain": label,
            "monthlyNewFamilies": monthly,
            "currentMonthReleases": counts[current_month.isoformat()],
            "previousMonthReleases": counts[prior_month.isoformat()],
            "trackedBenchmarkCount": len(landmarks),
            "trackedModelEntries": tracked_total,
            "topFiveShare": concentration,
            "topBenchmarks": landmarks[:8],
        })

    OUTPUT.write_text(json.dumps({
        "schemaVersion": "3.1",
        "asOf": as_of.isoformat(),
        "releaseCoverageStart": start.isoformat(),
        "releaseMetric": "new reusable benchmark families by first public release month",
        "currentUseMetric": "current catalog model coverage plus source-linked official model-report references",
        "currentUseRanking": "official provider breadth multiplied by log2(1 + tracked catalog models); missing model coverage ranks after comparable records",
        "taxonomy": "General AI is organized by technical capability; application fields are a separate axis. A benchmark may appear on both axes.",
        "interpretation": "Release volume measures evaluation activity, not deployment or technical progress. Current tracked use is a snapshot, not a historical adoption series. Catalog-only coverage remains visibly provisional.",
        "domains": series,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"domains={len(series)} output={OUTPUT}")


if __name__ == "__main__":
    main()

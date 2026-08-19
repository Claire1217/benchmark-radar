#!/usr/bin/env python3
"""Build an auditable domain-release activity dataset without claiming technical progress."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "benchmarks.json"
OUTPUT = ROOT / "data" / "domain_trends.json"


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    as_of = date.fromisoformat(payload["manifest"].get("latestSourceDate", payload["manifest"]["dataAsOf"]))
    start = as_of - timedelta(days=89)
    week_starts: list[date] = []
    cursor = start - timedelta(days=start.weekday())
    while cursor <= as_of:
        week_starts.append(cursor)
        cursor += timedelta(days=7)

    domains = sorted({record["primaryDomain"] for record in records})
    series = []
    for domain in domains:
        domain_records = [record for record in records if record["primaryDomain"] == domain]
        weekly = Counter(
            (released - timedelta(days=released.weekday())).isoformat()
            for released in (date.fromisoformat(record["releasedAt"]) for record in domain_records)
            if start <= released <= as_of
        )
        recent_start = as_of - timedelta(days=29)
        previous_start = as_of - timedelta(days=59)
        recent = sum(recent_start <= date.fromisoformat(record["releasedAt"]) <= as_of for record in domain_records)
        previous = sum(previous_start <= date.fromisoformat(record["releasedAt"]) < recent_start for record in domain_records)
        evidence_count = recent + previous
        series.append({
            "domain": domain,
            "weeklyNewFamilies": [{"week": week.isoformat(), "count": weekly[week.isoformat()]} for week in week_starts],
            "recent30": recent,
            "previous30": previous,
            "smoothedGrowthLog2": round(math.log2((recent + 1) / (previous + 1)), 3),
            "confidence": "Medium" if evidence_count >= 15 else "Low" if evidence_count < 5 else "Moderate",
            "evidenceCount60d": evidence_count,
        })

    OUTPUT.write_text(json.dumps({
        "schemaVersion": "1.0",
        "asOf": as_of.isoformat(),
        "windowDays": 90,
        "metric": "new benchmark families by first public release date",
        "interpretation": "Evaluation-activity proxy only; not a measure of technical progress or benchmark quality.",
        "domains": sorted(series, key=lambda item: (item["recent30"], item["evidenceCount60d"]), reverse=True),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"domains={len(series)} output={OUTPUT}")


if __name__ == "__main__":
    main()

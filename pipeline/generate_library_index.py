#!/usr/bin/env python3
"""Generate the all-time Library without changing the recent Radar feed."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from generate_public_index import project_record


ROOT = Path(__file__).resolve().parents[1]
RECENT = ROOT / "data" / "benchmarks.json"
CLASSICS = ROOT / "data" / "library_records.json"
OUTPUT = ROOT / "data" / "library_index.json"


def public_classic(record: dict, classics: dict) -> dict:
    release = record.get("firstRelease") or {}
    if release.get("date"):
        released_at = release["date"]
        precision = "day"
    elif release.get("year"):
        # Compatibility sort key for the current static client. `firstRelease`
        # and `releaseDatePrecision` remain the authoritative display fields.
        released_at = f"{int(release['year']):04d}-01-01"
        precision = "year"
    else:
        released_at = "0001-01-01"
        precision = "unknown"
    links = record.get("links") or {}
    source_items = record.get("sourceAttribution") or []
    report = links.get("paper") or links.get("project") or (source_items[0].get("url") if source_items else None)
    readiness = "Runnable" if links.get("code") else "Inspectable" if links.get("project") else "Paper only"
    kind = "variant" if record.get("recordType") == "variant" else "family"
    result = {
        "id": record["id"],
        "familyId": record["familyId"],
        "name": record["name"],
        "oneLine": f"Established benchmark {kind} · {record['area']}.",
        "area": record["area"],
        "applicationDomains": [record["primaryDomain"]],
        "primaryDomain": record["primaryDomain"],
        "industrySectors": [],
        "capabilities": [],
        "topics": [record["area"]],
        "construction": "Unknown",
        "annotation": "Unknown",
        "readiness": readiness,
        "releasedAt": released_at,
        "releaseDatePrecision": precision,
        "firstRelease": release,
        "firstSeenAt": classics.get("reviewedAt"),
        "recognitionConfidence": 1.0,
        "links": {
            "report": report,
            "pdf": None,
            "project": links.get("project"),
            "code": links.get("code"),
            "data": links.get("data"),
            "hfPaper": None,
        },
        "evidence": {
            "snippet": "Reviewed Library record; follow the linked benchmark source for its definition.",
            "reasonCodes": ["editorial Library seed", "source attribution retained"],
        },
        "dataStatus": record.get("dataStatus"),
        "demo": False,
        "attention": {},
        "source": {"type": "library", "id": record["id"]},
        "ranking": {},
        "recordType": record.get("recordType"),
        "aliases": record.get("aliases", []),
        "sourceAttribution": source_items,
        "adoptionRefs": record.get("adoptionRefs", []),
        "modelReportReferences": [
            {"sourceId": ref, "url": classics["modelReportSources"][ref]}
            for ref in record.get("adoptionRefs", [])
        ],
        "catalogDiscoveryRefs": record.get("catalogDiscoveryRefs", []),
        "catalogDiscoverySources": [
            {"sourceId": ref, "url": classics["catalogsConsulted"][ref]}
            for ref in record.get("catalogDiscoveryRefs", [])
        ],
        "usageObservations": record.get("usageObservations", []),
    }
    for key in ("variantOf", "variantOfExternal", "versionPolicy"):
        if record.get(key):
            result[key] = record[key]
    return result


def main() -> None:
    recent = json.loads(RECENT.read_text(encoding="utf-8"))
    classics = json.loads(CLASSICS.read_text(encoding="utf-8"))
    # A reviewed Library record wins on collision. Radar remains untouched.
    recent_records = [project_record(record) for record in recent.get("records", [])]
    classic_records = [public_classic(record, classics) for record in classics.get("records", [])]
    by_id = {record["id"]: record for record in recent_records}
    by_id.update({record["id"]: record for record in classic_records})
    records = sorted(by_id.values(), key=lambda item: (item.get("name", "").casefold(), item["id"]))
    payload = {
        "manifest": {
            "schemaVersion": "1.0",
            "dataAsOf": recent["manifest"].get("dataAsOf", date.today().isoformat()),
            "recordCount": len(records),
            "classicRecordCount": len(classics.get("records", [])),
            "recentRecordCount": len(recent.get("records", [])),
            "scope": "all-time reviewed Library plus recent Radar records",
        },
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"records={len(records)} classics={payload['manifest']['classicRecordCount']} output={OUTPUT}")


if __name__ == "__main__":
    main()

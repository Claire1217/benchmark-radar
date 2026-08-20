#!/usr/bin/env python3
"""Generate the all-time Library without changing the recent Radar feed."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from generate_public_index import project_record
from taxonomy import normalize_taxonomy


ROOT = Path(__file__).resolve().parents[1]
RECENT = ROOT / "data" / "benchmarks.json"
CLASSICS = ROOT / "data" / "library_records.json"
CATALOGS = ROOT / "data" / "catalog_records.json"
OUTPUT = ROOT / "data" / "library_index.json"

MODEL_REPORT_LABELS = {
    "openai-gpt5": {"provider": "OpenAI", "model": "GPT-5"},
    "anthropic-claude4": {"provider": "Anthropic", "model": "Claude 4"},
    "google-gemini25": {"provider": "Google DeepMind", "model": "Gemini 2.5"},
    "deepseek-v3": {"provider": "DeepSeek", "model": "DeepSeek-V3"},
}


def normalized_name(value: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", "", ascii_name)


def catalog_legacy_taxonomy(categories: list[str]) -> tuple[str, str, list[str], list[str]]:
    values = {value.casefold() for value in categories}
    topics = [value.title() for value in categories]
    capabilities: list[str] = []
    if values & {"tool calling"}:
        area, capabilities = "Agents & Tool Use", ["Tool use"]
    elif values & {"agents", "agent", "research"}:
        area = "Agents & Tool Use"
    elif values & {"code", "coding", "frontend development"}:
        area = "Code & Software"
    elif values & {"math", "mathematics", "spatial reasoning", "spatial"}:
        area = "Mathematical Reasoning"
    elif values & {"long context", "memory"}:
        area = "Long Context"
    elif values & {"instruction following", "structured output"}:
        area = "Instruction Following"
    elif values & {"multimodal", "image to text", "image-generation", "text-to-image"}:
        area = "Multimodal"
    elif values & {"vision", "video", "3d"}:
        area = "Vision & 3D"
    elif values & {"audio", "speech to text"}:
        area = "Speech & Audio"
    elif values & {"safety", "privacy"}:
        area = "Safety & Trustworthiness"
    elif values & {"systems"}:
        area = "Systems & Efficiency"
    elif values & {"robotics", "embodied"}:
        area = "Robotics & Embodied AI"
    else:
        area = "Language & Knowledge"

    if values & {"finance", "economics"}:
        domain = "Finance"
    elif values & {"healthcare", "medical", "biology"}:
        domain = "Health & Biomedicine"
    elif values & {"robotics", "embodied"}:
        domain = "Robotics & Embodied AI"
    elif values & {"legal"}:
        domain = "Law & Government"
    elif values & {"science", "physics", "chemistry", "research"}:
        domain = "Scientific Research & AI for Science"
    else:
        domain = "General AI"
    return area, domain, capabilities, topics


def public_catalog(record: dict, first_seen: str) -> dict:
    area, domain, capabilities, topics = catalog_legacy_taxonomy(record.get("categories", []))
    sources = record.get("sourceRecords", [])
    preferred = next((source for source in sources if source.get("paperUrl")), None) or sources[0]
    report = preferred.get("paperUrl") or preferred.get("url")
    result = {
        "id": record["id"],
        "familyId": "catalog_family_" + hashlib.sha256(record["normalizedName"].encode()).hexdigest()[:16],
        "name": record["name"],
        "oneLine": record.get("description") or "Catalog-listed benchmark; original-source verification is pending.",
        "description": record.get("description") or "Catalog-listed benchmark; original-source verification is pending.",
        "area": area,
        "applicationDomains": [domain],
        "primaryDomain": domain,
        "industrySectors": [],
        "capabilities": capabilities,
        "topics": topics,
        "construction": "Unknown",
        "annotation": "Unknown",
        "readiness": "Paper only",
        "releasedAt": "0001-01-01",
        "releaseDatePrecision": "unknown",
        "firstRelease": {"year": None, "date": None},
        "firstSeenAt": first_seen[:10],
        "recognitionConfidence": 0.5,
        "links": {"report": report, "pdf": None, "project": None, "code": None, "data": None, "hfPaper": None},
        "evidence": {"snippet": "Listed by BenchLM or llm-stats; original-source verification is pending.", "reasonCodes": ["external catalog listing"]},
        "dataStatus": "catalog-listed-unverified",
        "demo": False,
        "attention": {},
        "source": {"type": "catalog", "id": record["id"]},
        "ranking": {},
        "recordType": "catalog-entry",
        "aliases": [],
        "sourceAttribution": [{"role": source["catalog"], "url": source["url"]} for source in sources],
        "catalogSources": sources,
        "catalogCategories": record.get("categories", []),
        "catalogModelCount": record.get("modelCount", 0),
        "catalogStarCount": record.get("starCount", 0),
        "modelReportReferences": [],
        "usageObservations": [],
    }
    result.update(normalize_taxonomy(result))
    return result


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
            {
                "sourceId": ref,
                "url": classics["modelReportSources"][ref],
                **MODEL_REPORT_LABELS.get(ref, {"provider": ref, "model": "Model report"}),
            }
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
    result.update(normalize_taxonomy(result))
    return result


def main() -> None:
    recent = json.loads(RECENT.read_text(encoding="utf-8"))
    classics = json.loads(CLASSICS.read_text(encoding="utf-8"))
    catalogs = json.loads(CATALOGS.read_text(encoding="utf-8")) if CATALOGS.exists() else {"records": []}
    # A reviewed Library record wins on collision. Radar remains untouched.
    recent_records = [project_record(record) for record in recent.get("records", [])]
    classic_records = [public_classic(record, classics) for record in classics.get("records", [])]
    by_id = {record["id"]: record for record in recent_records}
    by_id.update({record["id"]: record for record in classic_records})
    identities: dict[str, dict] = {}
    for item in by_id.values():
        for name in [item.get("name", ""), *(item.get("aliases") or [])]:
            if normalized := normalized_name(name):
                identities.setdefault(normalized, item)
    catalog_only = 0
    catalog_merged = 0
    for source in catalogs.get("records", []):
        existing = identities.get(source["normalizedName"])
        if existing:
            existing["catalogSources"] = source.get("sourceRecords", [])
            existing["catalogCategories"] = source.get("categories", [])
            existing["catalogModelCount"] = max(existing.get("catalogModelCount", 0), source.get("modelCount", 0))
            existing["catalogStarCount"] = max(existing.get("catalogStarCount", 0), source.get("starCount", 0))
            catalog_merged += 1
            continue
        item = public_catalog(source, catalogs.get("retrievedAt", date.today().isoformat()))
        by_id[item["id"]] = item
        identities[source["normalizedName"]] = item
        catalog_only += 1
    records = sorted(by_id.values(), key=lambda item: (item.get("name", "").casefold(), item["id"]))
    payload = {
        "manifest": {
            "schemaVersion": "1.0",
            "dataAsOf": recent["manifest"].get("dataAsOf", date.today().isoformat()),
            "recordCount": len(records),
            "classicRecordCount": len(classics.get("records", [])),
            "catalogSourceRecordCount": sum(source.get("recordCount", 0) for source in catalogs.get("sources", {}).values()),
            "catalogEntityCount": len(catalogs.get("records", [])),
            "catalogMergedCount": catalog_merged,
            "catalogOnlyCount": catalog_only,
            "recentRecordCount": len(recent.get("records", [])),
            "scope": "all-time Library, complete BenchLM and llm-stats catalogs, plus recent Radar records",
        },
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(
        f"records={len(records)} classics={payload['manifest']['classicRecordCount']} "
        f"catalog_merged={catalog_merged} catalog_only={catalog_only} output={OUTPUT}"
    )


if __name__ == "__main__":
    main()

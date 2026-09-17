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
from library_identity import merge_library_identities
from library_release_dates import apply_release_dates
from library_source_reviews import apply_source_reviews
from research_directions import annotate_records, direction_manifest
from research_topics import annotate_topics, topic_manifest


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
    ascii_name = unicodedata.normalize("NFKD", value.replace("+", " plus ").replace("τ", "tau").replace("²", "2").replace("³", "3")).encode("ascii", "ignore").decode().casefold()
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
        "firstSeenAt": record.get("firstSeenAt", first_seen[:10]),
        "recognitionConfidence": 0.5,
        "links": {"report": report, "pdf": None, "project": None, "code": None, "data": None, "hfPaper": None},
        "evidence": {"snippet": "Listed in a public benchmark catalog; original-source verification is pending.", "reasonCodes": ["external catalog listing"]},
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
    if record.get("releasedAt") and record.get("releaseEvidenceUrl"):
        result["releasedAt"] = record["releasedAt"]
        result["releaseDatePrecision"] = "day"
        result["firstRelease"] = {"year": int(record["releasedAt"][:4]), "date": record["releasedAt"], "sourceUrl": record["releaseEvidenceUrl"]}
    result["aliases"] = record.get("aliases", [])
    result["links"].update(record.get("links", {}))
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
        "oneLine": record.get("description") or f"Established benchmark {kind} · {record['area']}.",
        "description": record.get("description"),
        "descriptionProvenance": record.get("descriptionProvenance"),
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
        existing = next((identities[key] for name in [source["name"], *source.get("aliases", [])] if (key := normalized_name(name)) in identities), None)
        if existing:
            existing["catalogSources"] = list({(ref["catalog"], ref.get("sourceId") or ref["url"]): ref for ref in [*existing.get("catalogSources", []), *source.get("sourceRecords", [])]}.values())
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
    identity_path = ROOT / "data" / "library_identity_merges.json"
    decisions = json.loads(identity_path.read_text()) if identity_path.exists() else {}
    records, identity_redirects = merge_library_identities(records, decisions)
    release_path = ROOT / "data" / "library_release_dates.json"
    from repository_index import load_and_apply
    load_and_apply(records, ROOT / "data")
    reviewed_additions = 0
    review_path = ROOT / "data" / "library_source_reviews.json"
    if review_path.exists():
        reviews = json.loads(review_path.read_text())
        reviewed_additions = len(reviews.get("additions", []))
        apply_source_reviews(records, reviews)
    if release_path.exists():
        apply_release_dates(records, json.loads(release_path.read_text()))
    annotate_records(records)
    annotate_topics(records)
    # Both surfaces use the merged Library classification, including catalog evidence.
    public_path = ROOT / "data" / "benchmarks_index.json"
    if public_path.exists():
        public = json.loads(public_path.read_text())
        canonical = {r["id"]: r for r in records}
        for row in public["records"]:
            current = canonical.get(row["id"])
            if current:
                for key in ("researchDirections", "researchDirectionEvidence", "researchClassification", "researchFacets", "benchmarkTaxonomy", "researchTopics", "researchTopicEvidence", "topicClassification", "evaluationRole", "sourceAudit", "repositoryScopeReview"):
                    if key in current: row[key] = current[key]
                if current.get("repositoryScopeReview"):
                    row.setdefault("attention",{})["githubScope"] = current["repositoryScopeReview"]["scope"]
        public["manifest"]["researchTaxonomy"] = direction_manifest(public["records"])
        public["manifest"]["topicTaxonomy"] = topic_manifest(public["records"])
        public_path.write_text(json.dumps(public, ensure_ascii=False, separators=(",", ":")) + "\n")
    payload = {
        "manifest": {
            "schemaVersion": "1.0",
            "researchTaxonomy": direction_manifest(records),
            "topicTaxonomy": topic_manifest(records),
            "dataAsOf": recent["manifest"].get("dataAsOf", date.today().isoformat()),
            "recordCount": len(records),
            "classicRecordCount": len(classics.get("records", [])),
            "reviewedAdditionCount": reviewed_additions,
            "catalogSourceRecordCount": sum(source.get("recordCount", 0) for source in catalogs.get("sources", {}).values()),
            "catalogEntityCount": len(catalogs.get("records", [])),
            "catalogMergedCount": catalog_merged,
            "catalogOnlyCount": sum(r.get("recordType") == "catalog-entry" for r in records),
            "identityRedirects": identity_redirects,
            "identityMergeCount": len(identity_redirects),
            "recentRecordCount": len(recent.get("records", [])),
            "scope": "all-time Library, BenchLM and llm-stats catalogs, audited supplemental public catalogs, and recent Radar records",
        },
        "records": records,
    }
    # Attach imported evidence without converting it into popularity or adoption scores.
    if (ROOT / "data/usage/manifest.json").exists():
        from usage_store import UsageStore
        usage = UsageStore(ROOT / "data", library=records)
        for record in records:
            keys = usage.entities[record["id"]].get("usageSourceIds", [])
            if keys:
                record["reportedUsage"] = {**usage.summary(keys), "sourceIds": keys}
        payload["manifest"]["usageDatasetVersion"] = usage.manifest["datasetVersion"]
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(
        f"records={len(records)} classics={payload['manifest']['classicRecordCount']} "
        f"catalog_merged={catalog_merged} catalog_only={catalog_only} output={OUTPUT}"
    )


if __name__ == "__main__":
    main()

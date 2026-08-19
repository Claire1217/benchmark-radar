#!/usr/bin/env python3
"""Build the reviewed all-time Library from editorial seeds.

The builder is deterministic. Model-report and catalog references are retained
as evidence pointers, not converted into dated usage observations unless an
editorial seed supplies an explicit observation date.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "data" / "library_seed_records.json"
RADAR_PATH = ROOT / "data" / "benchmarks.json"
OUTPUT_PATH = ROOT / "data" / "library_records.json"
USAGE_CONTEXTS = {"model-report", "paper", "leaderboard", "industry-evaluation"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def valid_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def normalized_official_url(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value.strip())
    host = parts.netloc.casefold().removeprefix("www.")
    path = re.sub(r"/+", "/", parts.path).rstrip("/")
    if host == "arxiv.org":
        match = re.search(r"/(?:abs|pdf)/([^/]+?)(?:\.pdf)?$", path, re.I)
        if match:
            return f"arxiv.org/{match.group(1).split('v')[0].casefold()}"
    if host == "github.com":
        path = path.removesuffix(".git").casefold()
    return urlunsplit(("https", host, path, "", ""))


def record_names(record: dict[str, Any]) -> set[str]:
    return {
        normalized_name(value)
        for value in [record.get("name", ""), *record.get("aliases", [])]
        if value
    }


def record_official_urls(record: dict[str, Any]) -> set[str]:
    values = list((record.get("links") or {}).values())
    values.extend(item.get("url") for item in record.get("sourceAttribution", []))
    source_url = (record.get("source") or {}).get("url")
    if source_url:
        values.append(source_url)
    return {url for value in values if (url := normalized_official_url(value))}


def radar_duplicate(seed_record: dict[str, Any], radar_records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Require both an identity-name match and a shared official link.

    Name-only matching is unsafe: a new variant may be misnamed as its parent
    by an automated paper indexer. Link-only matching is unsafe because variants
    often share repositories with their parent family.
    """
    names = record_names(seed_record)
    urls = record_official_urls(seed_record)
    for radar_record in radar_records:
        if names & record_names(radar_record) and urls & record_official_urls(radar_record):
            return radar_record
    return None


def validate_seed(seed: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    reports = seed.get("modelReportSources", {})
    catalogs = seed.get("catalogsConsulted", {})
    records = seed.get("records", [])
    ids = {record.get("id") for record in records}
    by_id = {record.get("id"): record for record in records}
    if len(ids) != len(records) or None in ids:
        errors.append("seed record ids must be present and unique")
    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        for key in ("id", "familyId", "name", "recordType", "primaryDomain", "area", "firstRelease", "links", "sourceAttribution"):
            if key not in record:
                errors.append(f"{prefix}: missing {key}")
        if record.get("recordType") not in {"family", "variant"}:
            errors.append(f"{prefix}: invalid recordType")
        if record.get("recordType") == "variant" and not (record.get("variantOf") or record.get("variantOfExternal")):
            errors.append(f"{prefix}: variant needs variantOf or variantOfExternal")
        if record.get("variantOf") and record["variantOf"] not in ids:
            errors.append(f"{prefix}: unknown variantOf {record['variantOf']}")
        if record.get("variantOf") in by_id and by_id[record["variantOf"]].get("familyId") != record.get("familyId"):
            errors.append(f"{prefix}: variant and parent must share familyId")
        release = record.get("firstRelease") or {}
        if release.get("date") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(release["date"])):
            errors.append(f"{prefix}: invalid firstRelease.date")
        if release.get("date") and release.get("year") != int(str(release["date"])[:4]):
            errors.append(f"{prefix}: firstRelease year/date mismatch")
        if not record.get("sourceAttribution"):
            errors.append(f"{prefix}: sourceAttribution cannot be empty")
        for key, value in (record.get("links") or {}).items():
            if value is not None and not valid_http_url(value):
                errors.append(f"{prefix}: invalid links.{key}")
        for source_index, source in enumerate(record.get("sourceAttribution", [])):
            if not source.get("role") or not valid_http_url(source.get("url")):
                errors.append(f"{prefix}.sourceAttribution[{source_index}]: invalid source")
        for ref in record.get("adoptionRefs", []):
            if ref not in reports:
                errors.append(f"{prefix}: unknown adoptionRef {ref}")
        for ref in record.get("catalogDiscoveryRefs", []):
            if ref not in catalogs:
                errors.append(f"{prefix}: unknown catalogDiscoveryRef {ref}")
        for observation in record.get("usageObservations", []):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(observation.get("observedAt", ""))):
                errors.append(f"{prefix}: usage observation needs explicit observedAt")
            if not valid_http_url(observation.get("sourceUrl")):
                errors.append(f"{prefix}: usage observation needs sourceUrl")
            if not str(observation.get("organization", "")).strip():
                errors.append(f"{prefix}: usage observation needs organization")
            if observation.get("contextType") not in USAGE_CONTEXTS:
                errors.append(f"{prefix}: usage observation has invalid contextType")
    for key, value in {**reports, **catalogs}.items():
        if not valid_http_url(value):
            errors.append(f"source registry {key}: invalid URL")
    return errors


def build_payload(seed: dict[str, Any], radar: dict[str, Any]) -> dict[str, Any]:
    errors = validate_seed(seed)
    if errors:
        raise ValueError("\n".join(errors))
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    radar_records = radar.get("records", [])
    for source in seed.get("records", []):
        duplicate = radar_duplicate(source, radar_records)
        if duplicate:
            excluded.append({
                "seedId": source["id"],
                "name": source["name"],
                "radarId": duplicate["id"],
                "radarSourceId": str(duplicate.get("source", {}).get("id", "")),
                "reason": "normalized name/alias and official link both match",
            })
            continue
        record = dict(source)
        # Empty is intentional: report citations are evidence of adoption, but
        # the seed does not assert a dated observation event.
        record["usageObservations"] = list(source.get("usageObservations", []))
        record["dataStatus"] = "editorial-source-reviewed"
        kept.append(record)
    return {
        "schemaVersion": "1.1",
        "description": seed.get("description"),
        "reviewedAt": seed.get("reviewedAt"),
        "modelReportSources": seed.get("modelReportSources", {}),
        "catalogsConsulted": seed.get("catalogsConsulted", {}),
        "generation": {
            "source": "data/library_seed_records.json",
            "radarDataAsOf": radar.get("manifest", {}).get("dataAsOf"),
            "deduplicationRule": "normalized name or alias AND normalized official link",
            "inputRecordCount": len(seed.get("records", [])),
            "recordCount": len(kept),
            "excludedRadarDuplicates": excluded,
        },
        "records": kept,
    }


def main() -> None:
    payload = build_payload(read_json(SEED_PATH), read_json(RADAR_PATH))
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"library_records={len(payload['records'])} "
        f"radar_duplicates={len(payload['generation']['excludedRadarDuplicates'])} output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()

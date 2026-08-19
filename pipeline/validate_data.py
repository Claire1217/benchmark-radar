#!/usr/bin/env python3
"""Validate public snapshot invariants without third-party dependencies."""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from urllib.parse import urlparse

from build_library_records import SEED_PATH, build_payload


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data" / "benchmarks.json"
PUBLIC = ROOT / "data" / "benchmarks_index.json"
LIBRARY = ROOT / "data" / "library_records.json"
LIBRARY_PUBLIC = ROOT / "data" / "library_index.json"
READINESS = {"Paper only", "Inspectable", "Runnable", "Maintained"}
PUBLICATION = {"accepted", "published", "acceptance_claimed", "publication_reported", "unverified"}
WINDOWS = {"today", "30d", "90d"}
USAGE_CONTEXTS = {"model-report", "paper", "leaderboard", "industry-evaluation"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def valid_date(value: object) -> bool:
    try:
        date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def valid_timestamp(value: object) -> bool:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def valid_url(value: object) -> bool:
    if value is None:
        return True
    parsed = urlparse(str(value))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_record(record: dict, index: int) -> list[str]:
    errors: list[str] = []
    prefix = f"records[{index}]"
    for key in ("id", "familyId", "name", "oneLine", "area", "primaryDomain", "releasedAt", "firstSeenAt", "readiness", "links", "source"):
        if key not in record:
            errors.append(f"{prefix}: missing {key}")
    if record.get("readiness") not in READINESS:
        errors.append(f"{prefix}: invalid readiness {record.get('readiness')!r}")
    for key in ("releasedAt", "firstSeenAt"):
        if not valid_date(record.get(key)):
            errors.append(f"{prefix}: invalid {key}")
    if record.get("indexedAt") and not valid_timestamp(record["indexedAt"]):
        errors.append(f"{prefix}: invalid indexedAt")
    for key, value in (record.get("links") or {}).items():
        if not valid_url(value):
            errors.append(f"{prefix}: invalid links.{key}")
    if "Evaluation" in record.get("capabilities", []):
        errors.append(f"{prefix}: generic Evaluation is not a capability")
    detail = record.get("detail") or {}
    for key in ("leaderboardUrl", "submissionUrl"):
        if detail.get(key) and not valid_url(detail[key]):
            errors.append(f"{prefix}: invalid detail.{key}")
    leaderboard_source = (detail.get("leaderboard") or {}).get("sourceUrl")
    if leaderboard_source and not valid_url(leaderboard_source):
        errors.append(f"{prefix}: invalid detail.leaderboard.sourceUrl")
    publication = record.get("publication") or {}
    if publication and publication.get("status") not in PUBLICATION:
        errors.append(f"{prefix}: invalid publication status")
    ranking = record.get("ranking") or {}
    if set(ranking) - WINDOWS:
        errors.append(f"{prefix}: invalid ranking window")
    watch = record.get("watch") or {}
    if watch and watch.get("status") != "watch":
        errors.append(f"{prefix}: invalid watch status")
    for usage_index, observation in enumerate(record.get("usageObservations", [])):
        usage_prefix = f"{prefix}.usageObservations[{usage_index}]"
        if not valid_date(observation.get("observedAt")):
            errors.append(f"{usage_prefix}: invalid observedAt")
        if not str(observation.get("organization", "")).strip():
            errors.append(f"{usage_prefix}: missing organization")
        if observation.get("contextType") not in USAGE_CONTEXTS:
            errors.append(f"{usage_prefix}: invalid contextType")
        if not valid_url(observation.get("sourceUrl")) or not observation.get("sourceUrl"):
            errors.append(f"{usage_prefix}: invalid sourceUrl")
    return errors


def validate_library_record(record: dict, index: int, library: dict) -> list[str]:
    errors: list[str] = []
    prefix = f"library.records[{index}]"
    for key in ("id", "familyId", "name", "recordType", "primaryDomain", "area", "firstRelease", "links", "sourceAttribution"):
        if key not in record:
            errors.append(f"{prefix}: missing {key}")
    if record.get("recordType") not in {"family", "variant"}:
        errors.append(f"{prefix}: invalid recordType")
    release = record.get("firstRelease") or {}
    if release.get("date") and not valid_date(release["date"]):
        errors.append(f"{prefix}: invalid firstRelease.date")
    for key, value in (record.get("links") or {}).items():
        if not valid_url(value):
            errors.append(f"{prefix}: invalid links.{key}")
    for source_index, source in enumerate(record.get("sourceAttribution", [])):
        if not source.get("role") or not valid_url(source.get("url")) or not source.get("url"):
            errors.append(f"{prefix}.sourceAttribution[{source_index}]: invalid source")
    for ref in record.get("adoptionRefs", []):
        if ref not in library.get("modelReportSources", {}):
            errors.append(f"{prefix}: unknown adoptionRef {ref}")
    for ref in record.get("catalogDiscoveryRefs", []):
        if ref not in library.get("catalogsConsulted", {}):
            errors.append(f"{prefix}: unknown catalogDiscoveryRef {ref}")
    for usage_index, observation in enumerate(record.get("usageObservations", [])):
        usage_prefix = f"{prefix}.usageObservations[{usage_index}]"
        if not valid_date(observation.get("observedAt")):
            errors.append(f"{usage_prefix}: invalid observedAt")
        if not str(observation.get("organization", "")).strip():
            errors.append(f"{usage_prefix}: missing organization")
        if observation.get("contextType") not in USAGE_CONTEXTS:
            errors.append(f"{usage_prefix}: invalid contextType")
        if not valid_url(observation.get("sourceUrl")) or not observation.get("sourceUrl"):
            errors.append(f"{usage_prefix}: invalid sourceUrl")
    return errors


def main() -> None:
    canonical = load(CANONICAL)
    public = load(PUBLIC)
    library = load(LIBRARY)
    library_public = load(LIBRARY_PUBLIC)
    records = canonical.get("records", [])
    library_records = library.get("records", [])
    errors: list[str] = []
    if canonical.get("manifest", {}).get("recordCount") != len(records):
        errors.append("canonical manifest recordCount mismatch")
    if public.get("manifest", {}).get("recordCount") != len(public.get("records", [])):
        errors.append("public manifest recordCount mismatch")
    expected_library_count = len(records) + len(library_records)
    if library_public.get("manifest", {}).get("recordCount") != expected_library_count:
        errors.append("library public manifest recordCount mismatch")
    ids = [record.get("id") for record in records]
    source_ids = [record.get("source", {}).get("id") for record in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate benchmark id")
    if len(source_ids) != len(set(source_ids)):
        errors.append("duplicate source id")
    library_ids = [record.get("id") for record in library_records]
    if len(library_ids) != len(set(library_ids)):
        errors.append("duplicate Library benchmark id")
    if set(ids) & set(library_ids):
        errors.append("Library classic duplicates a Radar record")
    expected_library = build_payload(load(SEED_PATH), canonical)
    if library != expected_library:
        errors.append("library_records.json is stale; run pipeline/build_library_records.py")
    for index, record in enumerate(library_records):
        errors.extend(validate_library_record(record, index, library))
    for index, record in enumerate(records):
        errors.extend(validate_record(record, index))
    if errors:
        raise SystemExit("\n".join(errors[:100]))
    print(f"validated_records={len(records)} library_classics={len(library_records)} library_public={len(library_public.get('records', []))}")


if __name__ == "__main__":
    main()

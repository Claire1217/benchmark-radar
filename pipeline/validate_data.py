#!/usr/bin/env python3
"""Validate public snapshot invariants without third-party dependencies."""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data" / "benchmarks.json"
PUBLIC = ROOT / "data" / "benchmarks_index.json"
READINESS = {"Paper only", "Inspectable", "Runnable", "Maintained"}
PUBLICATION = {"accepted", "published", "acceptance_claimed", "publication_reported", "unverified"}
WINDOWS = {"today", "30d", "90d"}


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
    publication = record.get("publication") or {}
    if publication and publication.get("status") not in PUBLICATION:
        errors.append(f"{prefix}: invalid publication status")
    ranking = record.get("ranking") or {}
    if set(ranking) - WINDOWS:
        errors.append(f"{prefix}: invalid ranking window")
    watch = record.get("watch") or {}
    if watch and watch.get("status") != "watch":
        errors.append(f"{prefix}: invalid watch status")
    return errors


def main() -> None:
    canonical = load(CANONICAL)
    public = load(PUBLIC)
    records = canonical.get("records", [])
    errors: list[str] = []
    if canonical.get("manifest", {}).get("recordCount") != len(records):
        errors.append("canonical manifest recordCount mismatch")
    if public.get("manifest", {}).get("recordCount") != len(public.get("records", [])):
        errors.append("public manifest recordCount mismatch")
    ids = [record.get("id") for record in records]
    source_ids = [record.get("source", {}).get("id") for record in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate benchmark id")
    if len(source_ids) != len(set(source_ids)):
        errors.append("duplicate source id")
    for index, record in enumerate(records):
        errors.extend(validate_record(record, index))
    if errors:
        raise SystemExit("\n".join(errors[:100]))
    print(f"validated_records={len(records)} public_records={len(public.get('records', []))}")


if __name__ == "__main__":
    main()

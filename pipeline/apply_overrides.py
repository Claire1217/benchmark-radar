#!/usr/bin/env python3
"""Reapply reviewed source overrides and generated editorial copy."""

from pathlib import Path
import re

from generate_editorial_copy import public_release_ready, publisher_identity_is_distinct
from index_benchmarks import DATA_PATH, apply_curated_overrides, curated_records, read_json, upsert, write_json


EDITORIAL_COPY_PATH = Path(__file__).resolve().parents[1] / "data/editorial_copy.json"


def restore_official_heading_name(record: dict) -> None:
    """Use a matching README heading to restore capitalization lost in a slug."""
    if (record.get("source") or {}).get("type") != "github" or not str(record.get("name", "")).islower():
        return
    snippet = str((record.get("evidence") or {}).get("snippet") or "")
    normalized = lambda value: re.sub(r"[^a-z0-9]+", "", value.casefold())
    for heading in re.findall(r"(?:^|\s)#\s+([A-Za-z][A-Za-z0-9_.-]+)", snippet):
        if normalized(heading) == normalized(str(record["name"])):
            record["name"] = heading
            return


def apply_editorial_copy(records: list[dict]) -> list[dict]:
    copies = read_json(EDITORIAL_COPY_PATH).get("bySourceId", {}) if EDITORIAL_COPY_PATH.exists() else {}
    for record in records:
        source_id = str(record.get("source", {}).get("id", ""))
        copy = copies.get(source_id)
        if not copy:
            continue
        if copy.get("canonicalName"):
            record["name"] = copy["canonicalName"]
        record["description"] = copy["description"]
        record["whyItMatters"] = copy["whyItMatters"]
        record["oneLine"] = copy["description"]
        publishers = [
            publisher for publisher in copy.get("publishers", [])
            if publisher_identity_is_distinct(
                str(publisher.get("name", "")),
                str(publisher.get("sourceUrl", "")),
                str(record.get("name", "")),
            )
        ]
        if publishers:
            record["publishers"] = publishers
        else:
            record.pop("publishers", None)
        record["copyGeneration"] = {key: copy[key] for key in ("model", "generatedAt", "inputHash")}
    return records


def main() -> None:
    payload = read_json(DATA_PATH)
    # Generated copy fills gaps; source-reviewed overrides always win last.
    records = apply_curated_overrides(apply_editorial_copy(upsert(payload.get("records", []), curated_records())))
    for record in records:
        if not public_release_ready(record):
            record["displayEligible"] = False
        restore_official_heading_name(record)
        record["capabilities"] = [
            capability
            for capability in record.get("capabilities", [])
            if capability != "Evaluation"
        ]
    payload["records"] = records
    payload["manifest"]["recordCount"] = len(payload["records"])
    write_json(DATA_PATH, payload)
    print(f"overrides_applied={len(payload['records'])}")


if __name__ == "__main__":
    main()

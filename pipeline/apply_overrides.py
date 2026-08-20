#!/usr/bin/env python3
"""Reapply reviewed source overrides and generated editorial copy."""

from pathlib import Path

from index_benchmarks import DATA_PATH, apply_curated_overrides, curated_records, read_json, upsert, write_json


EDITORIAL_COPY_PATH = Path(__file__).resolve().parents[1] / "data/editorial_copy.json"


def apply_editorial_copy(records: list[dict]) -> list[dict]:
    copies = read_json(EDITORIAL_COPY_PATH).get("bySourceId", {}) if EDITORIAL_COPY_PATH.exists() else {}
    for record in records:
        source_id = str(record.get("source", {}).get("id", ""))
        copy = copies.get(source_id)
        if not copy:
            continue
        record["description"] = copy["description"]
        record["whyItMatters"] = copy["whyItMatters"]
        record["oneLine"] = copy["description"]
        if copy.get("publishers"):
            record["publishers"] = copy["publishers"]
        record["copyGeneration"] = {key: copy[key] for key in ("model", "generatedAt", "inputHash")}
    return records


def main() -> None:
    payload = read_json(DATA_PATH)
    records = apply_editorial_copy(apply_curated_overrides(upsert(payload.get("records", []), curated_records())))
    for record in records:
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

#!/usr/bin/env python3
"""Reapply reviewed primary-source overrides without refetching arXiv."""

from index_benchmarks import DATA_PATH, apply_curated_overrides, curated_records, read_json, upsert, write_json


def main() -> None:
    payload = read_json(DATA_PATH)
    records = apply_curated_overrides(upsert(payload.get("records", []), curated_records()))
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

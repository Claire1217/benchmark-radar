#!/usr/bin/env python3
"""Snapshot the complete public BenchLM and llm-stats benchmark catalogs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "catalog_records.json"
BENCHLM_URL = "https://benchlm.ai/data/benchmarks.json"
LLM_STATS_URL = "https://llm-stats.com/benchmarks"
MIN_EXPECTED_ROWS = {"benchlm": 100, "llm-stats": 100}


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "benchmark-radar/1.0 (+https://github.com/Claire1217/benchmark-radar)"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def normalized_name(value: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", "", ascii_name)


def parse_llm_stats(body: bytes) -> list[dict]:
    html = body.decode("utf-8", errors="replace")
    for match in re.finditer(r"self\.__next_f\.push\((\[.*?\])\)</script>", html, re.S):
        try:
            chunk = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if len(chunk) < 2 or not isinstance(chunk[1], str) or '"initialBenchmarks":' not in chunk[1]:
            continue
        serialized = chunk[1]
        start = serialized.index('"initialBenchmarks":') + len('"initialBenchmarks":')
        records, _ = json.JSONDecoder().raw_decode(serialized[start:])
        if not isinstance(records, list):
            break
        return records
    raise ValueError("llm-stats public catalog payload was not found")


def build_payload(benchlm_body: bytes, llm_stats_body: bytes, retrieved_at: str) -> dict:
    benchlm_payload = json.loads(benchlm_body)
    benchlm_rows = benchlm_payload.get("items", [])
    llm_stats_rows = parse_llm_stats(llm_stats_body)
    if len(benchlm_rows) < MIN_EXPECTED_ROWS["benchlm"]:
        raise ValueError(f"BenchLM catalog is unexpectedly small: {len(benchlm_rows)} rows")
    if len(llm_stats_rows) < MIN_EXPECTED_ROWS["llm-stats"]:
        raise ValueError(f"llm-stats catalog is unexpectedly small: {len(llm_stats_rows)} rows")
    grouped: dict[str, dict] = {}

    def group(name: str) -> dict:
        key = normalized_name(name)
        if not key:
            key = "unnamed-" + hashlib.sha256(name.encode()).hexdigest()[:12]
        return grouped.setdefault(key, {
            "id": "catalog_" + hashlib.sha256(key.encode()).hexdigest()[:16],
            "normalizedName": key,
            "name": name.strip() or "Unnamed benchmark",
            "description": "",
            "categories": [],
            "modality": None,
            "modelCount": 0,
            "starCount": 0,
            "sourceRecords": [],
        })

    for row in benchlm_rows:
        item = group(str(row.get("name") or row.get("fullName") or row.get("benchmarkKey") or ""))
        if not item["description"] and row.get("description"):
            item["description"] = row["description"]
        item["categories"] = list(dict.fromkeys(item["categories"] + [str(row.get("category") or "").replace("_", " ")]))
        item["sourceRecords"].append({
            "catalog": "benchlm",
            "sourceId": row.get("benchmarkKey"),
            "url": row.get("url") or f"https://benchlm.ai/benchmarks/{row.get('benchmarkKey')}",
            "paperUrl": row.get("paperUrl"),
            "year": row.get("year"),
            "fullName": row.get("fullName"),
            "format": row.get("format"),
            "tasks": row.get("tasks"),
            "successorKey": row.get("successorKey"),
        })

    for row in llm_stats_rows:
        item = group(str(row.get("name") or row.get("benchmark_id") or ""))
        if row.get("description"):
            item["description"] = row["description"]
        item["categories"] = list(dict.fromkeys(item["categories"] + [str(value).replace("_", " ") for value in row.get("categories", []) if value]))
        item["modality"] = row.get("modality") or item["modality"]
        item["modelCount"] = max(item["modelCount"], int(row.get("model_count") or 0))
        item["starCount"] = max(item["starCount"], int(row.get("star_count") or 0))
        item["sourceRecords"].append({
            "catalog": "llm-stats",
            "sourceId": row.get("benchmark_id"),
            "url": f"https://llm-stats.com/benchmarks/{row.get('benchmark_id')}",
            "datasetSlug": row.get("dataset_slug"),
            "versionCount": row.get("version_count"),
            "subsetCount": row.get("subset_count"),
            "rowCount": row.get("latest_version_row_count"),
            "updatedAt": row.get("updated_at"),
            "community": row.get("is_community"),
        })

    for item in grouped.values():
        item["categories"] = [value for value in item["categories"] if value]
    records = sorted(grouped.values(), key=lambda row: (row["name"].casefold(), row["id"]))
    return {
        "schemaVersion": "1.0",
        "retrievedAt": retrieved_at,
        "sources": {
            "benchlm": {
                "url": BENCHLM_URL,
                "recordCount": len(benchlm_rows),
                "sha256": hashlib.sha256(benchlm_body).hexdigest(),
                "attribution": "BenchLM",
            },
            "llm-stats": {
                "url": LLM_STATS_URL,
                "recordCount": len(llm_stats_rows),
                "sha256": hashlib.sha256(llm_stats_body).hexdigest(),
                "attribution": "llm-stats",
            },
        },
        "recordCount": len(records),
        "records": records,
    }


def main() -> None:
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = build_payload(fetch(BENCHLM_URL), fetch(LLM_STATS_URL), retrieved_at)
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(
        f"benchlm={payload['sources']['benchlm']['recordCount']} "
        f"llm_stats={payload['sources']['llm-stats']['recordCount']} "
        f"catalog_entities={payload['recordCount']}"
    )


if __name__ == "__main__":
    main()

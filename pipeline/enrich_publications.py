#!/usr/bin/env python3
"""Refresh arXiv-declared venue metadata for indexed benchmark papers.

This stage records author metadata as claims. It does not upgrade an arXiv
comment to an official conference decision, and it never infers rejection from
missing data.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from index_benchmarks import Paper, infer_publication, normalize_space, venue_entities


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "benchmarks.json"
RECEIPT_DIR = ROOT / "data" / "publication"
API_URL = "https://export.arxiv.org/api/query"
ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
VERSION_RE = re.compile(r"v\d+$")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_id(value: str) -> str:
    return VERSION_RE.sub("", value.rsplit("/", 1)[-1])


def text(entry: ET.Element, path: str) -> str:
    item = entry.find(path, ATOM)
    return normalize_space(item.text if item is not None else "")


def fetch_batch(ids: list[str]) -> dict[str, dict[str, str]]:
    request = Request(
        f"{API_URL}?{urlencode({'id_list': ','.join(ids), 'max_results': str(len(ids))})}",
        headers={"User-Agent": "BenchmarkRadar/1.0 (https://github.com/Claire1217/benchmark-radar)"},
    )
    with urlopen(request, timeout=90) as response:
        root = ET.fromstring(response.read())
    output: dict[str, dict[str, str]] = {}
    for entry in root.findall("atom:entry", ATOM):
        arxiv_id = clean_id(text(entry, "atom:id"))
        if arxiv_id:
            output[arxiv_id] = {
                "comment": text(entry, "arxiv:comment"),
                "journal_ref": text(entry, "arxiv:journal_ref"),
                "updated": text(entry, "atom:updated"),
            }
    return output


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Refresh arXiv publication and acceptance claims.")
    result.add_argument("--batch-size", type=int, default=100)
    result.add_argument("--delay", type=float, default=3.0)
    result.add_argument("--limit", type=int)
    return result


def main() -> None:
    args = parser().parse_args()
    payload = read_json(DATA_PATH)
    records = payload.get("records", [])
    selected = records[: args.limit] if args.limit else records
    by_id = {clean_id(str(record.get("source", {}).get("id", ""))): record for record in selected}
    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata: dict[str, dict[str, str]] = {}
    failures: list[dict[str, str]] = []
    ids = [value for value in by_id if value]
    for offset in range(0, len(ids), args.batch_size):
        batch = ids[offset : offset + args.batch_size]
        try:
            metadata.update(fetch_batch(batch))
        except Exception as exc:  # keep prior verified data when a source is unavailable
            failures.append({"ids": f"{batch[0]}..{batch[-1]}", "error": str(exc)[:300]})
        if offset + args.batch_size < len(ids):
            time.sleep(args.delay)

    counts = {"publication_reported": 0, "acceptance_claimed": 0, "unverified": 0}
    for arxiv_id, record in by_id.items():
        source = metadata.get(arxiv_id)
        if source is None:
            continue
        paper = Paper(
            arxiv_id=arxiv_id,
            title=str(record.get("paperTitle") or record.get("name") or ""),
            authors=list(record.get("source", {}).get("authors", [])),
            abstract=str(record.get("oneLine") or ""),
            categories=list(record.get("source", {}).get("categories", [])),
            primary_category="",
            released_at=str(record.get("releasedAt") or ""),
            updated_at=source["updated"],
            entry_url=str(record.get("links", {}).get("report") or f"https://arxiv.org/abs/{arxiv_id}"),
            pdf_url=str(record.get("links", {}).get("pdf") or f"https://arxiv.org/pdf/{arxiv_id}"),
            comments=source["comment"],
            journal_ref=source["journal_ref"],
        )
        record["publication"] = infer_publication(paper, observed_at)
        entities = venue_entities(record["publication"])
        record["venueAttempts"] = entities["venueAttempts"]
        record["publications"] = entities["publications"]
        counts[record["publication"]["status"]] += 1

    payload["manifest"]["publicationMetadata"] = {
        "observedAt": observed_at,
        "source": "arXiv API comments and journal references",
        "recordsChecked": len(metadata),
        "note": "arXiv venue text is author-provided; official venue adapters may upgrade evidence later.",
    }
    write_json(DATA_PATH, payload)
    receipt = {
        "observedAt": observed_at,
        "recordsRequested": len(ids),
        "recordsChecked": len(metadata),
        "counts": counts,
        "failures": failures,
    }
    write_json(RECEIPT_DIR / f"{date.today().isoformat()}.json", receipt)
    print(f"requested={len(ids)} checked={len(metadata)} counts={counts} failures={len(failures)}")


if __name__ == "__main__":
    main()

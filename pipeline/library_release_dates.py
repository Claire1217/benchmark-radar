"""Apply reviewed release evidence independently of refreshed catalog snapshots."""

from datetime import date
from urllib.parse import urlparse


def apply_release_dates(records: list[dict], evidence: dict) -> None:
    by_id = {record["id"]: record for record in records}
    seen = set()
    for item in evidence.get("records", []):
        identity = item["id"]
        if identity in seen or identity not in by_id:
            raise ValueError(f"Duplicate or missing release evidence target: {identity}")
        seen.add(identity)
        precision = item["precision"]
        if precision not in {"day", "year"}:
            raise ValueError(f"Invalid release precision: {precision}")
        value = item["date"]
        parsed = date.fromisoformat(value if precision == "day" else value + "-01-01")
        if parsed > date.today():
            raise ValueError(f"Future release date: {identity}")
        if item["basis"] not in {"paper-v1", "official-announcement"}:
            raise ValueError(f"Unsupported release evidence basis: {identity}")
        url = urlparse(item["sourceUrl"])
        if url.scheme != "https" or not url.netloc:
            raise ValueError(f"Invalid release evidence URL: {identity}")
        record = by_id[identity]
        record["releasedAt"] = parsed.isoformat()
        record["releaseDatePrecision"] = precision
        record["firstRelease"] = {
            "year": parsed.year,
            "date": value if precision == "day" else None,
            "sourceUrl": item["sourceUrl"],
        }
        record["releaseEvidence"] = dict(item)

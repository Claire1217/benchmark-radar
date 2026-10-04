"""Apply reviewed release evidence independently of refreshed catalog snapshots."""

from datetime import date
import re
import sys
from urllib.parse import urlparse


def _resolve(identity: str, by_id: dict, redirects: dict) -> str | None:
    seen = set()
    while identity not in by_id and identity in redirects and identity not in seen:
        seen.add(identity)
        identity = redirects[identity]
    return identity if identity in by_id else None


def apply_release_dates(records: list[dict], evidence: dict, redirects: dict | None = None) -> list[str]:
    """Apply evidence; return ids that no longer resolve to any record.

    A record can disappear between runs when a newly admitted Radar record
    absorbs a catalog row of the same name. Evidence for such ids follows the
    redirect; evidence with no surviving target is reported, not fatal, so one
    stale review cannot block the whole daily publish.
    """
    redirects = redirects or {}
    by_id = {record["id"]: record for record in records}
    seen = set()
    direct = {item["id"] for item in evidence.get("records", [])}
    orphaned = []
    for item in evidence.get("records", []):
        identity = item["id"]
        if identity in seen:
            raise ValueError(f"Duplicate release evidence target: {identity}")
        seen.add(identity)
        precision = item["precision"]
        if precision not in {"day", "month", "year"}:
            raise ValueError(f"Invalid release precision: {precision}")
        value = item["date"]
        pattern = {"day": r"\d{4}-\d{2}-\d{2}", "month": r"\d{4}-\d{2}", "year": r"\d{4}"}[precision]
        if not re.fullmatch(pattern, value):
            raise ValueError(f"Invalid release date shape: {identity}")
        parsed = date.fromisoformat(value + {"day": "", "month": "-01", "year": "-01-01"}[precision])
        if parsed > date.today():
            raise ValueError(f"Future release date: {identity}")
        if item["basis"] not in {"paper-v1", "official-announcement"}:
            raise ValueError(f"Unsupported release evidence basis: {identity}")
        url = urlparse(item["sourceUrl"])
        if url.scheme != "https" or not url.netloc:
            raise ValueError(f"Invalid release evidence URL: {identity}")
        target = _resolve(identity, by_id, redirects)
        if target is None:
            orphaned.append(identity)
            continue
        # Evidence reviewed for the surviving record itself takes precedence.
        if target != identity and target in direct:
            continue
        record = by_id[target]
        record["releasedAt"] = parsed.isoformat()
        record["releaseDatePrecision"] = precision
        record["firstRelease"] = {
            "year": parsed.year,
            "month": parsed.month if precision in {"day", "month"} else None,
            "date": value if precision == "day" else None,
            "sourceUrl": item["sourceUrl"],
        }
        record["releaseEvidence"] = dict(item)
    if orphaned:
        print(f"warning: release evidence without a Library record: {', '.join(orphaned)}", file=sys.stderr)
    return orphaned

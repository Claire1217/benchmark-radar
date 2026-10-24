"""Bounded admission scheduling; operational attempts are not editorial decisions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def source_key(record: dict) -> str:
    source = record.get("source") or {}
    kind, identifier = str(source.get("type") or "unknown"), str(source.get("id") or "")
    return identifier if identifier.startswith(kind + ":") else f"{kind}:{identifier}"


def select(records: list[dict], state: dict, *, limit: int, now: str, force: bool = False) -> list[dict]:
    """Reserve half the budget for oldest work, half for newest; refill unused slots.

    The caller supplies records whose content needs review. Publication date never
    makes a pending item ineligible. Operational retries cool down for a day.
    """
    attempts = state.get("bySource", {})
    eligible = [r for r in records if force or attempts.get(source_key(r), {}).get("nextAttemptAt", "") <= now]
    if limit <= 0:
        return sorted(eligible, key=lambda r: (r.get("firstSeenAt") or r.get("releasedAt", ""), source_key(r)))
    oldest = sorted(eligible, key=lambda r: (attempts.get(source_key(r), {}).get("lastAttemptAt", ""),
                                            r.get("firstSeenAt") or r.get("releasedAt", ""), source_key(r)))
    selected = oldest[:(limit + 1) // 2]
    used = {source_key(r) for r in selected}
    newest = sorted((r for r in eligible if source_key(r) not in used),
                    key=lambda r: (r.get("sourceUpdatedAt") or r.get("releasedAt", ""), source_key(r)), reverse=True)
    return selected + newest[:limit - len(selected)]


def record_attempt(state: dict, record: dict, status: str, now: str, fingerprint: str, reason: str = "") -> None:
    previous = state.setdefault("bySource", {}).get(source_key(record), {})
    next_at = (datetime.fromisoformat(now.replace("Z", "+00:00")) + timedelta(days=1)).astimezone(timezone.utc)
    event = {"status": status, "at": now, "reason": reason[:500], "fingerprint": fingerprint}
    state["bySource"][source_key(record)] = {
        "status": status, "lastAttemptAt": now,
        "nextAttemptAt": next_at.isoformat().replace("+00:00", "Z"),
        "selectionFingerprint": fingerprint,
        "attempts": int(previous.get("attempts", 0)) + 1,
        "history": [*previous.get("history", []), event][-20:],
    }
    state["schemaVersion"] = 1

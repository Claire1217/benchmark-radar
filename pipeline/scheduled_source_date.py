#!/usr/bin/env python3
"""Return the previous calendar day for the fixed publication timezone."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


PUBLICATION_TIMEZONE = "Australia/Brisbane"


def previous_calendar_day(now: datetime | None = None) -> str:
    timezone = ZoneInfo(PUBLICATION_TIMEZONE)
    local_now = now.astimezone(timezone) if now is not None else datetime.now(timezone)
    return (local_now.date() - timedelta(days=1)).isoformat()


if __name__ == "__main__":
    print(previous_calendar_day())

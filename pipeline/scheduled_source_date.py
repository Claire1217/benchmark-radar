#!/usr/bin/env python3
"""Resolve the previous publication day and its catch-up window."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


PUBLICATION_TIMEZONE = "Australia/Brisbane"


def previous_calendar_day(now: datetime | None = None) -> str:
    timezone = ZoneInfo(PUBLICATION_TIMEZONE)
    local_now = now.astimezone(timezone) if now is not None else datetime.now(timezone)
    return (local_now.date() - timedelta(days=1)).isoformat()


def batch_start(target: str) -> str:
    """A Monday publication catches up Friday through Sunday."""
    source_day = date.fromisoformat(target)
    return (source_day - timedelta(days=2)).isoformat() if source_day.weekday() == 6 else target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target")
    parser.add_argument("--batch-start", action="store_true")
    args = parser.parse_args()
    target = args.target or previous_calendar_day()
    print(batch_start(target) if args.batch_start else target)

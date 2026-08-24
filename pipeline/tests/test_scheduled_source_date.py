from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scheduled_source_date import batch_start, previous_calendar_day


class ScheduledSourceDateTests(unittest.TestCase):
    def test_uses_previous_brisbane_calendar_day(self) -> None:
        now = datetime(2026, 8, 20, 4, 17, tzinfo=timezone.utc)
        self.assertEqual(previous_calendar_day(now), "2026-08-19")

    def test_timezone_boundary_is_explicit(self) -> None:
        now = datetime(2026, 8, 20, 18, 30, tzinfo=timezone.utc)
        self.assertEqual(previous_calendar_day(now), "2026-08-20")

    def test_monday_batch_starts_on_friday(self) -> None:
        self.assertEqual(batch_start("2026-08-23"), "2026-08-21")
        self.assertEqual(batch_start("2026-08-24"), "2026-08-24")


if __name__ == "__main__":
    unittest.main()

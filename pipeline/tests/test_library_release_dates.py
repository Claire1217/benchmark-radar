import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from library_release_dates import apply_release_dates


class ReleaseDatesTest(unittest.TestCase):
    def setUp(self):
        self.rows = [{"id": "arc", "releasedAt": "0001-01-01", "releaseDatePrecision": "unknown"}]
        self.entry = {"id": "arc", "date": "2018-03-14", "precision": "day",
                      "basis": "paper-v1", "sourceUrl": "https://arxiv.org/abs/1803.05457"}

    def test_reviewed_evidence_survives_regeneration(self):
        fresh = copy.deepcopy(self.rows)
        for rows in [self.rows, fresh]:
            apply_release_dates(rows, {"records": [self.entry]})
            self.assertEqual(rows[0]["releasedAt"], "2018-03-14")
            self.assertEqual(rows[0]["firstRelease"]["sourceUrl"], self.entry["sourceUrl"])
        self.assertEqual(self.rows, fresh)

    def test_year_precision_does_not_invent_a_day(self):
        self.entry.update(date="2018", precision="year")
        apply_release_dates(self.rows, {"records": [self.entry]})
        self.assertEqual(self.rows[0]["releaseDatePrecision"], "year")
        self.assertIsNone(self.rows[0]["firstRelease"]["date"])

    def test_missing_evidence_stays_unknown(self):
        self.rows[0]["catalogSources"] = [{"year": 2026}]
        apply_release_dates(self.rows, {})
        self.assertEqual(self.rows[0]["releaseDatePrecision"], "unknown")

    def test_bad_evidence_fails_build(self):
        for patch in [{"id": "missing"}, {"date": "2018-02-30"},
                      {"basis": "catalog-year"}, {"sourceUrl": "javascript:alert(1)"}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                apply_release_dates(copy.deepcopy(self.rows), {"records": [{**self.entry, **patch}]})

    def test_duplicate_target_fails_build(self):
        with self.assertRaises(ValueError):
            apply_release_dates(self.rows, {"records": [self.entry, self.entry]})


if __name__ == "__main__":
    unittest.main()

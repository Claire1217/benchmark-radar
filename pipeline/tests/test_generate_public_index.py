import unittest

from pipeline.generate_public_index import effective_latest_batch, effective_latest_release, public_publishers


class PublicIndexTests(unittest.TestCase):
    def test_empty_source_day_remains_the_latest_report_day(self) -> None:
        records = [
            {"releasedAt": "2026-08-20", "displayEligible": True},
            {"releasedAt": "2026-08-13", "displayEligible": True},
        ]
        self.assertEqual(
            effective_latest_batch(records, "2026-08-21", {"from": "2026-08-21", "to": "2026-08-21"}),
            {"from": "2026-08-21", "to": "2026-08-21"},
        )

    def test_historical_rerun_does_not_move_latest_report_backwards(self) -> None:
        records = [
            {"releasedAt": "2026-08-20", "displayEligible": True},
            {"releasedAt": "2026-08-22", "displayEligible": True},
        ]
        self.assertEqual(
            effective_latest_batch(
                records, "2026-08-23", {"from": "2026-08-20", "to": "2026-08-20"}, "2026-08-22"
            ),
            {"from": "2026-08-22", "to": "2026-08-22"},
        )

    def test_hosting_platform_is_not_a_publisher(self) -> None:
        source = {
            "name": "SWE-bench Science",
            "publishers": [
                {"name": "arXiv", "organizationType": "community"},
                {"name": "Example Research", "organizationType": "academic-lab"},
            ],
        }
        self.assertEqual([item["name"] for item in public_publishers(source)], ["Example Research"])

    def test_weekend_catch_up_does_not_expand_latest_beyond_one_day(self) -> None:
        records = [
            {"releasedAt": "2026-08-21", "displayEligible": True},
            {"releasedAt": "2026-08-22", "displayEligible": True},
        ]
        self.assertEqual(
            effective_latest_batch(
                records, "2026-08-23", {"from": "2026-08-21", "to": "2026-08-23"}
            ),
            {"from": "2026-08-23", "to": "2026-08-23"},
        )

    def test_benchmark_name_is_not_a_publisher(self) -> None:
        source = {"name": "NCP-Bench", "publishers": [{"name": "NCP-Bench"}]}
        self.assertEqual(public_publishers(source), [])


if __name__ == "__main__":
    unittest.main()

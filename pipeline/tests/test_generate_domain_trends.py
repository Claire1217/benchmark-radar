import unittest

from pipeline.generate_domain_trends import matches_trend, tracked_use_score, trend_definitions


class TrackedUseScoreTests(unittest.TestCase):
    def test_balances_provider_and_model_breadth(self) -> None:
        mmlu = tracked_use_score(4, 101)
        aime = tracked_use_score(4, 2)
        swe_verified = tracked_use_score(3, 111)

        self.assertGreater(mmlu, swe_verified)
        self.assertGreater(swe_verified, aime)

    def test_missing_model_coverage_stays_missing(self) -> None:
        self.assertIsNone(tracked_use_score(4, 0))


class TrendTaxonomyTests(unittest.TestCase):
    def test_code_benchmark_matches_general_and_coding(self) -> None:
        record = {
            "domainScope": "general",
            "capabilityGroups": ["Coding & Software Engineering"],
            "applicationDomains": [],
        }
        self.assertTrue(matches_trend(record, "overview", "General AI"))
        self.assertTrue(matches_trend(record, "capability", "Coding & Software Engineering"))
        self.assertFalse(matches_trend(record, "application", "Science & Research"))

    def test_applied_benchmark_can_match_capability_and_field(self) -> None:
        record = {
            "domainScope": "specific",
            "capabilityGroups": ["Agents"],
            "applicationDomains": ["Science & Research"],
        }
        self.assertFalse(matches_trend(record, "overview", "General AI"))
        self.assertTrue(matches_trend(record, "capability", "Agents"))
        self.assertTrue(matches_trend(record, "application", "Science & Research"))

    def test_definitions_keep_general_ai_before_application_fields(self) -> None:
        records = [{
            "capabilityGroups": ["Coding & Software Engineering"],
            "applicationDomains": ["Science & Research"],
        }]
        definitions = trend_definitions(records)
        self.assertEqual(definitions[0], ("overview", "General AI", "General AI"))
        self.assertLess(
            definitions.index(("capability", "Coding & Software Engineering", "General AI capabilities")),
            definitions.index(("application", "Science & Research", "Application fields")),
        )


if __name__ == "__main__":
    unittest.main()

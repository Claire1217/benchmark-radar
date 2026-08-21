import unittest

from pipeline.generate_domain_trends import tracked_use_score


class TrackedUseScoreTests(unittest.TestCase):
    def test_balances_provider_and_model_breadth(self) -> None:
        mmlu = tracked_use_score(4, 101)
        aime = tracked_use_score(4, 2)
        swe_verified = tracked_use_score(3, 111)

        self.assertGreater(mmlu, swe_verified)
        self.assertGreater(swe_verified, aime)

    def test_missing_model_coverage_stays_missing(self) -> None:
        self.assertIsNone(tracked_use_score(4, 0))


if __name__ == "__main__":
    unittest.main()

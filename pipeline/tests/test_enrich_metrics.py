from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enrich_metrics import dataset_slug, github_slug, percentile, readiness_from_links


class MetricTests(unittest.TestCase):
    def test_parses_supported_public_resource_urls(self) -> None:
        self.assertEqual(github_slug("https://github.com/org/repo.git?tab=readme"), "org/repo")
        self.assertEqual(dataset_slug("https://huggingface.co/datasets/org/data"), "org/data")

    def test_percentile_keeps_missing_unknown(self) -> None:
        self.assertIsNone(percentile(None, [1, 2, 3]))
        self.assertEqual(percentile(2, [1, 2, 3]), 0.5)

    def test_readiness_is_recomputed_after_resource_enrichment(self) -> None:
        self.assertEqual(readiness_from_links({"code": "https://github.com/o/r"}), "Runnable")
        self.assertEqual(readiness_from_links({"data": "https://huggingface.co/datasets/o/d"}), "Inspectable")
        self.assertEqual(readiness_from_links({}), "Paper only")


if __name__ == "__main__":
    unittest.main()

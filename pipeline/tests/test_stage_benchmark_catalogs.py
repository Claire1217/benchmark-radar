from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage_benchmark_catalogs import (  # noqa: E402
    adapt_llm_stats_public_page,
    adapt_payload,
    stage_llm_stats,
)


FIXTURES = Path(__file__).parent / "fixtures"
RETRIEVED_AT = "2026-08-19T00:00:00Z"


class CatalogStagingTests(unittest.TestCase):
    def test_adapts_benchlm_official_items_shape(self) -> None:
        payload = {
            "schemaVersion": "1.0",
            "items": [{"benchmarkKey": "healthBench", "name": "HealthBench (raw)", "format": "Raw rubric score"}],
        }
        staged = adapt_payload(
            payload,
            source_id="benchlm",
            source_url="https://benchlm.ai/data/benchmarks.json",
            retrieved_at="2026-08-19T00:00:00Z",
        )
        self.assertEqual(staged["recordCount"], 1)
        self.assertEqual(staged["candidates"][0]["sourceKey"], "healthBench")

    def load_fixture(self, name: str) -> dict:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_adapts_benchlm_mapping_and_preserves_evidence(self) -> None:
        payload = self.load_fixture("benchlm_benchmarks.json")
        result = adapt_payload(
            payload,
            source_id="benchlm",
            source_url="https://benchlm.ai/benchmarks.json",
            retrieved_at=RETRIEVED_AT,
        )
        self.assertEqual(result["recordCount"], 2)
        terminal = result["candidates"][0]
        self.assertEqual(terminal["sourceKey"], "terminalBench2")
        self.assertEqual(terminal["rawVersion"], "2.0")
        self.assertTrue(terminal["protocolEvidence"])
        self.assertTrue(terminal["metricEvidence"])
        self.assertTrue(terminal["attributionEvidence"])
        self.assertEqual(len(terminal["rawRecordSha256"]), 64)
        self.assertEqual(result["mode"], "staging-only")

    def test_llm_stats_public_page_keeps_directory_and_original_source_links(self) -> None:
        result = adapt_llm_stats_public_page(
            '<a href="https://arxiv.org/abs/2406.12045">tau-bench</a>'
            '<a href="https://github.com/sierra-research/tau-bench">official code</a>'
            '<a href="/benchmarks/internal">navigation</a>'
            '<a href="https://example.com/blog">blog</a>'
            '<script>self.__next_f.push([1,"/benchmarks/gpqa-diamond"])</script>',
            RETRIEVED_AT,
        )
        candidate = result["candidates"][0]
        self.assertEqual(result["recordCount"], 4)
        self.assertEqual(candidate["originalSourceUrl"], "https://arxiv.org/abs/2406.12045")
        self.assertFalse(candidate["canonicalPromotionAllowed"])
        internal = next(item for item in result["candidates"] if item["sourceKey"] == "internal")
        self.assertEqual(internal["stagingStatus"], "catalog-detail-pending-primary-source")
        self.assertIsNone(internal["originalSourceUrl"])
        self.assertTrue(any(item["sourceKey"] == "gpqa-diamond" for item in result["candidates"]))
        self.assertEqual(result["mode"], "public-page-discovery-only")

    @patch("stage_benchmark_catalogs.fetch_bytes", side_effect=RuntimeError("offline"))
    def test_llm_stats_public_page_failure_is_non_blocking(self, _fetch: object) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = stage_llm_stats(Path(directory), RETRIEVED_AT)
        self.assertIsNone(result)

    @patch(
        "stage_benchmark_catalogs.fetch_bytes",
        return_value=b'<a href="https://huggingface.co/datasets/org/bench">Bench data</a>',
    )
    def test_llm_stats_public_page_needs_no_key(self, _fetch: object) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = stage_llm_stats(Path(directory), RETRIEVED_AT)
            payload = json.loads(Path(result).read_text(encoding="utf-8"))
        self.assertEqual(payload["recordCount"], 1)


if __name__ == "__main__":
    unittest.main()

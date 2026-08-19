from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage_benchmark_catalogs import (  # noqa: E402
    LLM_STATS_KEY_ENV,
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

    def test_adapts_llm_stats_list_to_same_schema(self) -> None:
        payload = self.load_fixture("llm_stats_benchmarks.json")
        result = adapt_payload(
            payload,
            source_id="llm-stats-zeroeval",
            source_url="https://api.zeroeval.com/stats/v1/benchmarks",
            retrieved_at=RETRIEVED_AT,
        )
        candidate = result["candidates"][0]
        self.assertEqual(candidate["sourceKey"], "swe-bench-verified")
        self.assertEqual(candidate["rawVersion"], "verified")
        self.assertTrue(candidate["protocolEvidence"])
        self.assertTrue(candidate["metricEvidence"])

    def test_missing_llm_stats_key_can_skip_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {LLM_STATS_KEY_ENV: ""}, clear=False
        ):
            result = stage_llm_stats(Path(directory), RETRIEVED_AT, skip_missing_key=True)
        self.assertIsNone(result)

    def test_missing_llm_stats_key_has_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {LLM_STATS_KEY_ENV: ""}, clear=False
        ):
            with self.assertRaisesRegex(RuntimeError, LLM_STATS_KEY_ENV):
                stage_llm_stats(Path(directory), RETRIEVED_AT, skip_missing_key=False)


if __name__ == "__main__":
    unittest.main()

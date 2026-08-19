from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from review_candidates_with_codex import (
    KEY_ENV,
    codex_command,
    normalize_base_url,
    validate_decisions,
)


def candidate() -> dict:
    return {
        "id": "bm_deepswe",
        "paperTitle": "DeepSWE: Measuring Frontier Coding Agents",
        "reviewContext": {
            "abstract": "DeepSWE is a benchmark of 113 original software engineering tasks.",
            "comments": "",
        },
    }


class AiReviewTests(unittest.TestCase):
    def test_normalizes_https_base_url(self) -> None:
        self.assertEqual(normalize_base_url("https://example.test"), "https://example.test/v1")
        self.assertEqual(normalize_base_url("https://example.test/v1/"), "https://example.test/v1")
        with self.assertRaises(ValueError):
            normalize_base_url("http://example.test")

    def test_command_contains_env_name_not_secret(self) -> None:
        command = codex_command("codex", "model-id", "https://example.test/v1", Path("out.json"))
        rendered = " ".join(command)
        self.assertIn(KEY_ENV, rendered)
        self.assertNotIn("secret-value", rendered)
        self.assertIn("--ephemeral", command)
        self.assertIn("read-only", command)

    def test_accepts_exact_release_evidence(self) -> None:
        response = {
            "decisions": [
                {
                    "id": "bm_deepswe",
                    "verdict": "benchmark_release",
                    "relation": "introduces",
                    "artifact_role": "reusable_benchmark",
                    "benchmark_name": "DeepSWE",
                    "evidence_quote": "DeepSWE is a benchmark of 113 original software engineering tasks.",
                    "confidence": 0.98,
                    "reason": "Explicit identity statement.",
                }
            ]
        }
        result = validate_decisions([candidate()], response)
        self.assertTrue(result[0]["validation"]["valid"])

    def test_rejects_hallucinated_release_evidence(self) -> None:
        response = {
            "decisions": [
                {
                    "id": "bm_deepswe",
                    "verdict": "benchmark_release",
                    "relation": "introduces",
                    "artifact_role": "diagnostic_benchmark",
                    "benchmark_name": "DeepSWE",
                    "evidence_quote": "We release the world's best benchmark and leaderboard.",
                    "confidence": 0.99,
                    "reason": "Claimed release.",
                }
            ]
        }
        result = validate_decisions([candidate()], response)
        self.assertFalse(result[0]["validation"]["valid"])


if __name__ == "__main__":
    unittest.main()

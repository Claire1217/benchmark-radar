from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from index_benchmarks import Paper, canonical_name, recognition, to_record, upsert


def sample(title: str, abstract: str, arxiv_id: str = "2608.00001") -> Paper:
    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors=["A. Researcher"],
        abstract=abstract,
        categories=["cs.AI"],
        primary_category="cs.AI",
        released_at="2026-08-18",
        updated_at="2026-08-18T12:00:00Z",
        entry_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        comments="",
    )


class IndexerTests(unittest.TestCase):
    def test_accepts_explicit_named_release(self) -> None:
        paper = sample(
            "ClearBench: A Benchmark for Reliable Agents",
            "We introduce ClearBench, a new benchmark with 500 tasks, an evaluation protocol, and strong baselines.",
        )
        score, relation, reasons = recognition(paper)
        self.assertGreaterEqual(score, 0.75)
        self.assertEqual(relation, "introduces")
        self.assertIn("named benchmark or evaluation-suite title", reasons)
        self.assertEqual(canonical_name(paper), "ClearBench")

    def test_benchmarking_study_is_not_auto_published(self) -> None:
        paper = sample(
            "Benchmarking Large Language Models on Filing Tasks",
            "We evaluate six existing models and report their accuracy.",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.75)
        self.assertEqual(relation, "evaluates_only")

    def test_never_invents_resource_links(self) -> None:
        paper = sample(
            "ClearBench: A Benchmark for Reliable Agents",
            "We introduce ClearBench, a new benchmark with evaluation tasks and baselines.",
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertIsNone(record["links"]["code"])
        self.assertIsNone(record["links"]["data"])
        self.assertEqual(record["links"]["report"], paper.entry_url)
        self.assertFalse(record["demo"])

    def test_upsert_preserves_first_seen(self) -> None:
        old = to_record(
            sample("ClearBench: A Benchmark for Reliable Agents", "We introduce a new benchmark with tasks."),
            "2026-08-19T00:00:00Z",
            0.8,
            "introduces",
            [],
        )
        new = dict(old)
        new["firstSeenAt"] = "2026-08-20"
        merged = upsert([old], [new])
        self.assertEqual(merged[0]["firstSeenAt"], "2026-08-19")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from index_benchmarks import Paper, canonical_name, curated_records, family_id, infer_publication, merge_patch, recognition, to_record, upsert, venue_entities


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

    def test_accepts_coined_name_without_bench_suffix(self) -> None:
        paper = sample(
            "DeepSWE: Measuring Frontier Coding Agents",
            "DeepSWE is a benchmark of 113 original, long-horizon software engineering tasks for evaluating coding agents.",
            "2607.07946",
        )
        score, relation, reasons = recognition(paper)
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(relation, "introduces")
        self.assertIn("coined benchmark name tied to benchmark evidence", reasons)
        self.assertEqual(canonical_name(paper), "DeepSWE")

    def test_model_name_near_benchmark_is_not_a_named_benchmark(self) -> None:
        paper = sample(
            "TRUSS: A Retrieval Model",
            "TRUSS improves retrieval performance on the existing MMLU benchmark and several evaluation tasks.",
        )
        score, relation, reasons = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertNotIn("coined benchmark name tied to benchmark evidence", reasons)

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

    def test_domain_is_a_separate_controlled_axis(self) -> None:
        paper = sample(
            "ChipBench: A Benchmark for RTL Generation",
            "We introduce ChipBench, a new benchmark for Verilog and EDA workflows with evaluation tasks.",
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertEqual(record["primaryDomain"], "Chip Design & EDA")
        self.assertIn("Semiconductors", record["industrySectors"])
        self.assertEqual(record["domainCuration"]["method"], "rules-v1")

    def test_family_id_is_stable_across_spelling_punctuation(self) -> None:
        self.assertEqual(family_id("Clear-Bench"), family_id("Clear Bench"))

    def test_curated_patch_preserves_unmodified_source_fields(self) -> None:
        merged = merge_patch({"name": "ClearBench", "links": {"paper": "p", "code": None}}, {"links": {"code": "c"}})
        self.assertEqual(merged["name"], "ClearBench")
        self.assertEqual(merged["links"], {"paper": "p", "code": "c"})

    def test_non_arxiv_curated_record_has_primary_source(self) -> None:
        kotlin = next(record for record in curated_records() if record["name"] == "Kotlin Benchmark")
        self.assertEqual(kotlin["source"]["type"], "official-project")
        self.assertTrue(kotlin["links"]["report"].startswith("https://"))
        self.assertEqual(kotlin["dataStatus"], "primary-source-reviewed")

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

    def test_publication_uses_explicit_acceptance_comment(self) -> None:
        paper = sample("ClearBench: A Benchmark", "We introduce a new benchmark with tasks.")
        paper = Paper(**{**paper.__dict__, "comments": "Accepted at NeurIPS 2026."})
        publication = infer_publication(paper, "2026-08-19T00:00:00Z")
        self.assertEqual(publication["status"], "acceptance_claimed")
        self.assertEqual(publication["venue"], "NeurIPS 2026")
        self.assertEqual(publication["source"], "arxiv-comments")
        entities = venue_entities(publication)
        self.assertEqual(entities["venueAttempts"][0]["reviewStatus"], "accepted")
        self.assertEqual(entities["publications"], [])

    def test_publication_prefers_journal_reference(self) -> None:
        paper = sample("ClearBench: A Benchmark", "We introduce a new benchmark with tasks.")
        paper = Paper(**{**paper.__dict__, "journal_ref": "Proceedings of ICML 2026"})
        publication = infer_publication(paper, "2026-08-19T00:00:00Z")
        self.assertEqual(publication["status"], "publication_reported")
        self.assertEqual(publication["venue"], "Proceedings of ICML 2026")
        entities = venue_entities(publication)
        self.assertEqual(entities["publications"][0]["publicationStatus"], "published")

    def test_absent_acceptance_is_unverified_not_rejected(self) -> None:
        paper = sample("ClearBench: A Benchmark", "We introduce a new benchmark with tasks.")
        publication = infer_publication(paper, "2026-08-19T00:00:00Z")
        self.assertEqual(publication["status"], "unverified")
        self.assertNotEqual(publication["status"], "rejected")


if __name__ == "__main__":
    unittest.main()

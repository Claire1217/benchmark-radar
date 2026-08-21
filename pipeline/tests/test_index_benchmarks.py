from __future__ import annotations

from io import BytesIO
import socket
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from index_benchmarks import Paper, canonical_name, curated_records, family_id, infer_publication, merge_patch, persistent_review_candidates, recognition, request_oai, to_record, upsert, venue_entities


OAI_OK = b'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords /></OAI-PMH>'


def response_with(body: bytes) -> Mock:
    response = Mock()
    response.read.return_value = body
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return response


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
    def test_review_queue_upsert_preserves_deferred_candidates_outside_daily_window(self) -> None:
        older = full = {
            "id": "older", "releasedAt": "2026-07-01",
            "source": {"id": "2607.00001"},
            "reviewContext": {"abstract": "old", "comments": ""},
            "autoReview": {"status": "deferred"},
        }
        today = {
            "id": "today", "releasedAt": "2026-08-19",
            "source": {"id": "2608.19001"},
            "reviewContext": {"abstract": "new", "comments": ""},
        }
        result = persistent_review_candidates(
            [older], [today], "2026-08-19", "2026-08-19", set()
        )
        self.assertEqual({item["id"] for item in result}, {"older", "today"})
        self.assertEqual(full["autoReview"]["status"], "deferred")

    def test_review_queue_excludes_persistently_promoted_source(self) -> None:
        candidate = {
            "id": "candidate", "releasedAt": "2026-08-19",
            "source": {"id": "2608.19002"},
            "reviewContext": {"abstract": "text", "comments": ""},
        }
        result = persistent_review_candidates(
            [candidate], [candidate], "2026-08-19", "2026-08-19", {"2608.19002"}
        )
        self.assertEqual(result, [])

    def test_systematic_benchmark_on_existing_datasets_is_evaluates_only(self) -> None:
        paper = sample(
            "Zero-Shot Vision-Language Models for Classroom Engagement Recognition: A Benchmark Study of Prompt Sensitivity and Cross-Dataset Generalization",
            "We present a systematic benchmark that evaluates five widely-used VLMs across two complementary educational datasets: DAiSEE and the public Student Classroom Behaviour dataset. We compare prompt sensitivity and cross-dataset generalization without releasing a new evaluation artifact.",
            "2606.21861",
        )
        score, relation, reasons = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(relation, "evaluates_only")
        self.assertIn(
            "benchmark study on existing or public datasets without a named artifact release",
            reasons,
        )

    def test_long_prose_prefix_with_benchmark_subtitle_is_not_canonical_identity(self) -> None:
        title = (
            "How Reliably Do Vision Language Models Recognize Classroom Engagement: "
            "A Benchmark Study Across Public Datasets"
        )
        paper = sample(
            title,
            "We compare several models on widely-used public datasets and report a systematic benchmark study.",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(canonical_name(paper), title)
        self.assertNotEqual(
            canonical_name(paper),
            "How Reliably Do Vision Language Models Recognize Classroom Engagement",
        )

    def test_named_investlogicbench_release_is_extracted_and_accepted(self) -> None:
        paper = sample(
            "Evaluating Investment Logic in Large Language Models: A Real-World Benchmark Towards Personalized Financial Agents",
            "We introduce \\textsc{InvestLogicBench}, a process-native benchmark containing 201,247 documented decisions from 151 real-world investors. It provides evaluation tasks and baselines for personalized financial agents.",
            "2608.06108",
        )
        score, relation, reasons = recognition(paper)
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(relation, "introduces")
        self.assertEqual(canonical_name(paper), "InvestLogicBench")
        self.assertIn("exact named benchmark artifact released in abstract", reasons)

    def test_bench_family_name_with_suffix_is_not_truncated(self) -> None:
        paper = sample(
            "SWE-bench Science: Can Coding Agents Resolve Engineering Tasks in Science?",
            "We introduce SWE-bench Science, a repository-level benchmark for scientific software engineering comprising 119 tasks from 98 repositories.",
            "2608.19799",
        )
        self.assertEqual(canonical_name(paper), "SWE-bench Science")
        self.assertNotEqual(family_id(canonical_name(paper)), family_id("SWE-bench"))

    def test_tactus_model_is_not_promoted_to_benchmark_identity(self) -> None:
        title = "TactusBench: A Tactile Foundation Model for Robot Learning"
        paper = sample(
            title,
            "TactusBench is a foundation model for tactile understanding. We evaluate it on an existing robot manipulation benchmark and release the model weights.",
            "2607.01001",
        )
        score, relation, reasons = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(relation, "evaluates_only")
        self.assertEqual(canonical_name(paper), title)
        self.assertIn("named entity is a model, method, framework, or dataset used in evaluation", reasons)

    def test_timee_dataset_benchmarked_on_is_not_a_release(self) -> None:
        title = "TimEE: Temporal Event Extraction at Scale"
        paper = sample(
            title,
            "TimEE is a dataset of temporal events. We benchmark six baseline models on TimEE using existing evaluation protocols.",
            "2607.01002",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(relation, "evaluates_only")
        self.assertEqual(canonical_name(paper), title)

    def test_cafosat_framework_scored_on_existing_benchmark_is_not_identity(self) -> None:
        paper = sample(
            "CAFOSat: A Framework for Satellite Reasoning",
            "CAFOSat is a framework for satellite reasoning. We present results on the existing SatQA benchmark and release our code.",
            "2607.01003",
        )
        score, relation, reasons = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(relation, "evaluates_only")
        self.assertIn("named entity is a model, method, framework, or dataset used in evaluation", reasons)

    def test_biomazon_model_evaluated_on_public_benchmarks_is_not_identity(self) -> None:
        paper = sample(
            "Biomazon: A Biomedical Foundation Model",
            "Biomazon is a model for biomedical language understanding. We evaluate Biomazon on existing public benchmarks and release its weights.",
            "2607.01004",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(relation, "evaluates_only")

    def test_from_paper_to_benchmark_is_not_a_coined_title_prefix(self) -> None:
        title = "From Paper to Benchmark: A Workflow for Reusing Public Datasets"
        paper = sample(
            title,
            "We introduce a method that converts existing public datasets into evaluation tables and benchmark several baselines.",
            "2607.01005",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(canonical_name(paper), title)

    def test_negated_benchmark_window_is_not_identity_evidence(self) -> None:
        title = "NoScopeBench: Learning Without Evaluation Suites"
        paper = sample(
            title,
            "NoScopeBench is a method that currently lacks a benchmark for systematic comparison. We release the method implementation.",
            "2607.01006",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(relation, "evaluates_only")
        self.assertEqual(canonical_name(paper), title)

    def test_benchmarking_models_on_named_data_defaults_to_dataset_usage(self) -> None:
        title = "ClinicSet: Clinical Instructions at Scale"
        paper = sample(
            title,
            "We benchmark language models on ClinicSet and compare them with baselines from established benchmarks.",
            "2607.01007",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(relation, "evaluates_only")

    def test_exact_benchmark_identity_overrides_nearby_benchmarking_language(self) -> None:
        paper = sample(
            "Tactus: Tactile Agent Evaluation",
            "Tactus is a large-scale benchmark with 420 evaluation tasks. We benchmark baseline models on Tactus and release the task data.",
            "2607.01008",
        )
        score, relation, _ = recognition(paper)
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(relation, "introduces")
        self.assertEqual(canonical_name(paper), "Tactus")

    def test_bcijelly_explicit_collection_can_remain_aggregate(self) -> None:
        paper = sample(
            "BCIJelly: Unified Evaluation for Brain-Computer Interfaces",
            "BCIJelly is a unified suite that aggregates a collection of benchmarks and their evaluation protocols.",
            "2607.01009",
        )
        _, relation, _ = recognition(paper)
        self.assertEqual(relation, "aggregates")

    def test_omniopt_explicit_aggregate_is_not_forced_to_evaluates_only(self) -> None:
        paper = sample(
            "OmniOpt: Unified Optimization Evaluation",
            "OmniOpt is a framework that provides a unified suite aggregating a collection of benchmarks across optimization domains.",
            "2607.01010",
        )
        _, relation, _ = recognition(paper)
        self.assertEqual(relation, "aggregates")

    @patch("index_benchmarks.time.sleep")
    @patch("index_benchmarks.random.uniform", return_value=0.0)
    @patch("index_benchmarks.urlopen")
    def test_oai_retries_timeout_then_succeeds(self, mocked_urlopen: Mock, _jitter: Mock, sleep: Mock) -> None:
        mocked_urlopen.side_effect = [socket.timeout("timed out"), response_with(OAI_OK)]
        root = request_oai({"verb": "ListRecords"})
        self.assertTrue(root.tag.endswith("OAI-PMH"))
        self.assertEqual(mocked_urlopen.call_count, 2)
        sleep.assert_called_once_with(1.0)

    @patch("index_benchmarks.time.sleep")
    @patch("index_benchmarks.urlopen")
    def test_oai_retries_429_using_retry_after_then_succeeds(self, mocked_urlopen: Mock, sleep: Mock) -> None:
        throttled = HTTPError(
            "https://oaipmh.arxiv.org/oai",
            429,
            "Too Many Requests",
            {"Retry-After": "3"},
            BytesIO(),
        )
        mocked_urlopen.side_effect = [throttled, response_with(OAI_OK)]
        request_oai({"verb": "ListRecords"})
        self.assertEqual(mocked_urlopen.call_count, 2)
        sleep.assert_called_once_with(3.0)

    @patch("index_benchmarks.time.sleep")
    @patch("index_benchmarks.urlopen")
    def test_oai_does_not_retry_404(self, mocked_urlopen: Mock, sleep: Mock) -> None:
        missing = HTTPError(
            "https://oaipmh.arxiv.org/oai", 404, "Not Found", {}, BytesIO()
        )
        mocked_urlopen.side_effect = missing
        with self.assertRaises(HTTPError):
            request_oai({"verb": "ListRecords"})
        self.assertEqual(mocked_urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch("index_benchmarks.time.sleep")
    @patch("index_benchmarks.random.uniform", return_value=0.0)
    @patch("index_benchmarks.urlopen")
    def test_oai_raises_after_retry_exhaustion(self, mocked_urlopen: Mock, _jitter: Mock, sleep: Mock) -> None:
        mocked_urlopen.side_effect = URLError("temporary DNS failure")
        with self.assertRaises(URLError):
            request_oai({"verb": "ListRecords"})
        self.assertEqual(mocked_urlopen.call_count, 5)
        self.assertEqual(sleep.call_count, 4)

    @patch("index_benchmarks.time.sleep")
    @patch("index_benchmarks.urlopen")
    def test_oai_semantic_error_is_not_retried(self, mocked_urlopen: Mock, sleep: Mock) -> None:
        semantic_error = (
            b'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">'
            b'<error code="badArgument">invalid set</error></OAI-PMH>'
        )
        mocked_urlopen.return_value = response_with(semantic_error)
        with self.assertRaisesRegex(RuntimeError, "OAI-PMH error badArgument"):
            request_oai({"verb": "ListRecords"})
        self.assertEqual(mocked_urlopen.call_count, 1)
        sleep.assert_not_called()

    def test_edgebench_two_sentence_identity_and_release_is_published(self) -> None:
        paper = sample(
            "EdgeBench: Unveiling Scaling Laws of Learning from Real-World Environments",
            "Pretraining scaling laws reveal predictable improvements. "
            "This discovery stems from EdgeBench, a suite of 134 real world tasks with ultra-long horizons, spanning scientific discovery, software engineering, combinatorial optimization, professional knowledge work, formal mathematics, and interactive games. "
            "Each task sustains at least 12 hours of agent operation in real world environments. "
            "We publicly release 51 tasks and our full evaluation framework to study how agents learn from real world experience.",
            "2607.05155",
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(relation, "introduces")
        self.assertIn("named benchmark identity and task release stated in nearby sentences", reasons)
        self.assertIn("We publicly release 51 tasks", record["evidence"]["snippet"])
        self.assertEqual(record["area"], "Agents & Tool Use")
        self.assertEqual(record["primaryDomain"], "General AI")
        self.assertEqual(record["construction"], "Interactive Environment")

    def test_iosworld_plural_agents_and_phone_domain(self) -> None:
        paper = sample(
            "iOSWorld: A Benchmark for Personally Intelligent Phone Agents",
            "We introduce iOSWorld, the first interactive native iOS simulator benchmark built around a persistent user identity spanning 26 newly built iOS apps. "
            "The phone agents complete personal workflows including messages, calendars, and a finance app.",
            "2606.09764",
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertEqual(record["area"], "Agents & Tool Use")
        self.assertEqual(record["primaryDomain"], "Mobile & Personal Computing")
        self.assertNotEqual(record["primaryDomain"], "Finance")

    def test_bigfinancebench_remains_language_and_finance(self) -> None:
        paper = sample(
            "BigFinanceBench: A Workflow-Grounded Benchmark for Financial-Research Agents",
            "We introduce BigFinanceBench, a 928-item expert-authored benchmark of open-ended financial-research tasks with ground-truth answers and point-weighted rubrics.",
            "2606.03829",
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertEqual(record["area"], "Language & Knowledge")
        self.assertEqual(record["primaryDomain"], "Finance")

    def test_trading_card_game_does_not_trigger_finance(self) -> None:
        paper = sample(
            "PTCG-Bench: Can LLM Agents Master Pokemon Trading Card Game?",
            "We present PTCG-Bench, a benchmark built on the Pokemon Trading Card Game that evaluates strategic decision making and learning through accumulated game experience.",
            "2605.29653",
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertEqual(record["primaryDomain"], "General AI")
        self.assertNotIn("Finance", record["applicationDomains"])

    def test_multi_domain_time_series_benchmark_is_not_finance_primary(self) -> None:
        paper = sample(
            "TS-Fault: Benchmarking Time Series Forecasters Against Structural Faults",
            "Time series forecasting underpins consequential decisions in energy, transportation, finance, and healthcare. "
            "We present TS-Fault, a benchmark that evaluates forecasting models under explicit parameterized fault scenarios.",
            "2606.18539",
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertEqual(record["primaryDomain"], "General AI")

    def test_spanning_named_domains_is_general_ai_without_finance_title(self) -> None:
        paper = sample(
            "CLBench-V: Evaluating Multimodal Context Learning",
            "We introduce CLBench-V, a benchmark for multimodal context learning spanning domains such as science, finance, long-document understanding, spatial reasoning, and web visual question answering.",
            "2607.25294",
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertEqual(record["primaryDomain"], "General AI")

    def test_algorithmic_trading_remains_finance(self) -> None:
        paper = sample(
            "Backtrader-Bench: Benchmarking LLM Agents on Algorithmic Trading",
            "We present Backtrader-Bench, a benchmark for evaluating coding agents on algorithmic trading workflows.",
            "2608.11232",
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertEqual(record["primaryDomain"], "Finance")

    def test_existing_suite_plus_released_code_is_not_new_benchmark(self) -> None:
        paper = sample(
            "EdgeAgent: Learning from Real-World Environments",
            "We evaluate EdgeAgent on an existing suite of 134 real-world tasks. We publicly release our code and evaluation framework.",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertNotIn(relation, {"introduces", "extends", "aggregates"})

    def test_benchmarking_existing_tasks_with_released_scripts_is_not_release(self) -> None:
        paper = sample(
            "Benchmarking Environment Learning at Scale",
            "We evaluate five agents on 134 existing benchmark tasks and release the reproduction scripts.",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertEqual(relation, "evaluates_only")

    def test_bench_named_model_releasing_weights_is_not_benchmark_release(self) -> None:
        paper = sample(
            "ModelBench: An Agent Model for Long-Horizon Work",
            "ModelBench is a model evaluated on existing benchmarks. We publicly release its weights and evaluation code.",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)

    def test_existing_benchmark_scaling_analysis_is_not_new_release(self) -> None:
        paper = sample(
            "ExistingBench: A Scaling Analysis",
            "ExistingBench is an established benchmark suite of 100 tasks. We publicly release reproduction code for our analysis.",
        )
        score, relation, _ = recognition(paper)
        self.assertLess(score, 0.85)

    def test_accepts_explicit_named_release(self) -> None:
        paper = sample(
            "ClearBench: A Benchmark for Reliable Agents",
            "We introduce ClearBench, a new benchmark with 500 tasks, an evaluation protocol, and strong baselines.",
        )
        score, relation, reasons = recognition(paper)
        self.assertGreaterEqual(score, 0.75)
        self.assertEqual(relation, "introduces")
        self.assertIn("coined title prefix ending in Bench or Benchmark", reasons)
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
        self.assertIn("exact coined title identity tied to benchmark evidence", reasons)
        self.assertEqual(canonical_name(paper), "DeepSWE")

    def test_model_name_near_benchmark_is_not_a_named_benchmark(self) -> None:
        paper = sample(
            "TRUSS: A Retrieval Model",
            "TRUSS improves retrieval performance on the existing MMLU benchmark and several evaluation tasks.",
        )
        score, relation, reasons = recognition(paper)
        self.assertLess(score, 0.85)
        self.assertNotIn("exact coined title identity tied to benchmark evidence", reasons)

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

    def test_evidence_prefers_exact_named_artifact_over_generic_benchmark_phrase(self) -> None:
        paper = sample(
            "From Synthesis to Removal: Video Dereflection",
            "We present a framework for simulation and benchmark evaluation. "
            "We further build S2R-Bench, the first benchmark for video reflection removal."
        )
        score, relation, reasons = recognition(paper)
        record = to_record(paper, "2026-08-19T00:00:00Z", score, relation, reasons)
        self.assertEqual(record["name"], "S2R-Bench")
        self.assertTrue(record["evidence"]["snippet"].startswith("We further build S2R-Bench"))

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

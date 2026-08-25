import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generate_editorial_copy
from generate_editorial_copy import public_release_ready, publishable, publisher_identity_is_distinct, response_text, review_batch, selection_fingerprint, upsert_curated, validate_copy


class DeepSeekReviewTests(unittest.TestCase):
    def valid_decision(self) -> dict:
        return {
            "canonicalName": "ExampleBench",
            "canonicalNameSource": "paper_title",
            "canonicalNameEvidence": "ExampleBench: A repeatable evaluation",
            "decision": "publish",
            "benchmarkMode": "public_reusable",
            "stableScoringContract": True,
            "publicReusePath": True,
            "decisionReason": "A stable public comparison path is documented.",
        }

    def test_chat_completion_content_is_extracted(self) -> None:
        payload = {"choices": [{"message": {"content": '{"records": []}'}}]}
        self.assertEqual(response_text(payload), '{"records": []}')

    def test_only_reusable_scored_public_artifact_is_publishable(self) -> None:
        base = {
            "decision": "publish",
            "benchmarkMode": "public_reusable",
            "stableScoringContract": True,
            "publicReusePath": True,
        }
        self.assertTrue(publishable(base))
        self.assertFalse(publishable({**base, "benchmarkMode": "viewpoint_probe"}))
        self.assertFalse(publishable({**base, "publicReusePath": False}))

    def test_first_person_editorial_copy_is_rejected(self) -> None:
        rows = [{"sourceId": "1", "description": "We evaluate agents.", "whyItMatters": "It supports comparison."}]
        with self.assertRaises(RuntimeError):
            validate_copy({"1": {"officialLinks": {}}}, rows)

    def test_new_github_repo_needs_independent_release_or_strong_adoption(self) -> None:
        repo = {
            "source": {"type": "github", "publicSignals": {"githubStars": 0}},
            "links": {"code": "https://github.com/example/bench"},
        }
        self.assertFalse(public_release_ready(repo))
        self.assertTrue(public_release_ready({**repo, "links": {**repo["links"], "paper": "https://arxiv.org/abs/2608.00001"}}))
        self.assertTrue(public_release_ready({**repo, "source": {"type": "github", "publicSignals": {"githubStars": 25}}}))
        self.assertTrue(public_release_ready({**repo, "attention": {"githubStars": 25}}))
        dataset = {"source": {"type": "huggingface"}, "links": {"data": "https://huggingface.co/datasets/example/bench"}, "attention": {"hfDatasetDownloads": 62, "hfDatasetLikes": 0}}
        self.assertFalse(public_release_ready(dataset))
        self.assertTrue(public_release_ready({**dataset, "attention": {"hfDatasetDownloads": 1000, "hfDatasetLikes": 0}}))

    def test_unsupported_publisher_is_dropped_without_blocking_copy(self) -> None:
        rows = [{
            **self.valid_decision(),
            "sourceId": "1",
            "description": "Evaluates agents on repeatable tasks.",
            "whyItMatters": "Supports comparable system evaluation.",
            "publishers": [{"name": "Example Lab", "organizationType": "academic-lab", "sourceUrl": "https://unsupported.example"}],
        }]
        validate_copy({"1": {"title": "ExampleBench: A repeatable evaluation", "officialLinks": {"code": "https://github.com/example/bench"}}}, rows)
        self.assertEqual(rows[0]["publishers"], [])

    def test_publisher_link_allows_a_trailing_slash_difference(self) -> None:
        rows = [{
            **self.valid_decision(),
            "sourceId": "1",
            "description": "Evaluates agents on repeatable tasks.",
            "whyItMatters": "Supports comparable system evaluation.",
            "publishers": [{"name": "Example Lab", "organizationType": "academic-lab", "sourceUrl": "https://github.com/example/bench/"}],
        }]
        validate_copy({"1": {"title": "ExampleBench: A repeatable evaluation", "officialLinks": {"code": "https://github.com/example/bench"}}}, rows)
        self.assertEqual(rows[0]["publishers"][0]["sourceUrl"], "https://github.com/example/bench")

    def test_canonical_name_requires_verbatim_source_evidence(self) -> None:
        rows = [{
            **self.valid_decision(),
            "sourceId": "1",
            "canonicalName": "InventedBench",
            "canonicalNameEvidence": "InventedBench is the official benchmark.",
            "description": "Evaluates agents on repeatable tasks.",
            "whyItMatters": "Supports comparable system evaluation.",
            "publishers": [],
        }]
        with self.assertRaises(RuntimeError):
            validate_copy({"1": {"title": "A Study of Agent Evaluation", "officialLinks": {}}}, rows)

    def test_canonical_name_can_be_grounded_in_official_readme(self) -> None:
        rows = [{
            **self.valid_decision(),
            "sourceId": "1",
            "canonicalName": "ExampleBench",
            "canonicalNameSource": "official_readme",
            "canonicalNameEvidence": "ExampleBench is a public benchmark",
            "description": "Evaluates agents on repeatable tasks.",
            "whyItMatters": "Supports comparable system evaluation.",
            "publishers": [],
        }]
        validate_copy({"1": {
            "title": "example-benchmark-repo",
            "artifactEvidence": [{"status": "available", "excerpt": "ExampleBench is a public benchmark for agents."}],
            "officialLinks": {},
        }}, rows)
        self.assertEqual(rows[0]["canonicalName"], "ExampleBench")

    def test_deferred_candidate_does_not_need_name_evidence(self) -> None:
        rows = [{
            **self.valid_decision(),
            "sourceId": "1",
            "canonicalName": "",
            "canonicalNameEvidence": "",
            "decision": "defer",
            "benchmarkMode": "unclear",
            "stableScoringContract": False,
            "publicReusePath": False,
            "description": "Evaluates agents on an incompletely documented task.",
            "whyItMatters": "The available evidence is insufficient for comparable evaluation.",
            "publishers": [],
        }]
        validate_copy({"1": {"title": "Agent Evaluation Study", "officialLinks": {}}}, rows)

    def test_name_audit_hides_existing_record_without_supported_name(self) -> None:
        candidate = {
            "name": "odd-repository-slug",
            "source": {"type": "github", "id": "github:example/odd-repository-slug"},
            "links": {"code": "https://github.com/example/odd-repository-slug"},
            "displayEligible": True,
        }
        decision = {
            **self.valid_decision(),
            "sourceId": "github:example/odd-repository-slug",
            "canonicalName": "",
            "canonicalNameEvidence": "",
            "decision": "defer",
            "benchmarkMode": "unclear",
            "stableScoringContract": False,
            "publicReusePath": False,
            "decisionReason": "No formally declared benchmark name is supported by the source.",
        }
        with tempfile.TemporaryDirectory() as directory:
            curated_path = Path(directory) / "curated.json"
            curated_path.write_text(json.dumps({"schemaVersion": "1.0", "records": [candidate]}), encoding="utf-8")
            with patch.object(generate_editorial_copy, "CURATED_PATH", curated_path):
                upsert_curated([candidate], [decision], "2026-08-26T00:00:00Z", "test-model", audit_existing=True)
            record = json.loads(curated_path.read_text(encoding="utf-8"))["records"][0]
        self.assertFalse(record["displayEligible"])
        self.assertEqual(record["curation"]["state"], "ai-name-audit-deferred")

    def test_name_audit_hides_source_grounded_name_without_release_evidence(self) -> None:
        candidate = {
            "name": "odd-repository-slug",
            "source": {"type": "github", "id": "github:example/odd-repository-slug"},
            "links": {"code": "https://github.com/example/odd-repository-slug"},
            "displayEligible": True,
        }
        decision = {
            **self.valid_decision(),
            "sourceId": "github:example/odd-repository-slug",
            "canonicalName": "Odd Repository Benchmark",
            "canonicalNameSource": "official_readme",
            "canonicalNameEvidence": "Odd Repository Benchmark",
        }
        with tempfile.TemporaryDirectory() as directory:
            curated_path = Path(directory) / "curated.json"
            curated_path.write_text(json.dumps({"schemaVersion": "1.0", "records": [candidate]}), encoding="utf-8")
            with patch.object(generate_editorial_copy, "CURATED_PATH", curated_path):
                upsert_curated([candidate], [decision], "2026-08-26T00:00:00Z", "test-model", audit_existing=True)
            record = json.loads(curated_path.read_text(encoding="utf-8"))["records"][0]
        self.assertFalse(record["displayEligible"])
        self.assertEqual(record["curation"]["state"], "ai-name-audit-deferred")

    def test_batch_review_retries_only_the_invalid_name(self) -> None:
        sources = [
            {"sourceId": "1", "title": "OneBench: Evaluation", "officialLinks": {}},
            {"sourceId": "2", "title": "TwoBench: Evaluation", "officialLinks": {}},
        ]
        def row(source_id: str, name: str, evidence: str) -> dict:
            return {
                **self.valid_decision(),
                "sourceId": source_id,
                "canonicalName": name,
                "canonicalNameEvidence": evidence,
                "description": "Evaluates agents on repeatable tasks.",
                "whyItMatters": "Supports comparable system evaluation.",
                "publishers": [],
            }
        first = [row("1", "OneBench", "OneBench: Evaluation"), row("2", "InventedBench", "InventedBench")]
        retry = [row("2", "TwoBench", "TwoBench: Evaluation")]
        with patch("generate_editorial_copy.call_deepseek", side_effect=[first, retry]) as mocked:
            reviewed = review_batch(sources, "test-model", "test-key")
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual([item["canonicalName"] for item in reviewed], ["OneBench", "TwoBench"])

    def test_repository_name_is_not_treated_as_a_publisher(self) -> None:
        self.assertFalse(
            publisher_identity_is_distinct(
                "NCP-Bench", "https://github.com/yingpengma/NCP-Bench", "NCP-Bench"
            )
        )
        self.assertTrue(
            publisher_identity_is_distinct(
                "Example Research Lab", "https://github.com/example/NCP-Bench", "NCP-Bench"
            )
        )

    def test_selection_fingerprint_changes_with_source_revision(self) -> None:
        record = {
            "name": "ExampleBench",
            "paperTitle": "ExampleBench: A Test",
            "source": {"id": "1", "updatedAt": "2026-08-20T00:00:00Z"},
            "links": {"code": "https://github.com/example/bench"},
        }
        first = selection_fingerprint(record)
        record["source"]["updatedAt"] = "2026-08-21T00:00:00Z"
        self.assertNotEqual(first, selection_fingerprint(record))


if __name__ == "__main__":
    unittest.main()

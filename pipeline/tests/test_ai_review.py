from __future__ import annotations

import os
from io import BytesIO
import json
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from review_candidates_with_deepseek import (
    automatic_promotion,
    candidate_fingerprint,
    deepseek_request_payload,
    deepseek_output_json,
    invoke_deepseek_api,
    promotion_gate_errors,
    restore_promoted_overlay,
    validate_critic_decisions,
    validate_decisions,
)


def candidate() -> dict:
    return {
        "id": "bm_deepswe",
        "paperTitle": "DeepSWE: Measuring Frontier Coding Agents",
        "reviewContext": {
            "abstract": "We introduce DeepSWE, a benchmark of 113 original software engineering tasks.",
            "comments": "",
        },
    }


def full_candidate() -> dict:
    value = candidate()
    value.update({
        "familyId": "bmf_old",
        "name": "DeepSWE: Measuring Frontier Coding Agents",
        "oneLine": "A benchmark of original software engineering tasks.",
        "area": "Code & Software",
        "applicationDomains": ["Software & AI Compute"],
        "primaryDomain": "Software & AI Compute",
        "industrySectors": ["Software & Cloud"],
        "capabilities": ["Code generation"],
        "topics": ["Code"],
        "construction": "Human Authored",
        "annotation": "Human",
        "readiness": "Paper only",
        "releasedAt": "2026-07-10",
        "firstSeenAt": "2026-07-11",
        "indexedAt": "2026-07-11T00:00:00Z",
        "recognitionConfidence": 0.6,
        "relation": "introduces",
        "links": {
            "report": "https://arxiv.org/abs/2607.07946",
            "paper": "https://arxiv.org/abs/2607.07946",
            "pdf": "https://arxiv.org/pdf/2607.07946",
            "project": None,
            "code": None,
            "data": None,
        },
        "source": {
            "type": "arxiv",
            "id": "2607.07946",
            "url": "https://arxiv.org/abs/2607.07946",
            "title": "DeepSWE: Measuring Frontier Coding Agents",
        },
        "evidence": {"snippet": "", "reasonCodes": ["benchmark release stated in one sentence"]},
        "dataStatus": "primary-source-indexed",
        "demo": False,
    })
    return value


def release_response(confidence: float = 0.98, quote: str | None = None) -> dict:
    return {
        "decisions": [{
            "id": "bm_deepswe",
            "verdict": "benchmark_release",
            "relation": "introduces",
            "artifact_role": "reusable_benchmark",
            "benchmark_name": "DeepSWE",
            "evidence_quote": quote or "We introduce DeepSWE, a benchmark of 113 original software engineering tasks.",
            "confidence": confidence,
            "reason": "Explicit identity statement.",
        }]
    }


def critic_response(base: dict | None = None, *, supported: bool = True) -> dict:
    decision = dict((base or release_response())["decisions"][0])
    decision["evidence_supported"] = supported
    return {"decisions": [decision]}


def release_critics(item: dict, response: dict | None = None) -> list[dict]:
    return validate_critic_decisions([item], critic_response(response))


class AiReviewTests(unittest.TestCase):
    def deepseek_http_response(self, content: str, finish_reason: str = "stop") -> Mock:
        response = Mock()
        response.read.return_value = (
            '{"choices":[{"finish_reason":"%s","message":{"content":%s}}]}'
            % (finish_reason, json.dumps(content))
        ).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        return response

    def test_unconfigured_deepseek_skips_successfully(self) -> None:
        environment = dict(os.environ)
        for name in ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL"):
            environment.pop(name, None)
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "review_candidates_with_deepseek.py"),
                "--skip-unconfigured",
            ],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("skipped", result.stdout)

    def test_deepseek_payload_has_json_mode_thinking_and_no_tools_or_secret(self) -> None:
        payload = deepseek_request_payload([candidate()], "deepseek-v4-pro")
        rendered = str(payload)
        self.assertNotIn("secret-value", rendered)
        self.assertNotIn("tools", payload)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "enabled"})
        self.assertEqual(payload["reasoning_effort"], "high")

    def test_critic_payload_is_independent_second_stage(self) -> None:
        classifier = release_response()["decisions"]
        payload = deepseek_request_payload([candidate()], "deepseek-v4-pro", critic_of=classifier)
        prompt = payload["messages"][1]["content"]
        self.assertIn("independent critic", prompt)
        self.assertIn("classifier_decision", prompt)
        self.assertIn("evidence_supported", prompt)

    def test_deepseek_only_accepts_stop(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "finish with stop"):
            deepseek_output_json({"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]})

    @patch("review_candidates_with_deepseek.time.sleep")
    @patch("review_candidates_with_deepseek.urlopen")
    def test_deepseek_retries_429_then_succeeds(self, urlopen_mock: Mock, _sleep: Mock) -> None:
        throttled = HTTPError("https://api.deepseek.com/chat/completions", 429, "rate", {"Retry-After": "1"}, BytesIO())
        urlopen_mock.side_effect = [throttled, self.deepseek_http_response('{"decisions":[]}')]
        self.assertEqual(invoke_deepseek_api([], "deepseek-v4-pro", "secret"), {"decisions": []})
        self.assertEqual(urlopen_mock.call_count, 2)

    @patch("review_candidates_with_deepseek.time.sleep")
    @patch("review_candidates_with_deepseek.urlopen")
    def test_deepseek_retries_empty_content_then_succeeds(self, urlopen_mock: Mock, _sleep: Mock) -> None:
        urlopen_mock.side_effect = [
            self.deepseek_http_response(""),
            self.deepseek_http_response('{"decisions":[]}'),
        ]
        self.assertEqual(invoke_deepseek_api([], "deepseek-v4-pro", "secret"), {"decisions": []})
        self.assertEqual(urlopen_mock.call_count, 2)

    @patch("review_candidates_with_deepseek.urlopen")
    def test_deepseek_does_not_retry_400(self, urlopen_mock: Mock) -> None:
        urlopen_mock.side_effect = HTTPError("https://api.deepseek.com/chat/completions", 400, "bad", {}, BytesIO())
        with self.assertRaisesRegex(RuntimeError, "HTTP 400"):
            invoke_deepseek_api([], "deepseek-v4-pro", "secret")
        self.assertEqual(urlopen_mock.call_count, 1)

    def test_accepts_exact_release_evidence(self) -> None:
        result = validate_decisions([candidate()], release_response())
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

    def test_high_confidence_exact_release_is_promoted(self) -> None:
        item = full_candidate()
        decisions = validate_decisions([item], release_response())
        canonical, queue, statuses = automatic_promotion(
            {"generatedAt": "2026-07-11T00:00:00Z", "candidates": [item]},
            {"manifest": {"recordCount": 0}, "records": []},
            decisions,
            release_critics(item),
            model="test-model",
            reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "promoted")
        self.assertEqual(canonical["records"][0]["name"], "DeepSWE")
        self.assertEqual(canonical["records"][0]["evidence"]["snippet"], decisions[0]["evidence_quote"])
        self.assertEqual(canonical["records"][0]["recognitionConfidence"], 0.6)
        self.assertEqual(canonical["records"][0]["aiPromotion"]["semanticConfidence"], 0.98)
        self.assertIn("canonicalRecord", statuses[0])
        self.assertEqual(queue["candidates"], [])

    def test_low_confidence_release_is_deferred(self) -> None:
        item = full_candidate()
        response = release_response(confidence=0.79)
        decisions = validate_decisions([item], response)
        canonical, queue, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions,
            release_critics(item, response),
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "deferred")
        self.assertEqual(canonical["records"], [])
        self.assertEqual(queue["candidates"][0]["autoReview"]["status"], "deferred")

    def test_classifier_and_critic_can_confirm_without_keyword_veto(self) -> None:
        item = full_candidate()
        quote = "DeepSWE is a benchmark of 113 original software engineering tasks."
        item["reviewContext"]["abstract"] = quote
        decisions = validate_decisions([item], release_response(quote=quote))
        _, _, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions,
            release_critics(item, release_response(quote=quote)),
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "promoted")

    def test_deterministic_relation_does_not_veto_semantic_agreement(self) -> None:
        item = full_candidate()
        item["relation"] = "evaluates_only"
        decisions = validate_decisions([item], release_response())
        _, _, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions,
            release_critics(item),
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "promoted")

    def test_high_confidence_existing_benchmark_use_is_rejected(self) -> None:
        item = full_candidate()
        negative_quote = "We evaluate six models on the existing SWE-bench benchmark and report accuracy."
        item["reviewContext"]["abstract"] = negative_quote
        response = {"decisions": [{
            "id": "bm_deepswe",
            "verdict": "uses_existing_benchmark",
            "relation": "evaluates_only",
            "artifact_role": "uses_existing_benchmarks",
            "benchmark_name": "SWE-bench",
            "evidence_quote": negative_quote,
            "confidence": 0.99,
            "reason": "The paper only reports results.",
        }]}
        decisions = validate_decisions([item], response)
        canonical, queue, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions,
            validate_critic_decisions([item], critic_response(response)),
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "rejected")
        self.assertEqual(canonical["records"], [])
        self.assertEqual(queue["candidates"][0]["autoReview"]["status"], "rejected")

    def test_unclear_or_invalid_nonrelease_is_deferred(self) -> None:
        item = full_candidate()
        response = {"decisions": [{
            "id": "bm_deepswe", "verdict": "unclear", "relation": "unclear",
            "artifact_role": "unclear", "benchmark_name": "", "evidence_quote": "",
            "confidence": 0.99, "reason": "Insufficient evidence.",
        }]}
        decisions = validate_decisions([item], response)
        _, _, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions,
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "deferred")

    def test_duplicate_library_source_is_deferred(self) -> None:
        item = full_candidate()
        decisions = validate_decisions([item], release_response())
        canonical, _, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions,
            library_records=[{"source": {"id": "2607.07946"}}],
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "deferred")
        self.assertEqual(len(canonical["records"]), 0)
        self.assertIn("source id already exists in established library data", statuses[0]["gateErrors"])

    def test_existing_radar_source_is_revalidated_in_place(self) -> None:
        item = full_candidate()
        legacy = dict(item)
        legacy.pop("reviewContext", None)
        legacy["attention"] = {"githubStars": 42}
        decisions = validate_decisions([item], release_response())
        canonical, _, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": [legacy]}, decisions,
            release_critics(item),
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "promoted")
        self.assertEqual(len(canonical["records"]), 1)
        self.assertEqual(canonical["records"][0]["attention"]["githubStars"], 42)
        self.assertEqual(canonical["records"][0]["aiPromotion"]["semanticConfidence"], 0.98)

    def test_duplicate_library_family_is_deferred(self) -> None:
        item = full_candidate()
        decisions = validate_decisions([item], release_response())
        library = [{"familyId": "bmf_3f6a106b16bd", "source": {"id": "library-deepswe"}}]
        # Use the exact family produced by the implementation rather than a
        # hand-maintained hash fixture.
        from index_benchmarks import family_id
        library[0]["familyId"] = family_id("DeepSWE")
        _, _, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions,
            library_records=library, model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertIn("benchmark identity already exists in established library data", statuses[0]["gateErrors"])

    def test_promoted_ledger_restores_missing_canonical_record(self) -> None:
        item = full_candidate()
        decisions = validate_decisions([item], release_response())
        canonical, _, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions,
            release_critics(item),
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        restored, count = restore_promoted_overlay(
            {"manifest": {"recordCount": 0}, "records": []},
            {"entries": statuses},
        )
        self.assertEqual(count, 1)
        self.assertEqual(restored["records"][0]["id"], canonical["records"][0]["id"])

    def test_fingerprint_changes_with_model_and_candidate_evidence(self) -> None:
        item = full_candidate()
        original = candidate_fingerprint(item, "model-a")
        self.assertNotEqual(original, candidate_fingerprint(item, "model-b"))
        item["evidence"]["reasonCodes"].append("policy-relevant change")
        self.assertNotEqual(original, candidate_fingerprint(item, "model-a"))

    def test_source_unsupported_url_blocks_promotion(self) -> None:
        item = full_candidate()
        item["links"]["code"] = "https://example.test/invented"
        decisions = validate_decisions([item], release_response())
        errors = promotion_gate_errors(item, decisions[0], release_critics(item)[0], [], [], 0.95)
        self.assertIn("links.code is not supported by source text", errors)

    def test_critic_disagreement_forces_defer(self) -> None:
        item = full_candidate()
        decisions = validate_decisions([item], release_response())
        critic = critic_response()
        critic["decisions"][0]["relation"] = "extends"
        critics = validate_critic_decisions([item], critic)
        _, _, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions, critics,
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "deferred")
        self.assertIn("classifier and critic disagree on relation", statuses[0]["gateErrors"])

    def test_missing_critic_forces_defer(self) -> None:
        item = full_candidate()
        decisions = validate_decisions([item], release_response())
        _, _, statuses = automatic_promotion(
            {"candidates": [item]}, {"manifest": {}, "records": []}, decisions,
            model="test-model", reviewed_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual(statuses[0]["status"], "deferred")
        self.assertIn("independent DeepSeek critic result is unavailable", statuses[0]["gateErrors"])


if __name__ == "__main__":
    unittest.main()

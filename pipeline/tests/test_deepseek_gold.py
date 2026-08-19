from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from review_candidates_with_deepseek import (
    automatic_promotion,
    build_prompt,
    candidate_payload,
    validate_critic_decisions,
    validate_decisions,
)


FIXTURE = Path(__file__).parent / "fixtures" / "deepseek_semantic_gold.json"


def candidate(case: dict) -> dict:
    source_id = case["id"]
    return {
        "id": f"gold_{source_id.replace('.', '_')}",
        "familyId": "bmf_gold",
        "name": case["title"],
        "paperTitle": case["title"],
        "oneLine": case["abstract"],
        "area": "Language & Knowledge",
        "applicationDomains": ["General AI"],
        "primaryDomain": "General AI",
        "industrySectors": [],
        "capabilities": ["Evaluation"],
        "topics": ["Evaluation"],
        "construction": "Unknown",
        "annotation": "Unknown",
        "readiness": "Paper only",
        "releasedAt": "2026-08-10",
        "firstSeenAt": "2026-08-11",
        "indexedAt": "2026-08-11T00:00:00Z",
        "recognitionConfidence": 0.5,
        "relation": "evaluates_only",
        "links": {
            "report": f"https://arxiv.org/abs/{source_id}",
            "paper": f"https://arxiv.org/abs/{source_id}",
            "pdf": f"https://arxiv.org/pdf/{source_id}",
            "project": None, "code": None, "data": None,
        },
        "source": {
            "type": "arxiv", "id": source_id,
            "url": f"https://arxiv.org/abs/{source_id}", "title": case["title"],
        },
        "evidence": {"snippet": "", "reasonCodes": ["recall-only candidate"]},
        "dataStatus": "primary-source-indexed",
        "demo": False,
        "reviewContext": {"abstract": case["abstract"], "comments": ""},
    }


class DeepSeekGoldFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_covers_required_semantic_boundaries(self) -> None:
        cases = self.payload["cases"]
        self.assertGreaterEqual(len(cases), 10)
        self.assertLessEqual(len(cases), 20)
        statuses = {case["expectedStatus"] for case in cases}
        self.assertEqual(statuses, {"promoted", "rejected_excluded", "rejected", "deferred"})
        roles = {case["decision"]["artifact_role"] for case in cases}
        self.assertTrue({"reusable_benchmark", "diagnostic_benchmark", "uses_existing_benchmarks"} <= roles)
        self.assertTrue(any(case["decision"]["relation"] == "aggregates" for case in cases))
        self.assertTrue(any("implementation code is not yet public" in case["abstract"] for case in cases))
        self.assertTrue(any("training" in case["abstract"] and case["expectedStatus"] == "deferred" for case in cases))

    def test_gold_decisions_traverse_real_classifier_critic_gates_offline(self) -> None:
        for case in self.payload["cases"]:
            with self.subTest(case=case["id"]):
                item = candidate(case)
                raw = {**case["decision"], "id": item["id"]}
                decisions = validate_decisions([item], {"decisions": [raw]})
                critics = []
                if raw["verdict"] != "unclear":
                    critics = validate_critic_decisions(
                        [item], {"decisions": [{**raw, "evidence_supported": True}]}
                    )
                canonical, _, statuses = automatic_promotion(
                    {"candidates": [item]}, {"manifest": {}, "records": []},
                    decisions, critics, model="deepseek-v4-flash",
                    reviewed_at="2026-08-12T00:00:00Z",
                )
                self.assertEqual(statuses[0]["status"], case["expectedStatus"])
                self.assertEqual(bool(canonical["records"]), case["expectedStatus"] == "promoted")

    def test_gold_prompt_is_bounded_for_flash(self) -> None:
        items = [candidate(case) for case in self.payload["cases"]]
        prompt = build_prompt(items)
        self.assertLess(len(prompt), 50_000)
        self.assertEqual(set(candidate_payload(items[0])), {"id", "title", "abstract", "comments"})


if __name__ == "__main__":
    unittest.main()

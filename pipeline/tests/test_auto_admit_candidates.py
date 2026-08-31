from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auto_admit_candidates import admit_candidates, automatically_publishable


class AutomaticAdmissionTests(unittest.TestCase):
    def candidate(self, **updates):
        record = {
            "id": "bm_example",
            "name": "ExampleBench",
            "relation": "introduces",
            "recognitionConfidence": 1.0,
            "releasedAt": "2026-08-28",
            "source": {"type": "arxiv", "id": "2608.00001"},
            "evidence": {
                "reasonCodes": [
                    "exact named benchmark artifact released in abstract",
                    "evaluation protocol evidence",
                ]
            },
            "reviewContext": {"abstract": "We introduce ExampleBench."},
            "candidatePriority": "high",
            "capabilities": ["Evaluation", "Reasoning"],
        }
        record.update(updates)
        return record

    def test_high_confidence_named_release_is_automatically_publishable(self):
        self.assertTrue(automatically_publishable(self.candidate(), 0.85))

    def test_existing_benchmark_study_is_not_automatically_published(self):
        self.assertFalse(
            automatically_publishable(
                self.candidate(relation="evaluates_only"), 0.85
            )
        )

    def test_low_confidence_candidate_remains_for_audit(self):
        self.assertFalse(
            automatically_publishable(
                self.candidate(recognitionConfidence=0.6), 0.85
            )
        )

    def test_named_release_without_evaluation_protocol_remains_for_audit(self):
        self.assertFalse(
            automatically_publishable(
                self.candidate(
                    evidence={
                        "reasonCodes": [
                            "exact named benchmark artifact released in abstract"
                        ]
                    }
                ),
                0.85,
            )
        )

    def test_admission_promotes_and_removes_candidate_from_queue(self):
        publish = self.candidate()
        keep = self.candidate(
            id="bm_keep",
            name="Unclear Study",
            recognitionConfidence=0.4,
            source={"type": "arxiv", "id": "2608.00002"},
        )
        data, queue, promoted = admit_candidates(
            {"manifest": {}, "records": []},
            {"candidates": [publish, keep]},
            0.85,
            "2026-08-31T00:00:00Z",
        )
        self.assertEqual([record["name"] for record in promoted], ["ExampleBench"])
        self.assertEqual(data["records"][0]["curation"]["state"], "rule-auto-admitted")
        self.assertNotIn("reviewContext", data["records"][0])
        self.assertEqual(data["records"][0]["capabilities"], ["Reasoning"])
        self.assertEqual([record["name"] for record in queue["candidates"]], ["Unclear Study"])
        self.assertEqual(queue["automaticAdmission"]["promoted"], 1)


if __name__ == "__main__":
    unittest.main()

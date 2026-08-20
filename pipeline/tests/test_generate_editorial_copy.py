import unittest

from generate_editorial_copy import publishable, response_text, selection_fingerprint, validate_copy


class DeepSeekReviewTests(unittest.TestCase):
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

    def test_publisher_requires_an_official_input_link(self) -> None:
        rows = [{
            "sourceId": "1",
            "description": "Evaluates agents on repeatable tasks.",
            "whyItMatters": "Supports comparable system evaluation.",
            "publishers": [{"name": "Example Lab", "organizationType": "academic-lab", "sourceUrl": "https://unsupported.example"}],
        }]
        with self.assertRaises(RuntimeError):
            validate_copy({"1": {"officialLinks": {"code": "https://github.com/example/bench"}}}, rows)

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

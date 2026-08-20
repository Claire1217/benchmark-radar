import unittest

from generate_editorial_copy import publishable, response_text, validate_copy


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
            validate_copy({"1"}, rows)


if __name__ == "__main__":
    unittest.main()

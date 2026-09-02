from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_overrides import curated_records_without_derived_attention


class ApplyOverridesTests(unittest.TestCase):
    @patch("apply_overrides.curated_records")
    def test_reviewed_records_cannot_overwrite_derived_attention(self, records):
        records.return_value = [{
            "id": "bm_example",
            "name": "ExampleBench",
            "attention": {"githubStars": 1},
            "ranking": {"today": {"score": None}},
            "watch": {"status": "watch"},
            "curation": {"state": "ai-reviewed"},
        }]

        result = curated_records_without_derived_attention()[0]

        self.assertNotIn("attention", result)
        self.assertNotIn("ranking", result)
        self.assertNotIn("watch", result)
        self.assertEqual(result["curation"], {"state": "ai-reviewed"})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import enrich_publications


class PublicationEnrichmentTests(unittest.TestCase):
    def test_source_outage_keeps_canonical_data_and_does_not_fail_update(self) -> None:
        payload = {
            "manifest": {},
            "records": [{
                "id": "example",
                "source": {"type": "arxiv", "id": "2608.12345"},
                "publication": {"status": "published", "venue": "ExampleConf"},
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_path = root / "benchmarks.json"
            receipt_dir = root / "publication"
            data_path.write_text(json.dumps(payload), encoding="utf-8")

            with (
                patch.object(enrich_publications, "DATA_PATH", data_path),
                patch.object(enrich_publications, "RECEIPT_DIR", receipt_dir),
                patch.object(enrich_publications, "fetch_batch", side_effect=OSError("source unavailable")),
                patch.object(sys, "argv", ["enrich_publications.py"]),
            ):
                enrich_publications.main()

            self.assertEqual(json.loads(data_path.read_text(encoding="utf-8")), payload)
            receipts = list(receipt_dir.glob("*.json"))
            self.assertEqual(len(receipts), 1)
            receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "source_unavailable_canonical_unchanged")
            self.assertEqual(receipt["recordsChecked"], 0)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from pipeline.sync_catalogs import build_payload, parse_llm_stats


class CatalogSyncTests(unittest.TestCase):
    def test_parses_next_catalog_payload(self):
        rows = [{"benchmark_id": "gpqa", "name": "GPQA", "categories": ["reasoning"]}]
        chunk = [1, 'x:{"initialBenchmarks":' + json.dumps(rows) + ',"rest":true}']
        body = f'<script>self.__next_f.push({json.dumps(chunk)})</script>'.encode()
        self.assertEqual(parse_llm_stats(body), rows)

    def test_rejects_incomplete_catalog_snapshots(self):
        benchlm = json.dumps({"items": [{"benchmarkKey": "x", "name": "X"}]}).encode()
        rows = [{"benchmark_id": "x", "name": "X", "categories": []}]
        chunk = [1, 'x:{"initialBenchmarks":' + json.dumps(rows) + '}']
        llm_stats = f'<script>self.__next_f.push({json.dumps(chunk)})</script>'.encode()
        with self.assertRaisesRegex(ValueError, "unexpectedly small"):
            build_payload(benchlm, llm_stats, "2026-08-21T00:00:00Z")


if __name__ == "__main__":
    unittest.main()

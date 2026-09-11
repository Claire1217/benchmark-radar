import contextlib
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usage_store import UsageStore, align
from import_usage import is_vendor_report
from benchmark_reader import run

class UsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = UsageStore()

    def test_shared_paper_does_not_merge_versions(self):
        library = [{'id': 'diamond', 'name': 'GPQA Diamond', 'links': {'paper': 'https://arxiv.org/abs/2301.12345'}}]
        imported = [{'id': 'full', 'name': 'GPQA', 'aliases': ['GPQA Diamond'], 'identityUrls': ['https://arxiv.org/pdf/2301.12345.pdf']}]
        self.assertIsNone(align(imported, library)['full']['localId'])
        imported[0]['name'] = 'GPQA Diamond'
        self.assertEqual(align(imported, library)['full']['localId'], 'diamond')
        library.append(dict(library[0], id='duplicate'))
        self.assertEqual(align(imported, library)['full']['status'], 'ambiguous')

    def test_leaderboard_is_not_vendor_report(self):
        self.assertFalse(is_vendor_report({'source': 'model_reports', 'organization': 'ApodexAI', 'document_type': 'benchmark_leaderboard'}))
        result = self.store.summary(['usage:model-reports:frontier_challenge'])
        self.assertEqual(result['reportedLabCount'], 0)
        self.assertEqual(result['reportCount'], 0)
        self.assertEqual(result['scoreObservationCount'], 13)

    def test_gpqa_counts_and_unknowns(self):
        summary = self.store.summary(['usage:model-reports:gpqa_diamond'])
        self.assertEqual((summary['reportedLabCount'], summary['reportCount'], summary['scoreObservationCount']), (11, 27, 21))
        self.assertEqual(summary, self.store.summary(['usage:model-reports:gpqa_diamond'] * 2))
        self.assertIsNone(summary['actualRunCount'])
        self.assertEqual(summary['saturation'], 'unknown')

    def test_snapshot_integrity(self):
        store = self.store
        ids = {r['id'] for r in store.records}
        self.assertEqual(len(ids), 1284)
        self.assertEqual(len({r['id'] for r in store.observations}), 12929)
        self.assertEqual(sum(r['kind'] == 'upstream_report_mention' for r in store.mentions), 447)
        for row in store.mentions + store.observations:
            self.assertIn(row['benchmarkId'], ids)
            if row.get('documentId'):
                self.assertIn(row['documentId'], store.documents)

    def invoke(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = run(args)
        return status, json.loads(output.getvalue())

    def test_agent_errors(self):
        for args, status, code in [(['show', 'definitely-nonexistent-benchmark'], 3, 'not_found'), (['search', '--limit', '0'], 2, 'invalid_arguments'), (['show', 'AA-LCR'], 2, 'ambiguous_identity')]:
            actual, result = self.invoke(args)
            self.assertEqual(actual, status)
            self.assertFalse(result['ok'])
            self.assertEqual(result['error']['code'], code)

    def test_pagination_and_source_id_resolution(self):
        status, result = self.invoke(['show', 'usage:model-reports:gpqa_diamond', '--limit', '1'])
        self.assertEqual(status, 0)
        self.assertEqual(result['data']['benchmark']['id'], 'lib_gpqa_diamond')
        self.assertEqual(len(result['data']['observations']), 1)
        self.assertEqual(result['data']['pagination']['nextOffset'], 1)
        self.assertEqual(result['data']['usage']['reportCount'], 27)

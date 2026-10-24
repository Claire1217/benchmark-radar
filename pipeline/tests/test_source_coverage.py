import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import discover_benchmarks as discovery
import index_benchmarks as index
import source_coverage as coverage


class CoverageTests(unittest.TestCase):
    def test_new_success_does_not_clear_old_debt_and_replay_is_idempotent(self):
        payload = {'windows': {}}
        old = coverage.enqueue(payload, 'arxiv', 'cs.AR', '2026-10-01', '2026-10-03')
        new = coverage.enqueue(payload, 'arxiv', 'cs.AR', '2026-10-20', '2026-10-22')
        coverage.attempt(payload, old, now='2026-10-24T00:00:00Z', status='failed', error='source outage')
        coverage.attempt(payload, new, now='2026-10-24T00:00:00Z', status='complete', candidate_hash='abc')
        self.assertEqual(coverage.pending(payload, '2026-10-24T03:00:00Z')[0][0], old)
        self.assertEqual(coverage.pending(payload, '2026-10-24T01:00:00Z'), [])
        coverage.enqueue(payload, 'arxiv', 'cs.AR', '2026-10-01', '2026-10-03')
        self.assertEqual(len(payload['windows']), 2)
        coverage.attempt(payload, old, now='2026-10-24T03:00:00Z', status='complete', candidate_hash='def')
        self.assertEqual(coverage.pending(payload, '2026-10-25T00:00:00Z'), [])
        self.assertEqual(payload['windows'][old]['attemptCount'], 2)

    def test_completion_without_persisted_receipt_is_rejected(self):
        payload = {'windows': {}}
        identifier = coverage.enqueue(payload, 'arxiv', 'cs.AR', '2026-10-01', '2026-10-03')
        with self.assertRaises(ValueError):
            coverage.attempt(payload, identifier, now='2026-10-24T00:00:00Z', status='complete')

    def test_oai_namespace_mapping_and_active_registry(self):
        for category, expected in {'cs.AR': 'cs:cs:AR', 'eess.AS': 'eess:eess:AS',
            'q-bio.QM': 'q-bio:q-bio:QM', 'cond-mat.mtrl-sci': 'physics:cond-mat:mtrl-sci',
            'quant-ph': 'physics:quant-ph', 'physics.comp-ph': 'physics:physics:comp-ph'}.items():
            self.assertEqual(index.category_to_set_spec(category), expected)
        root = Path(__file__).resolve().parents[2]
        config = json.loads((root / 'pipeline/config.json').read_text())
        registry = json.loads((root / 'data/source_registry.json').read_text())
        self.assertEqual(config['arxiv']['categories'], registry['activeCategories'])
        self.assertTrue({'cs.AR','cs.CR','cs.IR','cs.SD','cs.HC','eess.AS','stat.ML'} <= set(registry['activeCategories']))
        for category in registry['activeCategories']:
            index.category_to_set_spec(category)

    def test_empty_arxiv_replay_preserves_all_pending_sources(self):
        records = [{'id': 'a', 'releasedAt': '2026-10-01', 'source': {'type': 'arxiv', 'id': 'a'}},
                   {'id': 'g', 'releasedAt': '2026-10-01', 'source': {'type': 'github', 'id': 'g'}}]
        result = index.persistent_review_candidates(copy.deepcopy(records), [], '2026-10-01', '2026-10-03', set())
        self.assertEqual({r['id'] for r in result}, {'a', 'g'})

    def test_failed_scope_retains_queue_and_other_scope_completes(self):
        cfg = {'arxiv': {'categories': ['cs.AI', 'cs.AR']}, 'thresholds': {'review': .4, 'publish': .85}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue, ledger = root/'queue.json', root/'coverage.json'
            original = {'id':'pending', 'name':'Pending', 'releasedAt':'2026-10-24',
                        'source':{'type':'github','id':'github:lab/pending'}}
            queue.write_text(json.dumps({'candidates':[original]}))
            canonical = root/'canonical.json';canonical.write_text('{"records":[]}')
            with patch.multiple(discovery, REVIEW_PATH=queue, COVERAGE_PATH=ledger, RUNS_PATH=root/'runs'), \
                    patch.object(index, 'DATA_PATH', canonical), patch.object(index, 'curated_records', return_value=[]), \
                    patch.object(index, 'fetch_for_range', side_effect=[URLError('down'), []]), \
                    patch.object(index, 'fetch_for_range_atom', side_effect=URLError('down')):
                result = discovery.discover('2026-10-24', cfg, sources={'arxiv'})
            self.assertEqual((result['complete'], result['failed']), (1, 1))
            self.assertEqual(json.loads(queue.read_text())['candidates'], [original])
            self.assertEqual(sorted(w['status'] for w in json.loads(ledger.read_text())['windows'].values()), ['complete', 'failed'])
            # Same completed scope must not be fetched again, and failure cooldown remains.
            with patch.multiple(discovery, REVIEW_PATH=queue, COVERAGE_PATH=ledger, RUNS_PATH=root/'runs'), \
                    patch.object(index, 'DATA_PATH', canonical), patch.object(index, 'curated_records', return_value=[]), \
                    patch.object(index, 'fetch_for_range') as fetch:
                result = discovery.discover('2026-10-24', cfg, sources={'arxiv'})
            fetch.assert_not_called()
            self.assertEqual(result['outstandingWindows'], 1)

    def test_interruption_after_candidates_persist_never_marks_window_complete(self):
        cfg = {'arxiv': {'categories': ['cs.AR']}, 'thresholds': {'review': .4, 'publish': .85}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); ledger=root/'ledger.json'
            with patch.multiple(discovery, COVERAGE_PATH=ledger, REVIEW_PATH=root/'queue.json'), \
                    patch.object(index, 'fetch_for_range', return_value=[]), \
                    patch.object(discovery, 'merge_review_queue', side_effect=OSError('disk unavailable')):
                with self.assertRaises(OSError):
                    discovery.discover('2026-10-24', cfg, sources={'arxiv'})
            self.assertEqual(next(iter(json.loads(ledger.read_text())['windows'].values()))['status'], 'pending')

    def test_dry_run_writes_no_ledger_or_candidates(self):
        cfg={'arxiv':{'categories':['cs.AR']},'thresholds':{'review':.4,'publish':.85}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.multiple(discovery, COVERAGE_PATH=root/'ledger.json', REVIEW_PATH=root/'queue.json'), \
                    patch.object(index, 'fetch_for_range', return_value=[]):
                discovery.discover('2026-10-24', cfg, dry_run=True, sources={'arxiv'})
            self.assertEqual(list(root.iterdir()), [])

    def test_github_does_not_certify_search_caps_or_missing_totals(self):
        for result in ({'items':[], 'total_count': 1001}, {'items':[], 'incomplete_results':True, 'total_count':0}, {'items':[]}):
            with patch.object(discovery, 'fetch_json', return_value=result), self.assertRaises(index.IncompleteHarvestError):
                discovery.github_candidates('2026-10-24')

    def test_hf_follows_next_page_and_stops_only_below_target_day(self):
        with patch.object(discovery, 'fetch_json_page', side_effect=[
                ([{'id':'new','createdAt':'2026-10-25'}], 'https://huggingface.co/api/datasets?cursor=2'),
                ([{'id':'target','createdAt':'2026-10-24'}, {'id':'old','createdAt':'2026-10-23'}], None)]) as fetch:
            rows=list(discovery.huggingface_pages('https://huggingface.co/api/datasets', '2026-10-24'))
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual([r['id'] for r in rows], ['new','target','old'])

    def test_hf_cap_and_openreview_early_page_are_failures(self):
        with patch.object(discovery, 'fetch_json_page', return_value=([{'createdAt':'2026-10-24'}]*500, None)), \
                self.assertRaises(index.IncompleteHarvestError):
            list(discovery.huggingface_pages('https://huggingface.co/api/datasets', '2026-10-24'))
        with patch.object(discovery, 'fetch_json', side_effect=[{'notes':[{'id':'one'}], 'count':2}, {'notes':[], 'count':2}]), \
                self.assertRaises(index.IncompleteHarvestError):
            discovery.openreview_candidates('2026-10-24')


if __name__=='__main__':
    unittest.main()

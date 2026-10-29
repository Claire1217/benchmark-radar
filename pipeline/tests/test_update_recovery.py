import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from generate_library_index import assemble_catalog_records, public_catalog
from library_categories import annotate_categories
from index_benchmarks import persistent_review_candidates
from update_status import catchup_end, coverage_through, next_date, public_status, record


class CatalogIdentityRecoveryTests(unittest.TestCase):
    def test_live_catalog_cannot_shadow_reviewed_anchor(self):
        reviews = json.loads((ROOT / 'data/library_source_reviews.json').read_text())
        original = next(r for r in reviews['additions'] if r['id'] == 'review_longmemeval')
        source = {
            'id': 'catalog_5cbfbdb444ca8b83', 'name': 'LongMemEval',
            'normalizedName': 'longmemeval', 'aliases': [], 'categories': [],
            'description': 'Tests whether a chat assistant recalls and reasons over information spread across long, multi-session conversation histories.',
            'sourceRecords': [{'catalog': 'fixture', 'url': 'https://github.com/xiaowu0162/LongMemEval'}],
        }
        # Reproduce the original competing keyword classification.
        competing = public_catalog(source, '2026-10-24')
        annotate_categories([competing])
        self.assertEqual(competing['libraryCategories'], ['chat-writing'])
        before = copy.deepcopy(original)
        rows, redirects, merged, only = assemble_catalog_records(
            [], [], {'records': [source]}, {'additions': [original]})
        annotate_categories(rows)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], 'review_longmemeval')
        self.assertIn('agent-memory', rows[0]['libraryCategories'])
        self.assertEqual(redirects[source['id']], rows[0]['id'])
        self.assertEqual((merged, only), (1, 0))
        self.assertEqual(original, before)
        self.assertEqual(rows[0]['catalogSources'], source['sourceRecords'])


class RetryQueueTests(unittest.TestCase):
    def test_empty_retry_keeps_same_day_candidates_from_every_source(self):
        old = [{'id': sid, 'releasedAt': '2026-10-23', 'source': {'id': sid}}
               for sid in ['arxiv:one', 'github:two', 'hf:three']]
        result = persistent_review_candidates(old, [], '2026-10-23', '2026-10-23', {'hf:three'})
        self.assertEqual({r['id'] for r in result}, {'arxiv:one', 'github:two'})
        revised = {**old[0], 'name': 'Updated source title'}
        result = persistent_review_candidates(old, [revised], '2026-10-23', '2026-10-23', set())
        self.assertEqual(len(result), 3)
        self.assertEqual(next(r for r in result if r['id'] == 'arxiv:one')['name'], 'Updated source title')


class PublicationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.state = {'trackingStartedAfter': '2026-10-22', 'publications': {}}
        self.manifest = {'latestReportDate': '2026-10-22', 'dataAsOf': '2026-10-29',
                         'metrics': {'todayObservedAt': '2026-10-29T11:00:00Z'}}

    def receipt(self, state, day):
        return record(state, self.manifest, day, {'sourceDate': day,
                      'externalDiscovery': {'failures': {'openreview': 'HTTPError'}}}, 'https://example.org/run')

    def test_catchup_is_bounded_and_stops_at_expected_day(self):
        self.assertEqual(catchup_end('2026-10-23', '2026-10-29', 7), '2026-10-29')
        self.assertEqual(catchup_end('2026-10-28', '2026-10-29', 7), '2026-10-29')
        self.assertEqual(catchup_end('2026-10-23', '2026-10-29', 1), '2026-10-23')
        with self.assertRaises(ValueError):
            catchup_end('2026-10-23', '2026-10-29', 8)

    def test_attention_does_not_hide_outage_or_skip_missing_days(self):
        self.assertEqual(next_date({}, self.manifest, '2026-10-29'), '2026-10-23')
        status = public_status(self.manifest, self.state, '2026-10-29')
        self.assertEqual(status['lagDays'], 7)
        self.assertEqual(status['status'], 'delayed')
        self.assertEqual(status['attentionObservedAt'], '2026-10-29T11:00:00Z')

    def test_out_of_order_manual_run_never_skips_hole(self):
        state = self.receipt(self.state, '2026-10-29')
        self.assertEqual(coverage_through(state), '2026-10-22')
        self.assertEqual(next_date(state, self.manifest, '2026-10-29'), '2026-10-23')
        self.assertEqual(self.state['publications'], {})
        for day in range(23, 29):
            state = self.receipt(state, f'2026-10-{day}')
        self.assertEqual(coverage_through(state), '2026-10-29')
        self.assertEqual(next_date(state, self.manifest, '2026-10-29'), '2026-10-29')
        status = public_status(self.manifest, state, '2026-10-29')
        self.assertEqual(status['lagDays'], 0)
        self.assertEqual(status['sourceFailures'], {'openreview': 'HTTPError'})

    def test_missing_or_wrong_discovery_run_cannot_advance_receipt(self):
        for run in ({}, {'sourceDate': '2026-10-22', 'externalDiscovery': {}}, {'sourceDate': '2026-10-23'}):
            with self.assertRaises(ValueError):
                record(self.state, self.manifest, '2026-10-23', run, '')
        self.assertEqual(coverage_through(self.state), '2026-10-22')

    def test_unknown_discovery_never_falls_back_to_attention_date(self):
        status = public_status({'dataAsOf': '2026-10-29'}, {}, '2026-10-29')
        self.assertEqual(status['status'], 'unknown')
        self.assertIsNone(status['discoveryThrough'])

    def test_browser_recomputes_lag_even_when_static_site_has_not_rebuilt(self):
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const app=fs.readFileSync('web/app.js','utf8');
const code=app.slice(app.indexOf('function updateStatusText('),app.indexOf('function renderRadar('));
class FixedDate extends Date {static now(){return Date.parse('2026-10-30T04:00:00Z')}}
const c={Date:FixedDate};vm.createContext(c);vm.runInContext(code,c);
const text=c.updateStatusText({dataAsOf:'2026-10-30',updateStatus:{discoveryThrough:'2026-10-22',lagDays:0,attentionObservedAt:'2026-10-29T11:00:00Z'}});
assert(text.includes('7 days behind'));assert(text.includes('Attention observed 2026-10-29'));
assert(c.updateStatusText({dataAsOf:'2026-10-30'}).includes('coverage unknown'));
'''
        subprocess.run(['node', '-e', script], cwd=ROOT, check=True)


if __name__ == '__main__':
    unittest.main()

"""Protect provenance, missing values and report snapshots in Model Evals."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from update_model_evals import DATA_PATTERN, apply_updates, update_references


class ModelEvalUpdatesTest(unittest.TestCase):
    def setUp(self):
        self.updates = json.loads((ROOT / 'data/model_eval_updates.json').read_text())
        page = (ROOT / 'web/model-evals/index.html').read_text()
        self.data = json.loads(DATA_PATTERN.search(page)[2])

    def test_repeated_updates_preserve_history_and_do_not_duplicate_evidence(self):
        legacy = [r for r in self.data['observations'] if not r.get('reviewOverlay')]
        once = apply_updates(copy.deepcopy(self.data), self.updates)
        twice = apply_updates(copy.deepcopy(once), self.updates)
        self.assertEqual(once, twice)
        self.assertEqual(legacy, [r for r in once['observations'] if not r.get('reviewOverlay')])
        for org in ('OpenAI', 'Anthropic', 'DeepSeek', 'Moonshot AI'):
            dates = [once['models'][mid]['date'] for mid in once['flagship_models'][org]]
            self.assertEqual(dates, sorted(dates, reverse=True))

    def test_kimi_launch_preserves_metrics_and_raw_scale(self):
        data = apply_updates(self.data, self.updates)
        mid = 'official-reviewed:kimi-k3.1-pro'
        rows = [r for r in data['observations'] if r['model_id'] == mid]
        scores = {r['benchmark_id']: r['display_value'] for r in rows}
        self.assertEqual(len(scores), 48)
        prefix = 'reviewed-20261024:'
        self.assertEqual(scores[prefix + 'zero-avg5'], 29.8)
        self.assertEqual(scores[prefix + 'zero-pass5'], 39.0)
        self.assertEqual(scores[prefix + 'zero-python-pass5'], 63.0)
        self.assertEqual(scores[prefix + 'pdf-python'], 85.7)
        self.assertEqual(scores[prefix + 'pdf-strict'], 34.6)
        self.assertEqual(scores[prefix + 'ale-v11-all'], 43.2)
        self.assertEqual(scores[prefix + 'ale-v11-cli'], 44.2)
        self.assertNotIn('reviewed-202610:program', scores)
        self.assertNotIn('reviewed-202610:os21-partial', scores)
        self.assertIsNone(data['charts'][prefix + 'business-internal']['scale_max'])
        self.assertEqual(data['charts'][prefix + 'hallu-hard']['direction'], 'lower_is_better')
        self.assertEqual(data['flagship_models']['Moonshot AI'][0], mid)
        source_rows = [r for r in data['observations'] if r.get('sourceId') == 'moonshot-k31-pro-20261024']
        self.assertEqual(source_rows, rows)

    def test_newer_elo_snapshot_is_selected_even_when_lower(self):
        data = apply_updates(self.data, self.updates)
        bid = 'reviewed-202610:gdp-aa'
        mid = 'official-reviewed:claude-sonnet-5-5'
        rows = [r for r in data['observations'] if r['model_id'] == mid and r['benchmark_id'] == bid]
        self.assertEqual({r['display_value'] for r in rows}, {1840, 1844})
        chart_row = next(r for r in data['charts'][bid]['rows'] if r['model_id'] == mid)
        self.assertEqual(chart_row['display_value'], 1840)
        self.assertEqual(chart_row['reported_at'], '2026-10-07')

    def test_missing_chart_values_remain_coverage_without_entering_numeric_charts(self):
        data = apply_updates(self.data, self.updates)
        coverage = [r for r in data['observations'] if r.get('coverage_only')]
        self.assertTrue(coverage)
        for row in coverage:
            self.assertIsNone(row['display_value'])
            self.assertFalse(row['scale_verified'])
            self.assertNotIn(row['id'], {r['id'] for r in data['charts'][row['benchmark_id']]['rows']})

    def test_tools_and_subsets_remain_distinct(self):
        data = apply_updates(self.data, self.updates)
        rows = [r for r in data['observations'] if r['model_id'] == 'official-reviewed:deepseek-v4.1-flash-1017']
        scores = {r['benchmark_id']: r['display_value'] for r in rows}
        self.assertEqual(scores['reviewed-202610:hle-no-tools'], 42.6)
        self.assertEqual(scores['reviewed-202610:hle-text'], 44.0)
        self.assertNotIn('reviewed-202610:hle-tools', scores)
        sonnet = [r for r in data['observations'] if r['model_id'] == 'official-reviewed:claude-sonnet-5-5']
        self.assertEqual({r['benchmark_id'] for r in sonnet if r['benchmark_id'].startswith('reviewed-202610:os21-')},
                         {'reviewed-202610:os21-offline', 'reviewed-202610:os21-partial'})

    def test_sources_and_finite_percentage_bounds_are_validated(self):
        for mutation in ({'source_url': 'https://example.com/'}, {'display_value': float('nan')}, {'display_value': 101}):
            updates = copy.deepcopy(self.updates)
            updates['observations'][0].update(mutation)
            with self.assertRaises(ValueError):
                apply_updates(copy.deepcopy(self.data), updates)

    def test_reference_linkage_requires_existing_explicit_ids_and_is_idempotent(self):
        refs = json.loads((ROOT / 'data/model_eval_references.json').read_text())
        library = json.loads((ROOT / 'data/library_index.json').read_text())
        data = apply_updates(self.data, self.updates)
        once = update_references(copy.deepcopy(refs), self.updates, data, library)
        twice = update_references(copy.deepcopy(once), self.updates, data, library)
        self.assertEqual(once, twice)
        self.assertEqual(once['manifest']['reportReferenceCount'], sum(map(len, once['references'].values())))
        updates = copy.deepcopy(self.updates)
        next(iter(updates['benchmarks'].values()))['libraryId'] = 'nonexistent-library-id'
        with self.assertRaises(ValueError):
            update_references(refs, updates, data, library)


if __name__ == '__main__':
    unittest.main()

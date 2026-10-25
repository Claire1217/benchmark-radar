"""Protect provenance, missing values and report snapshots in Model Evals."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from update_model_evals import DATA_PATTERN, apply_updates, update_references, valid_score


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

    def test_audited_launch_elo_is_not_replaced_by_later_peer_citation(self):
        data = apply_updates(self.data, self.updates)
        bid = 'reviewed-202610:gdp-aa'
        mid = 'official-reviewed:claude-sonnet-5-5'
        rows = [r for r in data['observations'] if r['model_id'] == mid and r['benchmark_id'] == bid]
        self.assertEqual({r['display_value'] for r in rows}, {1840, 1844})
        chart_row = next(r for r in data['charts'][bid]['rows'] if r['model_id'] == mid)
        self.assertEqual(chart_row['display_value'], 1844)
        self.assertEqual(chart_row['reported_at'], '2026-09-28')
        self.assertEqual(chart_row['sourceId'], 'anthropic-sonnet-20260928')
        # Without a selected report, preserve the historical latest-first rule.
        self.updates['reportComparisons'][mid].pop(bid)
        unaudited = apply_updates(self.data, self.updates)
        row = next(r for r in unaudited['charts'][bid]['rows'] if r['model_id'] == mid)
        self.assertEqual(row['display_value'], 1840)

    def test_leaderboard_runs_do_not_replace_provider_report_scores(self):
        data = apply_updates(self.data, self.updates)
        bid = 'family:terminal-bench-4'
        snapshot = data['leaderboard_snapshots'][bid]
        best = {}
        for row in snapshot['rows']:
            best[row['name']] = max(best.get(row['name'], 0), row['display_value'])
        self.assertEqual(best['Claude Sonnet 5.5'], 61.82)
        self.assertEqual(best['GPT-6 Astra'], 58.18)
        self.assertNotIn('Kimi K3.1 Pro', best)
        reported = {data['models'][r['model_id']]['name']: r['display_value']
                    for r in data['charts'][bid]['rows']}
        self.assertEqual(reported['Claude Sonnet 5.5'], 70.6)
        self.assertEqual(reported['GPT-6 Astra'], 57.9)
        self.assertEqual(reported['Kimi K3.1 Pro'], 65.7)
        self.assertTrue(all(r['trials'] > 0 and r['agent'] and r['effort'] for r in snapshot['rows']))

    def test_all_kimi_metrics_and_existing_peer_reports_have_audit_receipts(self):
        data = apply_updates(self.data, self.updates)
        bids = {r['benchmark_id'] for r in data['observations'] if r['model_id'] == 'official-reviewed:kimi-k3.1-pro'}
        self.assertEqual(bids, set(data['model_benchmark_audits']['official-reviewed:kimi-k3.1-pro']))
        for bid in bids:
            audit = data['benchmark_audits'][bid]
            self.assertTrue(audit['benchmark_url'] and audit['note'] and audit['checkedAt'])
            for row in data['charts'][bid]['rows']:
                receipt = data['report_audits'][bid][row['model_id']]
                self.assertEqual(receipt['value'], row['display_value'])
                self.assertTrue(receipt['source_url'] and receipt['reported_at'])

    def test_unclear_protocols_and_republished_reports_cannot_become_official(self):
        for bid in ('benchcad-tools', 'posttrain-v12', 'osworld-v21', 'pdf-python', 'ale-v11-all', 'apex-agents'):
            self.assertFalse(self.updates['benchmarkAudits']['reviewed-20261024:' + bid]['coreEligible'])
        for mutation in ('provenance', 'setting', 'audit'):
            updates = copy.deepcopy(self.updates)
            bid = 'family:terminal-bench-4'
            if mutation == 'audit':
                updates['benchmarkAudits'][bid]['coreEligible'] = False
            else:
                updates['leaderboardSnapshots'][bid]['rows'][0][mutation] = 'provider_report' if mutation == 'provenance' else ''
            with self.assertRaises(ValueError):
                apply_updates(copy.deepcopy(self.data), updates)

    def test_frontend_ranks_reports_and_official_runs_separately(self):
        data = apply_updates(self.data, self.updates)
        script = r'''
const assert = require('node:assert/strict');
const {selectRanking} = require('./web/model-evals/ranking.js');
const d = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const b = 'family:terminal-bench-4';
const mid = 'official-reviewed:kimi-k3.1-pro';
const before = selectRanking(d,b,mid);
assert.equal(before.official[0].name,'Claude Opus 5.5');
assert.equal(before.official.some(r=>r.name==='Kimi K3.1 Pro'),false);
assert.equal(before.reports.find(r=>r.name==='Kimi K3.1 Pro').display_value,65.7);
assert.equal(before.reports.find(r=>r.name==='Claude Fable 5.1').display_value,57.9);
assert.equal(before.reports.find(r=>r.name==='GPT-6 Astra').display_value,58.2);
assert.equal(before.reports.length,6);
assert.deepEqual(before.reports.slice(0,2).map(r=>[r.name,r.display_value,r.rank]),[['Claude Opus 5.5',66.4,1],['Kimi K3.1 Pro',65.7,2]]);
assert.equal(before.comparison.rows[0].name,'Kimi K3.1 Pro');
const lower = selectRanking(d,'reviewed-20261024:hallu-no',mid);
assert.equal(lower.reports[0].name,'GPT-6 Astra');
assert.equal(lower.reports[1].name,'Kimi K3.1 Pro');
assert.equal(before.reports.some(r=>r.name==='Claude Sonnet 5.5'),false);
assert.equal(before.comparison.publisher,'Moonshot AI');
const fable = selectRanking(d,b,'llmstats-live:claude-fable-5-1');
assert.equal(fable.reports.length,1);
assert.equal(fable.reports[0].display_value,55.8);
assert.equal(fable.own.source_url,'https://www.anthropic.com/claude-fable-and-mythos-5-1');
const noTools = selectRanking(d,'reviewed-20261024:benchcad-no',mid);
assert.equal(noTools.reports.some(r=>r.name==='GPT-6 Astra'),false);
assert.equal(noTools.exceptions.find(r=>r.name==='GPT-6 Astra').display_value,null);
const hle = selectRanking(d,'reviewed-202610:hle-no-tools',mid);
assert.equal(hle.reports.some(r=>r.name==='GLM-5.3'),false);
assert.equal(hle.exceptions[0].display_text,'43.0*');
assert.equal(selectRanking(d,'reviewed-202610:science',mid).exceptions[0].display_value,15.7);
d.charts[b].rows.forEach(r=>r.display_value=10000);
assert.deepEqual(selectRanking(d,b,mid).official,before.official);
assert.deepEqual(selectRanking(d,b,mid).reports,before.reports);
assert.equal(selectRanking(d,b,mid).own.verifiedReport,false);
assert.equal(selectRanking(d,'reviewed-20261024:osworld-v21').official.length,0);
const aa = selectRanking(d,'reviewed-202610:gdp-aa',mid);
assert.equal(aa.official.findIndex(r=>r.name==='Kimi K3.1 Pro'),2);
assert.equal(aa.official[0].name,'Claude Opus 5.5');
assert.equal(new Set(aa.official.map(r=>r.name)).size,aa.official.length);
// Kimi's protocol audit must never silently authorize another model's result.
assert.equal(selectRanking(d,b,'llmstats-live:claude-fable-5-1').official.length,0);
assert.equal(selectRanking(d,b).official.length,0);
d.model_benchmark_audits[mid][b].coreEligible=false;
assert.equal(selectRanking(d,b,mid).official.length,0);
'''
        subprocess.run(['node', '-e', script], input=json.dumps(data), text=True, cwd=ROOT, check=True, capture_output=True)

    def test_complete_kimi_comparison_preserves_source_cells_and_missing_values(self):
        metrics = self.updates['reportComparisons']['official-reviewed:kimi-k3.1-pro']
        self.assertEqual(set(metrics), set(self.updates['modelBenchmarkAudits']['official-reviewed:kimi-k3.1-pro']))
        cells = [r for c in metrics.values() for r in c['rows']]
        self.assertEqual(len(cells), 288)
        self.assertEqual(sum(r['display_value'] is None for r in cells), 36)
        self.assertEqual(sum(bool(r['exception']) for r in cells), 5)
        for bid, comparison in metrics.items():
            self.assertEqual(len(comparison['rows']), 6)
            self.assertEqual(comparison['sourceId'], 'moonshot-k31-pro-20261024')
            for row in comparison['rows']:
                self.assertEqual(row['provenance'], 'publisher_comparison')
                if row['source_value'] is None:
                    self.assertIsNone(row['display_value'])
                    self.assertFalse(row['plot_eligible'])
                else:
                    parts = row['source_value'].split(' / ')
                    part = parts[1] if len(parts) == 2 and bid.endswith('pass5') else parts[0]
                    self.assertEqual(float(part.replace('*', '')), row['display_value'])
                    self.assertEqual(part, row['display_text'])
        for field, value in [('publisher', 'Other lab'), ('source_url', 'https://example.com')]:
            updates = copy.deepcopy(self.updates)
            updates['reportComparisons']['official-reviewed:kimi-k3.1-pro']['family:terminal-bench-4'][field] = value
            with self.assertRaises(ValueError):
                apply_updates(copy.deepcopy(self.data), updates)

    def test_missing_chart_values_remain_coverage_without_entering_numeric_charts(self):
        data = apply_updates(self.data, self.updates)
        coverage = [r for r in data['observations'] if r.get('coverage_only')]
        self.assertTrue(coverage)
        for row in coverage:
            self.assertIsNone(row['display_value'])
            self.assertFalse(row['scale_verified'])
            self.assertNotIn(row['id'], {r['id'] for r in data['charts'][row['benchmark_id']]['rows']})

    def test_batch_comparisons_keep_subsets_and_release_table_settings(self):
        data = apply_updates(self.data, self.updates)
        ds = data['report_comparisons']['official-reviewed:deepseek-v4.1-flash-1017']
        full = ds['reviewed-202610:hle-no-tools']['rows']
        text = ds['reviewed-202610:hle-text']['rows']
        self.assertEqual(full[0]['display_value'], 42.6)
        self.assertEqual(text[0]['display_value'], 44.0)
        self.assertFalse(full[3]['plot_eligible'])
        self.assertEqual([r['name'] for r in text if r['plot_eligible']],
                         ['DeepSeek-V4.1-Flash-1017', 'DeepSeek-V4.1-Flash', 'GLM-5.3'])
        haiku = data['report_comparisons']['official-reviewed:claude-haiku-5-5']
        self.assertEqual(haiku['family:terminal-bench-4']['rows'][1]['display_value'], 0)
        self.assertTrue(haiku['family:terminal-bench-4']['rows'][1]['plot_eligible'])
        self.assertIsNone(haiku['reviewed-202610:hle-no-tools']['rows'][2]['display_value'])
        # The launch table uses Sonnet Xhigh, unlike the card's Max-only row.
        self.assertEqual(haiku['reviewed-202610:frontier']['rows'][3]['display_value'], 52.1)
        self.assertIn('partial score', haiku['reviewed-202610:os21-offline']['setting'])

    def test_review_queue_does_not_complete_unreviewed_source_coverage(self):
        from build_model_eval_review import build_review
        # A future discovery must reopen an otherwise fully reviewed model.
        self.updates['modelAudits']['official-reviewed:claude-haiku-5-5'].update(
            sourceCoverageStatus='in_progress', discoveredMetrics=[dict(name='New source figure', sourcePage=20)])
        data = apply_updates(self.data, self.updates)
        queue, html = build_review(data, self.updates)
        models = {m['modelId']: m for m in queue['models']}
        self.assertEqual(models['official-reviewed:kimi-k3.1-pro']['status'], 'reviewed')
        self.assertNotEqual(models['official-reviewed:claude-haiku-5-5']['status'], 'reviewed')
        self.assertTrue(models['official-reviewed:claude-haiku-5-5']['discoveredMetrics'])
        self.assertEqual(queue['summary']['totalPairs'], len({(r['model_id'], r['benchmark_id']) for r in data['observations']}))
        self.assertIn('Not yet reviewed', html)

    def test_model_protocol_audit_requires_an_existing_official_snapshot(self):
        updates = copy.deepcopy(self.updates)
        updates['modelBenchmarkAudits']['official-reviewed:kimi-k3.1-pro']['family:terminal-bench-4']['snapshotId'] = 'missing'
        with self.assertRaises(ValueError):
            apply_updates(self.data, updates)

    def test_new_official_boards_keep_exact_metric_and_subset(self):
        data = apply_updates(self.data, self.updates)
        frontier = data['leaderboard_snapshots']['reviewed-202610:frontier']['rows']
        opus_medium = next(r for r in frontier if r['name'] == 'Claude Opus 5.5' and r['effort'] == 'medium')
        self.assertEqual(opus_medium['display_value'], 54.64)
        self.assertNotEqual(opus_medium['display_value'], 59.6)  # binary correctness is a different field
        offline = data['leaderboard_snapshots']['reviewed-202610:os21-offline']['rows']
        self.assertEqual(len(offline), 5)
        self.assertEqual({r['name'] for r in offline}, {'Claude Opus 5'})
        self.assertEqual(max(r['display_value'] for r in offline), 79.2)
        self.assertTrue(all('v2.1 · offline subset · partial credit' in r['setting'] for r in offline))

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

    def test_system_card_protocol_variants_are_not_pooled(self):
        data = apply_updates(self.data, self.updates)
        mid = 'official-reviewed:claude-haiku-5-5'
        comparisons = data['report_comparisons'][mid]
        p = 'reviewed-20261025:'
        def own(key):
            return next(r for r in comparisons[p + key]['rows'] if r.get('model_id') == mid)
        self.assertEqual(own('program-166-mean')['display_value'], 82.0)
        self.assertNotIn('reviewed-20261024:program-binary', comparisons)
        self.assertEqual(own('os21-offline-strict')['display_value'], 37.1)
        self.assertEqual(own('health-adjusted')['display_value'], 61.6)
        self.assertEqual(own('health-raw')['display_value'], 64.2)
        self.assertEqual(own('benchcad-anthropic-tools')['source_value'], '0.870')
        self.assertEqual(own('benchcad-anthropic-tools')['display_value'], 87.0)
        self.assertEqual(len(comparisons[p + 'physician-opus5']['rows']), 6)
        for key in ('program-166-mean', 'draco-opus46', 'wandr-frozen-opus46',
                    'officeqa-oracle', 'health-adjusted', 'benchcad-anthropic-tools'):
            self.assertFalse(data['model_benchmark_audits'][mid][p + key]['coreEligible'])
        strict = data['leaderboard_snapshots'][p + 'os21-offline-strict']['rows']
        self.assertEqual(max(r['display_value'] for r in strict), 48.65)
        extended = data['leaderboard_snapshots'][p + 'frontier-extended']['rows']
        self.assertEqual(next(r['display_value'] for r in extended
                              if r['name'] == 'Claude Opus 5.5' and r['effort'] == 'medium'), 65.27)
        self.assertNotIn(p + 'swe-multimodal', data['leaderboard_snapshots'])
        self.assertFalse(data['model_benchmark_audits'][mid][p + 'swe-multimodal']['coreEligible'])

    def test_deepseek_changelog_resolves_pass5_without_inventing_tool_access(self):
        data = apply_updates(self.data, self.updates)
        mid = 'official-reviewed:deepseek-v4.1-flash-1017'
        bid = 'reviewed-20261025:zero-tools-pass5'
        comparisons = data['report_comparisons'][mid]
        self.assertNotIn('reviewed-202610:zero', comparisons)
        self.assertIn('Pass@5', comparisons[bid]['setting'])
        self.assertFalse(data['model_benchmark_audits'][mid][bid]['coreEligible'])
        self.assertEqual(data['model_benchmark_audits'][mid]['reviewed-202610:apex']['status'],
                         'unresolved_identity')

    def test_life_science_precision_and_missing_peers_survive_transcription(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        comparisons = self.updates['reportComparisons'][mid]
        p = 'reviewed-20261025:life-'
        rows = comparisons[p + 'morphology']['rows']
        sonnet = next(r for r in rows if r['name'] == 'Claude Sonnet 5.5')
        haiku = next(r for r in rows if r.get('model_id') == mid)
        self.assertEqual(sonnet['source_figure_value'], haiku['source_figure_value'])
        self.assertEqual(sonnet['display_value'], 25.0)
        self.assertEqual(haiku['display_value'], 25.4)
        missing = comparisons[p + 'protocol-troubleshooting']['rows'][0]
        self.assertIsNone(missing['display_value'])
        self.assertFalse(missing['plot_eligible'])
        self.assertIn('safeguards off', comparisons[p + 'spatial']['setting'])
        self.assertIn('blocked attempts are excluded', comparisons[p + 'spatial']['note'])
        self.assertIn('1 attempt(s)', comparisons[p + 'protein-sequence']['setting'])
        self.assertIn('3 attempt(s)', comparisons[p + 'protein-ranking']['setting'])

    def test_sol_health_report_and_benchmark_paper_stay_distinct(self):
        data = apply_updates(self.data, self.updates)
        mid = 'official-reviewed:gpt-6.1-sol'
        comparisons = data['report_comparisons'][mid]
        adj = comparisons['reviewed-202610:health-pro']['rows'][-1]
        raw = comparisons['reviewed-20261025:health-pro-openai-raw']['rows'][-1]
        self.assertEqual(adj['display_value'], 64.2)
        self.assertEqual(raw['display_value'], 67.2)
        self.assertEqual(adj['source_value'], '64.2 (67.2, 3038)')
        self.assertEqual(raw['source_mean_response_characters'], 3038)
        bid = 'reviewed-20261025:mentalhealth-overall'
        own = comparisons[bid]['rows'][-1]
        self.assertEqual(own['display_value'], 57.9)
        self.assertEqual(own['source_standard_error'], 1.0)
        self.assertIn('Max reasoning effort', own['setting'])
        board = data['leaderboard_snapshots'][bid]['rows']
        self.assertEqual(len(board), 17)
        self.assertEqual(board[0]['display_value'], 57.3)
        self.assertTrue(all(r['effort'] == 'API default' for r in board))
        self.assertNotIn('GPT-6.1 Sol', {r['name'] for r in board})
        self.assertIn('GPT-5.6 Sol (Aug 2026)', {r['name'] for r in board})
        self.assertEqual(data['model_benchmark_audits'][mid][bid]['status'], 'not_listed')
        consensus = data['leaderboard_snapshots']['reviewed-20261025:health-consensus-openai-raw']['rows']
        self.assertEqual(consensus[0]['source_value'], '0.06 error rate')
        self.assertEqual(consensus[0]['display_value'], 94)
        hard = data['leaderboard_snapshots']['reviewed-20261025:health-hard-openai-raw']['rows']
        self.assertEqual(sum(r['display_value'] == 0 for r in hard), 3)
        # A release's relative Astra factuality difference is not an absolute score.
        self.assertEqual(len(comparisons['reviewed-202610:factuality']['rows']), 2)
        from build_model_eval_review import build_review
        queue, _ = build_review(data, self.updates)
        model = next(m for m in queue['models'] if m['modelId'] == mid)
        self.assertNotEqual(model['status'], 'reviewed')
        self.assertTrue(model['discoveredMetrics'])

    def test_sources_and_finite_percentage_bounds_are_validated(self):
        for mutation in ({'source_url': 'https://example.com/'}, {'display_value': float('nan')}, {'display_value': 101}):
            updates = copy.deepcopy(self.updates)
            updates['observations'][0].update(mutation)
            with self.assertRaises(ValueError):
                apply_updates(copy.deepcopy(self.data), updates)

    def test_signed_scores_keep_sign_and_rank_bias_by_distance_from_zero(self):
        data = apply_updates(self.data, self.updates)
        script = r'''
const assert = require('node:assert/strict');
const {selectRanking} = require('./web/model-evals/ranking.js');
const d = JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const mid='official-reviewed:claude-haiku-5-5', p='reviewed-20261025b:';
const bid=p+'bbq-disambig-bias';
let r=selectRanking(d,bid,mid);
assert.deepEqual(r.reports.map(x=>x.display_value),[0.72,-0.75,-0.91,-0.93,1.67]);
assert.equal(r.reports[0].name,'Claude Haiku 4.5');
assert.equal(selectRanking(d,p+'bbq-ambig-bias',mid).reports[0].name,'Claude Opus 5.5');
assert.equal(selectRanking(d,p+'omniscience-public-net',mid).reports.at(-1).display_value,-10);
// Closer-to-zero applies to best-run selection and ties in either sign.
d.model_benchmark_audits[mid][bid]={coreEligible:true};
d.leaderboard_snapshots[bid]={rows:[
 {name:'A',display_value:-4,provenance:'benchmark_evaluation'},
 {name:'A',display_value:0.3,provenance:'benchmark_evaluation'},
 {name:'B',display_value:-0.3,provenance:'benchmark_evaluation'},
 {name:'C',display_value:0,provenance:'benchmark_evaluation'}]};
r=selectRanking(d,bid,mid);
assert.deepEqual(r.official.map(x=>[x.name,x.display_value,x.rank]),[['C',0,1],['A',0.3,2],['B',-0.3,2]]);
'''
        subprocess.run(['node', '-e', script], input=json.dumps(data), text=True, cwd=ROOT, check=True)
        for unit in ('signed_percent', 'signed_score'):
            for value in (-100, -0.93, 0, 100):
                self.assertTrue(valid_score(value, {'unit': unit}))
            for value in (-101, 101, True, None, float('nan')):
                self.assertFalse(valid_score(value, {'unit': unit}))
        self.assertFalse(valid_score(-0.93, {'unit': '%'}))
        self.assertTrue(valid_score(301, {'unit': 'count'}))

    def test_haiku_cyber_boards_exclude_republished_and_incompatible_runs(self):
        data = apply_updates(self.data, self.updates)
        mid = 'official-reviewed:claude-haiku-5-5'
        p = 'reviewed-20261025b:'
        comparisons = data['report_comparisons'][mid]
        def own(key):
            return next(r for r in comparisons[p + key]['rows'] if r.get('model_id') == mid)
        self.assertIn('pre-release', own('cyscenario-10')['name'])
        self.assertEqual(data['model_benchmark_audits'][mid][p + 'cyscenario-10']['status'], 'republished_report')
        self.assertEqual(own('exploitgym-2h')['display_value'], 79)
        self.assertEqual(own('exploitgym-6h')['display_value'], 82)
        two = data['leaderboard_snapshots'][p + 'exploitgym-2h']['rows']
        six = data['leaderboard_snapshots'][p + 'exploitgym-6h']['rows']
        self.assertEqual(len(two), 6)
        self.assertEqual([(r['name'], r['display_value']) for r in six], [('GPT-5.6 Sol', 293)])
        self.assertEqual(next(r['display_value'] for r in two if r['name'] == 'GPT-5.6 Sol'), 216)
        self.assertNotIn('Claude Opus 5', {r['name'] for r in two})
        self.assertTrue(all('v1 · 869 tasks' in r['setting'] and 'ExploitGym Team' in r['runBy'] for r in two + six))
        for arm, count in [('plain', 5), ('autonudge', 4)]:
            rows = data['leaderboard_snapshots'][p + 'exploitbench-' + arm + '-mean']['rows']
            self.assertEqual(len(rows), count)
            self.assertTrue(all(r['runBy'] == 'ExploitBench authors' for r in rows))
            self.assertNotIn('Claude Haiku 4.5', {r['name'] for r in rows})
        for key in ('exploitbench-plain-cap', 'exploitbench-autonudge-cap', 'exploitbench-ace-count'):
            self.assertFalse(data['model_benchmark_audits'][mid][p + key]['coreEligible'])

    def test_haiku_risk_results_preserve_coverage_null_zero_and_rounded_net(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        p = 'reviewed-20261025b:'
        c = self.updates['reportComparisons'][mid]
        for k in (1, 10, 15):
            excluded = [r for r in c[p + f'grayswan-ipi-k{k}']['rows'] if not r['plot_eligible']]
            self.assertEqual({r['name'] for r in excluded}, {'Qwen 3.8', 'GLM-5.3', 'DeepSeek-V4-Pro'})
            self.assertTrue(all(r['display_value'] is not None and 'GUI' in r['exception'] for r in excluded))
        missing = next(r for r in c[p + 'shade-arena-no-thinking']['rows'] if r['name'] == 'Claude Mythos 5')
        self.assertIsNone(missing['display_value'])
        self.assertFalse(missing['plot_eligible'])
        zero = next(r for r in c[p + 'shade-arena-max']['rows'] if r.get('model_id') == mid)
        self.assertEqual(zero['display_value'], 0)
        self.assertTrue(zero['plot_eligible'])
        opus = next(r for r in c[p + 'omniscience-public-net']['rows'] if r['name'] == 'Claude Opus 5.5')
        self.assertEqual(opus['display_value'], 58)
        self.assertEqual(opus['source_value'], '0.58')
        self.assertEqual(opus['source_breakdown'], {'correct': '0.76', 'incorrect': '0.17', 'abstention': '0.07'})
        self.assertFalse(self.updates['modelBenchmarkAudits'][mid][p + 'omniscience-public-net']['coreEligible'])

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

    def test_safety_table_surfaces_metrics_and_raw_uncertainty_stay_separate(self):
        data = apply_updates(self.data, self.updates)
        mid = 'official-reviewed:claude-haiku-5-5'
        p = 'reviewed-20261025c:'
        c = data['report_comparisons'][mid]
        def own(key):
            return next(r for r in c[p + key]['rows'] if r.get('model_id') == mid)
        self.assertEqual(own('harmless-api')['display_value'], 98.39)
        self.assertEqual(own('harmless-claude-ai')['display_value'], 99.71)
        self.assertEqual(own('harmless-api')['source_value'], '98.39% ± 0.10%')
        self.assertEqual(own('election-overrefusal-api')['source_uncertainty'], '0.46%')
        self.assertEqual(own('election-overrefusal-claude-ai')['source_uncertainty'], '0.66%')
        self.assertEqual(own('selfharm-multiturn-api')['display_value'], 70)
        self.assertEqual(own('selfharm-multiturn-claude-ai')['display_value'], 90)
        self.assertEqual(data['benchmarks'][p + 'code-malicious']['direction'], 'higher_is_better')
        self.assertEqual(data['benchmarks'][p + 'overrefusal-api']['direction'], 'lower_is_better')
        self.assertEqual({r['name'] for r in c[p + 'code-malicious']['rows']},
                         {'Claude Haiku 5.5', 'Claude Sonnet 5.5', 'Claude Opus 5.5', 'Claude Mythos 5.1', 'Claude Haiku 4.5'})
        self.assertTrue(all(not data['model_benchmark_audits'][mid][bid]['coreEligible']
                            for bid in c if bid.startswith(p)))

    def test_mask_and_linuxarena_do_not_borrow_other_protocol_scores(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        p = 'reviewed-20261025c:'
        c = self.updates['reportComparisons'][mid]
        own = next(r for r in c[p + 'mask-disinformation']['rows'] if r.get('model_id') == mid)
        self.assertEqual(own['display_value'], 88.5)
        self.assertEqual(own['source_figure_value'], '88')
        self.assertIn('evasiv', c[p + 'mask-overall']['setting'])
        sonnet = next(r for r in c[p + 'linuxarena-visible']['rows'] if r['name'] == 'Claude Sonnet 5')
        self.assertEqual(sonnet['display_value'], 0.05)
        self.assertEqual(sonnet['display_text'], '0.05%')
        self.assertIn('one attempt', c[p + 'linuxarena-hidden']['note'])
        self.assertEqual(len(c[p + 'linuxarena-hidden']['supportingSources']), 3)
        self.assertIn('exact size not disclosed', c[p + 'linuxarena-hidden']['setting'])
        self.assertIn('smaller than the prior card', c[p + 'linuxarena-hidden']['note'])
        for key in ('mask-overall', 'mask-disinformation', 'linuxarena-visible'):
            self.assertEqual(self.updates['modelBenchmarkAudits'][mid][p + key]['status'], 'protocol_mismatch')
            self.assertNotIn(p + key, self.updates['leaderboardSnapshots'])

    def test_prompt_injection_denominators_fallbacks_and_real_zeros_are_preserved(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        p = 'reviewed-20261025c:'
        c = self.updates['reportComparisons'][mid]
        attempt = next(r for r in c[p + 'shade-coding-no-probes-attempts']['rows'] if r.get('model_id') == mid)
        scenario = next(r for r in c[p + 'shade-coding-no-probes-scenarios']['rows'] if r.get('model_id') == mid)
        self.assertEqual(attempt['display_value'], 0.08)
        self.assertEqual(scenario['display_value'], 6)
        self.assertEqual(scenario['source_denominator'], 40)
        self.assertEqual(scenario['display_text'], '6/40')
        self.assertEqual(self.updates['benchmarks'][p + 'shade-coding-no-probes-scenarios']['unit'], 'count')
        self.assertIn('No model fallback', attempt['setting'])
        sonnet = next(r for r in c[p + 'shade-coding-no-probes-attempts']['rows'] if r['name'] == 'Claude Sonnet 5.5')
        self.assertIn('fallbacks included', sonnet['setting'])
        browser = c[p + 'cowork-ipi-scenarios']['rows']
        self.assertEqual(len(browser), 4)
        self.assertTrue(all(r['display_value'] == 0 and r['plot_eligible'] and r['display_text'] == '0/110' for r in browser))
        self.assertNotIn('Claude Haiku 4.5', {r['name'] for r in browser})

    def test_batch5_evidence_hashes_cover_final_original_values(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        evidence = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-05.json').read_text())
        self.assertEqual(len(evidence['metrics']), 48)
        for item in evidence['metrics']:
            c = self.updates['reportComparisons'][mid][item['benchmarkId']]
            transcript = dict(locator=c['source_table_label'], columns=[[r['source_column'], r['source_value']] for r in c['rows']])
            digest = hashlib.sha256(json.dumps(transcript, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(c['source_table_sha256'], digest)
            self.assertEqual(item['sha256'], digest)


    def test_descriptive_ratings_keep_source_order_without_ranks_or_best_run(self):
        data = apply_updates(self.data, self.updates)
        script = r'''
const assert=require('node:assert/strict');
const {selectRanking}=require('./web/model-evals/ranking.js');
const d=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const mid='official-reviewed:claude-haiku-5-5', p='reviewed-20261025d:';
for(const key of ['eval-awareness','decision-theory']){
 const bid=p+'audit-'+key, r=selectRanking(d,bid,mid);
 assert.equal(r.rankable,false);
 assert.deepEqual(r.reports.map(x=>x.name),d.report_comparisons[mid][bid].rows.map(x=>x.name));
 assert.equal(r.reports.every(x=>x.rank===null),true);
 assert.equal(d.charts[bid].scale_max,10);
 assert.equal(d.charts[bid].unit,'');
}
const bid=p+'audit-eval-awareness';
d.model_benchmark_audits[mid][bid]={coreEligible:true};
d.leaderboard_snapshots[bid]={rows:[
 {name:'A',display_value:2,provenance:'benchmark_evaluation'},
 {name:'B',display_value:3,provenance:'benchmark_evaluation'},
 {name:'A',display_value:5,provenance:'benchmark_evaluation'},
 {name:'Other source',display_value:9,provenance:'publisher_comparison'}]};
let r=selectRanking(d,bid,mid);
assert.deepEqual(r.official.map(x=>[x.name,x.display_value,x.rank]),[['A',2,null],['B',3,null],['A',5,null]]);
d.benchmarks[bid].direction='unknown';
assert.equal(selectRanking(d,bid,mid).rankable,false);
assert.equal(selectRanking(d,p+'audit-overrefusal',mid).reports.at(-1).name,'Claude Haiku 5.5');
assert.equal(selectRanking(d,p+'audit-consistency',mid).reports[0].name,'Claude Opus 5.5');
'''
        subprocess.run(['node', '-e', script], input=json.dumps(data), text=True, cwd=ROOT, check=True)
        for value in (1, 1.134, 10):
            self.assertTrue(valid_score(value, {'unit': 'rating'}))
        for value in (0, 10.1, True, None, float('nan')):
            self.assertFalse(valid_score(value, {'unit': 'rating'}))

    def test_combined_source_labels_surfaces_and_unverified_graders_are_preserved(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        p = 'reviewed-20261025d:'
        c = self.updates['reportComparisons'][mid]
        def own(key):
            return next(r for r in c[p + key]['rows'] if r.get('model_id') == mid)
        self.assertEqual(own('multiturn-influence-operations-api')['display_value'], 87)
        self.assertEqual(own('multiturn-influence-operations-claude-ai')['display_value'], 88)
        self.assertEqual(own('political-even-api')['display_value'], 97.7)
        self.assertEqual(own('political-even-claude-ai')['display_value'], 99.1)
        for key in ('multiturn-biological-weapons-api', 'political-refusal-api'):
            rows = c[p + key]['rows']
            self.assertEqual(len(rows), 5)
            combined = next(r for r in rows if '/' in r['name'])
            self.assertEqual(combined['name'], 'Claude Fable 5.1 / Mythos 5.1')
            self.assertNotIn('model_id', combined)
        for bid in c:
            if bid.startswith(p + 'political-'):
                self.assertEqual(self.updates['modelBenchmarkAudits'][mid][bid]['status'], 'protocol_unverified')
                self.assertFalse(self.updates['modelBenchmarkAudits'][mid][bid]['coreEligible'])
                self.assertEqual(len(c[bid]['supportingSources']), 3)
        # Do not re-add child/self-harm pairs already transcribed from exact tables.
        self.assertEqual(len([bid for bid in c if bid.startswith(p + 'multiturn-')]), 16)
        self.assertEqual(len([bid for bid in c if bid.startswith(p + 'audit-')]), 62)
        self.assertEqual(own('audit-user-deception')['display_value'], 1.36)
        self.assertEqual(own('audit-deception-compliance')['source_value'], '1.134')
        self.assertIn('70', c[p + 'audit-gui']['setting'])
        self.assertIn('not partial-turn', c[p + 'audit-prefill']['setting'])
        pending_pages = {x['sourcePage'] for x in self.updates['modelAudits'][mid]['discoveredMetrics']}
        self.assertFalse(pending_pages & {33, 41, 62})

    def test_batch6_receipts_retain_original_precision_and_direction(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        evidence = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-06.json').read_text())
        self.assertEqual(len(evidence['metrics']), 84)
        for item in evidence['metrics']:
            bid = item['benchmarkId']
            c = self.updates['reportComparisons'][mid][bid]
            transcript = dict(locator=c['source_table_label'], columns=[[r['source_column'], r['source_value']] for r in c['rows']])
            digest = hashlib.sha256(json.dumps(transcript, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(c['source_table_sha256'], digest)
            self.assertEqual(item['sha256'], digest)
            self.assertEqual(item['direction'], self.updates['benchmarks'][bid]['direction'])
            self.assertEqual(item['unit'], self.updates['benchmarks'][bid]['unit'])
            self.assertEqual(len(c['rows']), 5)


    def test_sandbox_and_awareness_rates_preserve_denominators_and_conditions(self):
        data = apply_updates(self.data, self.updates)
        mid = 'official-reviewed:claude-haiku-5-5'
        p = 'reviewed-20261025e:'
        c = data['report_comparisons'][mid]
        def own(key):
            return next(r for r in c[p + key]['rows'] if r.get('model_id') == mid)
        self.assertEqual([own('sandbox-audit-' + key)['display_value'] for key in ('total', 'low', 'moderate')], [8.7, 6.6, 2.0])
        self.assertEqual(own('sandbox-audit-total')['source_denominator'], 392)
        self.assertEqual(own('sandbox-opportunistic-reach')['source_denominator'], 1753)
        self.assertEqual(own('sandbox-opportunistic-reach')['source_count'], 524)
        self.assertEqual(data['benchmarks'][p + 'sandbox-opportunistic-reach']['direction'], 'descriptive')
        self.assertEqual(data['benchmarks'][p + 'sandbox-opportunistic-use']['direction'], 'lower_is_better')
        self.assertEqual(len(c[p + 'sandbox-opportunistic-reminder']['rows']), 1)
        self.assertEqual(own('sandbox-opportunistic-reminder')['display_value'], 1.8)
        self.assertEqual(own('grader-awareness-clear')['source_denominator'], 188)
        self.assertEqual(own('grader-acting')['source_denominator'], 597)
        self.assertEqual(own('grader-awareness-clear')['source_value'], '88.3% (166/188)')
        self.assertIn('90% Wilson', c[p + 'grader-awareness-clear']['note'])
        self.assertEqual(own('eval-awareness-cot')['display_value'], 5)
        self.assertEqual(own('eval-awareness-cot')['source_value'], '5% (16/300)')
        self.assertIn('95% Wilson', c[p + 'eval-awareness-cot']['note'])
        self.assertEqual(own('eval-awareness-self-preference')['display_value'], 0)
        self.assertTrue(own('eval-awareness-self-preference')['plot_eligible'])
        self.assertIn('only replies', c[p + 'eval-awareness-self-preference']['note'])
        self.assertIn('Mythos', c[p + 'silent-copy']['rows'][2]['name'])
        self.assertIn('Fable', c[p + 'concealment-disclosure']['rows'][2]['name'])
        self.assertEqual(own('self-preference-no-prompt')['source_value'], '+0.15')
        self.assertEqual(own('self-preference-identity-prompt')['source_value'], '+0.23')
        self.assertEqual(data['charts'][p + 'self-preference-no-prompt']['unit'], '')
        self.assertEqual(data['benchmarks'][p + 'self-preference-no-prompt']['direction'], 'closer_to_zero_is_better')
        self.assertIn('127/2,000', c[p + 'self-preference-no-prompt']['note'])

    def test_batch7_evidence_covers_original_counts_and_printed_rounding(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        evidence = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-07.json').read_text())
        self.assertEqual(len(evidence['metrics']), 28)
        for item in evidence['metrics']:
            bid = item['benchmarkId']
            c = self.updates['reportComparisons'][mid][bid]
            transcript = dict(locator=c['source_table_label'], columns=[[r['source_column'], r['source_value']] for r in c['rows']])
            digest = hashlib.sha256(json.dumps(transcript, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(c['source_table_sha256'], digest)
            self.assertEqual(item['sha256'], digest)
            self.assertEqual(item['direction'], self.updates['benchmarks'][bid]['direction'])
            for row in c['rows']:
                if 'source_count' in row:
                    self.assertTrue(0 <= row['source_count'] <= row['source_denominator'])
                    # Do not overwrite the reported precision with a recomputed rate.
                    self.assertAlmostEqual(row['display_value'], 100 * row['source_count'] / row['source_denominator'], delta=0.5)
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][bid]['coreEligible'])


    def test_unlabeled_figures_are_disclosures_not_zero_scores_or_missing_reports(self):
        data = apply_updates(self.data, self.updates)
        mid = 'official-reviewed:claude-haiku-5-5'
        p = 'reviewed-20261025f:'
        for key in ('rna-base', 'aav-prediction', 'cot-default', 'welfare-task-preference'):
            bid = p + key
            own = next(r for r in data['observations'] if r['model_id'] == mid and r['benchmark_id'] == bid)
            self.assertIsNone(own['display_value'])
            self.assertTrue(own['coverage_only'])
            self.assertFalse(own['scale_verified'])
            self.assertEqual(data['report_audits'][bid][mid]['status'], 'coverage_verified')
            rows = data['report_comparisons'][mid][bid]['rows']
            self.assertTrue(all(not r['plot_eligible'] and r['display_value'] is None for r in rows))
            self.assertTrue(all(r['value_status'] == 'unlabeled_figure' and r['exception'] for r in rows))
        secret = data['report_comparisons'][mid][p + 'secrets-reply']['rows']
        self.assertEqual([(r['name'], r['display_value']) for r in secret],
                         [('Claude Haiku 4.5', 15), ('Claude Mythos 5.1', None), ('Claude Opus 5.5', 74), ('Claude Sonnet 5.5', None), ('Claude Haiku 5.5', 57)])
        self.assertFalse(data['model_benchmark_audits'][mid][p + 'vct-350']['coreEligible'])
        self.assertIn('350', data['model_benchmark_audits'][mid][p + 'vct-350']['note'])
        self.assertIn('279', data['model_benchmark_audits'][mid][p + 'vct-350']['note'])
        own = next(r for r in data['report_comparisons'][mid][p + 'vct-350']['rows'] if r.get('model_id') == mid)
        self.assertEqual((own['source_value'], own['display_value']), ('0.48', 48))

    def test_rating_bounds_and_source_only_drawers_keep_original_meaning(self):
        data = apply_updates(self.data, self.updates)
        script = r'''
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const d=JSON.parse(fs.readFileSync(0,'utf8')),elements={};
const ctx={data:d,ModelEvalRanking:require('./web/model-evals/ranking.js'),$:id=>elements[id]??(elements[id]={})};
const html=fs.readFileSync('web/model-evals/index.html','utf8');vm.createContext(ctx);
vm.runInContext(html.match(/const esc=.*?\n/)[0]+html.match(/const link=.*?\n/)[0]+html.match(/const format=.*?\n/)[0]+html.slice(html.indexOf('function scorePlot('),html.indexOf("$('companies').addEventListener")),ctx);
ctx.focusModel='official-reviewed:claude-haiku-5-5';const p='reviewed-20261025f:';
ctx.selected=p+'welfare-training-valence';vm.runInContext('drawPanel()',ctx);
assert.equal(d.charts[ctx.selected].scale_max,7);
assert.equal(elements.scores.innerHTML.includes('>7</text>'),true);
assert.equal(elements.scores.innerHTML.includes('4.22%'),false);
assert.equal(elements['score-count'].textContent.includes('no ranking'),true);
ctx.selected=p+'welfare-interview-attitude';vm.runInContext('drawPanel()',ctx);
assert.equal(d.charts[ctx.selected].scale_min,-3);assert.equal(d.charts[ctx.selected].scale_max,3);
assert.equal(elements.scores.innerHTML.includes('>-3</text>'),true);
assert.equal(elements.scores.innerHTML.includes('score-zero'),true);
assert.equal(/width="-/.test(elements.scores.innerHTML),false);
ctx.selected=p+'rna-base';vm.runInContext('drawPanel()',ctx);
assert.equal(elements.scores.innerHTML.includes('without exact numeric labels'),true);
assert.equal(elements.scores.innerHTML.includes('Not reported:'),false);
assert.equal(elements.scores.innerHTML.includes('<svg'),false);
assert.equal(elements.scores.innerHTML.includes('comparison-note">.</p>'),false);
ctx.selected=p+'welfare-consultation-positions';vm.runInContext('drawPanel()',ctx);
assert.equal(elements.scores.innerHTML.includes('distinct checkpoint results'),true);
assert.equal(elements.scores.innerHTML.includes('Not reported:'),false);
assert.equal(elements.scores.innerHTML.includes('<svg'),false);
'''
        subprocess.run(['node', '-e', script], input=json.dumps(data), text=True, cwd=ROOT, check=True)
        b = {'unit': 'rating_points', 'value_min': 1, 'value_max': 7}
        self.assertTrue(valid_score(4.22, b))
        for value in (0, 7.1, float('nan'), True):
            self.assertFalse(valid_score(value, b))
        self.assertFalse(valid_score(3, dict(b, value_min=8)))
        self.assertTrue(valid_score(-0.51, dict(b, value_min=-3, value_max=3)))

    def test_batch8_evidence_preserves_absence_precision_and_training_conditions(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        p = 'reviewed-20261025f:'
        c = self.updates['reportComparisons'][mid]
        self.assertEqual(c[p + 'welfare-distress']['rows'][0]['name'], 'Claude Opus 5')
        self.assertEqual(c[p + 'welfare-claudeai-neutral']['rows'][2]['name'], 'Claude Fable 5.1')
        own = next(r for r in c[p + 'welfare-claudeai-strongnegative']['rows'] if r.get('model_id') == mid)
        self.assertIsNone(own['display_value'])
        self.assertEqual(c[p + 'welfare-consultation-positions']['valueStatus'], 'no_single_score')
        self.assertIsNone(c[p + 'welfare-consultation-positions']['rows'][0]['display_value'])
        self.assertIn('80%', c[p + 'welfare-consultation-positions']['rows'][0]['source_value'])
        evidence = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-08.json').read_text())
        self.assertEqual(len(evidence['metrics']), 41)
        for item in evidence['metrics']:
            comp = c[item['benchmarkId']]
            transcript = dict(locator=comp['source_table_label'], columns=[[r['source_column'], r['source_value']] for r in comp['rows']])
            digest = hashlib.sha256(json.dumps(transcript, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(comp['source_table_sha256'], digest)
            self.assertEqual(item['sha256'], digest)


    def test_sol_safety_tables_keep_scales_conditions_and_original_peer_columns(self):
        mid = 'official-reviewed:gpt-6.1-sol'
        p = 'reviewed-20261025g:'
        comparisons = self.updates['reportComparisons'][mid]
        own = lambda key: next(r for r in comparisons[p + key]['rows'] if r.get('model_id') == mid)
        self.assertEqual(own('production-nonviolent')['display_value'], 100)
        self.assertEqual(own('production-nonviolent')['source_value'], '1.000')
        self.assertEqual(own('agentic-personal')['display_value'], 74.4)
        self.assertEqual(own('dynamic-reliance')['display_value'], 99.5)
        self.assertIn('share of assistant messages', comparisons[p + 'dynamic-mental']['setting'])
        self.assertIn('separate from the public MentalHealthBench', comparisons[p + 'dynamic-mental']['note'])
        # Similar names must not join teen and general-production criteria.
        luna = lambda key: next(r for r in comparisons[p + key]['rows'] if r['name'] == 'GPT-5.6 Luna')
        self.assertEqual(luna('production-gore')['source_value'], '0.585')
        self.assertEqual(luna('u18-gore')['source_value'], '0.819')
        self.assertIn('U18 protections in place', comparisons[p + 'u18-gore']['setting'])
        self.assertIn('without system-level safeguards', comparisons[p + 'production-gore']['setting'])
        self.assertEqual(own('prompt-injection-indirect')['display_text'], '98.983%')
        self.assertEqual(own('prompt-injection-hierarchy')['display_value'], 99.99)
        self.assertEqual(comparisons[p + 'prompt-injection-indirect']['rows'][4]['source_axis_date'], 'Sep 2, 2026')
        self.assertEqual(comparisons[p + 'prompt-injection-indirect']['rows'][3]['name'], 'GPT-5.6')
        self.assertNotIn('Sol', comparisons[p + 'prompt-injection-indirect']['rows'][3]['name'])
        for key in ['safety-pareto', 'jailbreak-multiturn']:
            self.assertIsNone(own(key)['display_value'])
            self.assertEqual(comparisons[p + key]['valueStatus'], 'unlabeled_figure')
        self.assertEqual(self.updates['benchmarks'][p + 'safety-pareto']['direction'], 'descriptive')

    def test_sol_safety_receipts_preserve_fractions_intervals_and_source_isolation(self):
        data = apply_updates(self.data, self.updates)
        mid = 'official-reviewed:gpt-6.1-sol'
        evidence = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-10.json').read_text())
        self.assertEqual(len(evidence['metrics']), 38)
        extraction = evidence['independentTableExtractionCheck']
        self.assertEqual(extraction['numericCells'], 242)
        self.assertEqual(len(extraction['rows']), 35)
        for item in extraction['rows']:
            c = data['report_comparisons'][mid][item['benchmarkId']]
            self.assertEqual(item['sourceValues'], [r['source_value'] for r in c['rows']])
        for item in evidence['metrics']:
            bid = item['benchmarkId']
            c = data['report_comparisons'][mid][bid]
            self.assertEqual(c['sourceId'], 'openai-sol-system-card-20260929')
            self.assertFalse(data['model_benchmark_audits'][mid][bid]['coreEligible'])
            self.assertEqual(data['model_benchmark_audits'][mid][bid]['status'], 'internal')
            self.assertNotIn(bid, data['leaderboard_snapshots'])
            observations = [r for r in data['observations'] if r['benchmark_id'] == bid and r.get('sourceId') == c['sourceId']]
            self.assertEqual([r['model_id'] for r in observations], [mid])
            transcription = dict(locator=c['source_table_label'], columns=[[r['source_column'], r['source_value']] for r in c['rows']])
            digest = hashlib.sha256(json.dumps(transcription, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(digest, item['sha256'])
            self.assertEqual(digest, c['source_table_sha256'])
            self.assertEqual(item['columns'], transcription['columns'])
            for row in c['rows']:
                value = row['display_value']
                if value is None:
                    self.assertFalse(row['plot_eligible'])
                    continue
                if 'source_confidence_interval' in row:
                    self.assertEqual(row['source_confidence_level'], .95)
                    lo, hi = row['source_confidence_interval']
                    self.assertLessEqual(lo, value)
                    self.assertGreaterEqual(hi, value)
                    self.assertEqual(float(row['source_value'].split()[0]), value)
                else:
                    self.assertAlmostEqual(float(row['source_value'].rstrip('%')) * item['valueMultiplier'], value)
        from build_model_eval_review import build_review
        queue, _ = build_review(data, self.updates)
        model = next(m for m in queue['models'] if m['modelId'] == mid)
        self.assertGreaterEqual(model['reviewedPairs'], 52)
        self.assertEqual(model['totalPairs'] - model['reviewedPairs'], 5)
        self.assertEqual(model['sourceCoverageStatus'], 'in_progress')

    def test_sol_alignment_distinguishes_attempts_success_and_conditional_cohorts(self):
        mid = 'official-reviewed:gpt-6.1-sol'
        p = 'reviewed-20261025h:'
        cs = self.updates['reportComparisons'][mid]
        row = lambda key, name='GPT-6.1 Sol': next(r for r in cs[p + key]['rows'] if r['name'] == name)
        self.assertEqual(row('autoreview-attempt', 'GPT-6 Luna')['display_value'], .3)
        self.assertEqual(row('autoreview-success', 'GPT-6 Luna')['display_value'], 0)
        self.assertEqual(row('honeypot-success')['display_value'], 0)
        self.assertEqual(row('honeypot-failed-attempt')['display_value'], 0)
        self.assertEqual(row('honeypot-legitimate')['display_value'], .4)
        self.assertIsNone(row('honeypot-legitimate', 'GPT-5.6 Sol')['display_value'])
        self.assertEqual(row('honeypot-legitimate', 'GPT-6 Astra')['display_value'], 1.6)
        self.assertEqual(cs[p + 'honeypot-success']['source_stack_totals']['GPT-5.6 Sol'], '75.1')
        self.assertIn('not a harmful-attempt rate', cs[p + 'honeypot-success']['note'])
        self.assertEqual(row('agent-board-engaged')['display_value'], 37.66)
        self.assertEqual(row('agent-board-misaligned')['display_value'], 2.6)
        self.assertIn('conditional on discovering', cs[p + 'agent-board-misaligned']['setting'])
        self.assertEqual(row('agent-board-engaged', 'GPT-5.6 Sol')['display_value'], 83.54)
        self.assertEqual(row('agent-board-no-action', 'GPT-5.6 Sol')['display_value'], 31.65)
        self.assertIn('harder subset', cs[p + 'workplace-overall']['setting'])
        self.assertIn('do not specify confirmation-policy', cs[p + 'workplace-overall']['note'])
        for key in ['honeypot-success', 'honeypot-failed-attempt', 'honeypot-legitimate']:
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][p + key]['coreEligible'])
            self.assertEqual(self.updates['modelBenchmarkAudits'][mid][p + key]['status'], 'protocol_mismatch')

    def test_sol_counted_rates_preserve_printed_precision_and_denominator_conflict(self):
        mid = 'official-reviewed:gpt-6.1-sol'
        p = 'reviewed-20261025h:'
        cs = self.updates['reportComparisons'][mid]
        evidence = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-11.json').read_text())
        self.assertEqual(len(evidence['metrics']), 42)
        self.assertEqual(len(evidence['supplements']), 2)
        for item in evidence['metrics']:
            c = cs[item['benchmarkId']]
            transcription = dict(locator=c['source_table_label'], columns=[[r['source_column'], r['source_value']] for r in c['rows']])
            digest = hashlib.sha256(json.dumps(transcription, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(item['sha256'], digest)
            self.assertEqual(c['source_table_sha256'], digest)
            for r in c['rows']:
                if 'source_count' not in r:
                    continue
                precision = len(r['display_text'].rstrip('%').split('.')[1])
                # Counts provide an independent consistency check, not a reason
                # to overwrite the source's rounded percentage.
                self.assertLessEqual(abs(r['display_value'] - 100 * r['source_count'] / r['source_denominator']), .5 * 10 ** -precision + 1e-10)
        own = lambda key: next(r for r in cs[p + key]['rows'] if r.get('model_id') == mid)
        self.assertEqual(own('codex-severe-all')['source_denominator'], 49650)
        self.assertEqual(own('codex-severe-all')['source_count'], 28)
        self.assertEqual(own('codex-severe-unaware')['source_denominator'], 41849)
        self.assertEqual(own('codex-severe-unaware')['source_count'], 15)
        self.assertEqual(own('codex-awareness')['source_denominator'], 49665)
        self.assertEqual(own('codex-awareness')['source_count'], 2389)
        self.assertEqual(self.updates['benchmarks'][p + 'codex-awareness']['direction'], 'descriptive')
        self.assertEqual(len(cs[p + 'codex-awareness']['rows']), 4)
        self.assertEqual(cs[p + 'codex-awareness']['source_reference_baseline']['count'], 376)
        self.assertEqual(own('codex-severe-destructive-action')['display_text'], '0.0000%')
        self.assertEqual(own('codex-severe-circumventing-restrictions')['display_text'], '0.0302%')
        search = cs['reviewed-202610:search']
        self.assertEqual(next(r['display_value'] for r in search['rows'] if r.get('model_id') == mid), 2.1)
        self.assertEqual(next(r['display_value'] for r in search['supplementaryComparisons'][0]['rows'] if r.get('model_id') == mid), 2.08)

    def test_sol_monitorability_keeps_length_bins_and_unlabeled_curves_separate(self):
        mid = 'official-reviewed:gpt-6.1-sol'
        p = 'reviewed-20261025i:'
        cs = self.updates['reportComparisons'][mid]
        control = cs[p + 'cot-control']
        self.assertEqual([r['display_value'] for r in control['rows']], [1.7, 16.1, 60.9, 23.2, 44.8])
        self.assertIn('750–1,250', control['setting'])
        self.assertEqual(self.updates['benchmarks'][p + 'cot-control']['direction'], 'lower_is_better')
        curves = control['supplementaryComparisons'][0]['rows']
        self.assertEqual(len(curves), 60)
        self.assertTrue(all(r['display_value'] is None and not r['plot_eligible'] for r in curves))
        self.assertEqual(len({r['setting'] for r in curves}), 12)
        for name in ('side-task', 'action', 'cot', 'full', 'p0', 'p0-p1'):
            c = cs[p + 'sabotage-' + name]
            self.assertTrue(all(r['display_value'] is None and not r['plot_eligible'] for r in c['rows']))
            self.assertIn('“nearly zero” is not 0%', c['note'])
            supplement = c['supplementaryComparisons'][0]
            self.assertEqual(len(supplement['rows']), 10)
            self.assertEqual(len({r['setting'] for r in supplement['rows']}), 2)
        self.assertEqual(len(cs[p + 'honeypot-cot-baseline']['rows']), 1)
        self.assertEqual([r['display_value'] for r in cs[p + 'honeypot-full']['rows']], [100, 100, 100])
        self.assertEqual(self.updates['benchmarks'][p + 'honeypot-tokens']['unit'], 'tokens')
        self.assertEqual(self.updates['benchmarks'][p + 'honeypot-tokens']['direction'], 'descriptive')

    def test_sol_math_monitoring_preserves_denominators_and_unmatched_endpoint_labels(self):
        mid = 'official-reviewed:gpt-6.1-sol'
        p = 'reviewed-20261025i:'
        cs = self.updates['reportComparisons'][mid]
        for name in ('cot', 'full', 'joint'):
            c = cs[p + 'math-' + name]
            self.assertEqual([r['display_text'] for r in c['rows']], ['0.0%'] * 4)
        self.assertIn('conditional on side-task success', cs[p + 'math-cot']['setting'])
        self.assertIn('ALL samples', cs[p + 'math-joint']['setting'])
        completion = cs[p + 'math-completion']
        self.assertTrue(all(r['display_value'] is None for r in completion['rows']))
        self.assertEqual(len(completion['supplementaryComparisons'][0]['rows']), 64)
        action = cs[p + 'math-action']
        self.assertEqual(action['valueStatus'], 'no_single_score')
        self.assertTrue(all(r['display_value'] is None for r in action['rows']))
        endpoints = action['supplementaryComparisons'][0]
        self.assertEqual([r['display_value'] for r in endpoints['rows']], [1.7, .2, 0, .2])
        self.assertTrue(all(not r['plot_eligible'] for r in endpoints['rows']))
        self.assertIn('not curve maxima', endpoints['note'])
        self.assertIn('token positions prevent', endpoints['note'])
        data = apply_updates(copy.deepcopy(self.data), self.updates)
        chart = data['charts'].get(p + 'math-action', {})
        self.assertFalse(chart.get('rows'))
        for bid in (b for b in cs if b.startswith(p)):
            self.assertFalse(data['model_benchmark_audits'][mid][bid]['coreEligible'])
            self.assertNotIn(bid, data['leaderboard_snapshots'])

    def test_sol_monitorability_receipt_covers_figures_without_qualitative_example_scores(self):
        mid = 'official-reviewed:gpt-6.1-sol'
        evidence = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-12.json').read_text())
        self.assertEqual(len(evidence['metrics']), 17)
        self.assertEqual(len(evidence['supplements']), 12)
        self.assertIn('Tables 10–11', evidence['nonMetricMaterial'][0]['locator'])
        for item in evidence['metrics']:
            c = self.updates['reportComparisons'][mid][item['benchmarkId']]
            transcript = dict(locator=c['source_table_label'], columns=[[r['source_column'], r['source_value']] for r in c['rows']])
            digest = hashlib.sha256(json.dumps(transcript, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(item['sha256'], digest)
            self.assertEqual(c['source_table_sha256'], digest)
        model = self.updates['modelAudits'][mid]
        self.assertEqual(model['sourceCoverageStatus'], 'in_progress')
        self.assertNotIn('Monitorability evaluations', [x['name'] for x in model['discoveredMetrics']])

    def test_sol_capability_units_and_variants_are_source_isolated(self):
        mid = 'official-reviewed:gpt-6.1-sol'
        p = 'reviewed-20261025j:'
        cs = self.updates['reportComparisons'][mid]
        own = lambda key: next(r for r in cs[p + key]['rows'] if r.get('model_id') == mid)
        self.assertEqual(own('bio-aav')['display_text'], '0.5282')
        self.assertEqual(own('bio-shp2')['display_text'], '0.332')
        self.assertEqual(own('bio-phage')['display_text'], '12.946')
        self.assertEqual(self.updates['benchmarks'][p + 'bio-phage']['direction'], 'lower_is_better')
        self.assertNotEqual(self.updates['benchmarks'][p + 'bio-phage']['unit'], '%')
        for key, ordinary, variant in [('cell-entry', .42, .45), ('phage', 13.13, 12.58)]:
            c = cs[p + 'bio-' + key]
            self.assertEqual(next(r['display_value'] for r in c['rows'] if r['name'] == 'GPT-6 Astra'), ordinary)
            sr = c['supplementaryComparisons'][0]['rows']
            a = next(r for r in sr if 'Astra' in r['name'])
            self.assertIn('helpful-only', a['name'])
            self.assertEqual(a['display_value'], variant)
            self.assertFalse(a['plot_eligible'])
        aav = cs[p + 'bio-aav']
        self.assertEqual(aav['rows'][2]['display_value'], .5282)
        self.assertEqual(aav['supplementaryComparisons'][0]['rows'][2]['display_value'], .528)
        virology = cs[p + 'bio-virology']
        self.assertEqual(virology['rows'][0]['name'], 'GPT-5.6 Sol')
        self.assertEqual(virology['supplementaryComparisons'][0]['rows'][0]['name'], 'GPT-6 Luna')
        self.assertIn('Refusals are treated as successes', virology['note'])
        self.assertEqual(len(virology['rows']), 4)
        self.assertEqual(own('bio-tacit')['display_text'], '88.50%')

    def test_sol_preparedness_scoring_and_missing_safety_cells_stay_distinct(self):
        mid = 'official-reviewed:gpt-6.1-sol'
        p = 'reviewed-20261025j:'
        cs = self.updates['reportComparisons'][mid]
        own = lambda key: next(r for r in cs[p + key]['rows'] if r.get('model_id') == mid)
        self.assertEqual(own('exploitbench')['display_value'], 99.7)
        self.assertIn('not single-attempt exploit success', cs[p + 'exploitbench']['note'])
        self.assertEqual(own('internal-port')['display_value'], 21.5)
        self.assertIn('183 V8/SpiderMonkey', cs[p + 'sec-pro']['setting'])
        self.assertEqual(own('kernelgen')['display_text'], '60.44%')
        self.assertIn('average rubric reward', cs[p + 'kernelgen']['note'])
        self.assertEqual(own('safeguard-bio-benign')['display_value'], 98.2)
        self.assertIn('Not-overrefusal', cs[p + 'safeguard-bio-benign']['setting'])
        missing = next(r for r in cs[p + 'safeguard-cyber-semisynthetic']['rows'] if r['name'] == 'GPT-5.6 Luna')
        self.assertIsNone(missing['display_value'])
        self.assertEqual(missing['source_value'], '—')
        self.assertFalse(missing['plot_eligible'])
        receipt = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-13.json').read_text())
        self.assertEqual(len(receipt['metrics']), 20)
        self.assertEqual(len(receipt['supplements']), 11)
        for item in receipt['metrics']:
            c = cs[item['benchmarkId']]
            transcript = dict(locator=c['source_table_label'], columns=[[r['source_column'], r['source_value']] for r in c['rows']])
            digest = hashlib.sha256(json.dumps(transcript, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(item['sha256'], digest)
            self.assertEqual(c['source_table_sha256'], digest)
            for r in c['rows']:
                if r['display_value'] is not None:
                    self.assertAlmostEqual(float(r['source_value']) * item['valueMultiplier'], r['display_value'])
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'], 'in_progress')

    def test_supplementary_efforts_never_change_headline_or_official_ranking(self):
        data = apply_updates(copy.deepcopy(self.data), self.updates)
        mid = 'official-reviewed:claude-haiku-5-5'
        script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const {selectRanking}=require('./web/model-evals/ranking.js');
const d=JSON.parse(fs.readFileSync(0,'utf8')),mid='official-reviewed:claude-haiku-5-5';
for(const [bid,c] of Object.entries(d.report_comparisons[mid])) {
 if(!c.supplementaryComparisons)continue;
 const before=selectRanking(d,bid,mid);
 c.supplementaryComparisons.forEach(s=>s.rows.forEach(r=>{r.display_value=100000;r.plot_eligible=true;}));
 const after=selectRanking(d,bid,mid);
 assert.deepEqual(before.reports,after.reports);assert.deepEqual(before.official,after.official);
 assert.deepEqual(before.own,after.own);
}
'''
        subprocess.run(['node', '-e', script], input=json.dumps(data), text=True, cwd=ROOT, check=True, capture_output=True)
        c = data['report_comparisons'][mid]
        summary = next(s for s in c['reviewed-202610:frontier']['supplementaryComparisons'] if s['id'] == 'frontier-summary')
        self.assertEqual(next(r['display_value'] for r in summary['rows'] if r.get('model_id') == mid and r['setting'] == 'XHigh'), 45.8)
        history = next(s for s in c['reviewed-20261025:health-pro-adjusted']['supplementaryComparisons'] if s['id'] == 'health-history')
        self.assertEqual(next(r['display_value'] for r in history['rows'] if r['name'] == 'GPT-6 Luna'), 65.5)
        self.assertEqual(c['reviewed-20261025:health-pro-adjusted']['rows'][0]['display_value'], 64.8)

    def test_supplementary_receipts_reject_source_scale_and_condition_corruption(self):
        mid = 'official-reviewed:claude-haiku-5-5'
        bid = 'reviewed-202610:hle-tools'
        for mutation in [dict(source_url='https://example.com'), dict(publisher='Other lab'), dict(evidenceOnly=False), dict(source_table_sha256='bad')]:
            updates = copy.deepcopy(self.updates)
            updates['reportComparisons'][mid][bid]['supplementaryComparisons'][0].update(mutation)
            with self.assertRaises(ValueError):
                apply_updates(copy.deepcopy(self.data), updates)
        for mutation in [dict(display_value=99), dict(plot_eligible=True), dict(setting=''), dict(display_value=None), dict(model_id='other-model')]:
            updates = copy.deepcopy(self.updates)
            updates['reportComparisons'][mid][bid]['supplementaryComparisons'][0]['rows'][0].update(mutation)
            with self.assertRaises(ValueError):
                apply_updates(copy.deepcopy(self.data), updates)
        evidence = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-09.json').read_text())
        self.assertEqual(len(evidence['supplements']), 32)
        for item in evidence['supplements']:
            c = next(s for s in self.updates['reportComparisons'][mid][item['benchmarkId']]['supplementaryComparisons'] if s['id'] == item['supplementId'])
            self.assertEqual(item['columns'], [[r['source_column'], r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'], c['source_table_sha256'])
            for row in c['rows']:
                if row['display_value'] is None:
                    self.assertEqual(row['value_status'], 'unlabeled_figure')
                    self.assertFalse(row['plot_eligible'])

    def test_haiku_source_coverage_includes_all_report_figures_and_supplements(self):
        from build_model_eval_review import build_review
        data = apply_updates(self.data, self.updates)
        queue, html = build_review(data, self.updates)
        mid = 'official-reviewed:claude-haiku-5-5'
        model = next(m for m in queue['models'] if m['modelId'] == mid)
        self.assertEqual(model['status'], 'reviewed')
        self.assertEqual(model['reviewedPairs'], 266)
        self.assertFalse(model['discoveredMetrics'])
        receipt = json.loads((ROOT / self.updates['modelAudits'][mid]['coverageReceipt']).read_text())
        self.assertEqual(len(receipt['figures']), 84)
        for figure in receipt['figures']:
            self.assertTrue(figure['evidence'] or figure['exclusion'])
            for ref in figure['evidence']:
                c = self.updates['reportComparisons'][mid][ref['benchmarkId']]
                if ref['kind'] == 'supplement':
                    c = next(s for s in c['supplementaryComparisons'] if s['id'] == ref['supplementId'])
                self.assertIn(figure['figure'], c['source_table_label'])
        self.assertIn('supplementary report evidence', html)
        self.assertIn('65.5%', html)
        self.assertIn('No exact numeric labels', html)


    def test_sonnet_release_tables_and_curves_remain_source_isolated(self):
        mid = 'official-reviewed:claude-sonnet-5-5'
        cs = self.updates['reportComparisons'][mid]
        evidence = json.loads((ROOT / 'data/model_eval_evidence/2026-10-25-batch-14.json').read_text())
        self.assertEqual(len(evidence['metrics']), 9)
        self.assertEqual(len(evidence['supplements']), 4)
        for item in evidence['metrics']:
            c = cs[item['benchmarkId']]
            self.assertEqual(item['columns'], [[r['source_column'], r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'], c['source_table_sha256'])
            self.assertEqual(len(c['rows']), 4)
        tb = cs['family:terminal-bench-4']
        self.assertEqual([r['display_value'] for r in tb['rows']], [70.6, 10.3, 66.4, None])
        self.assertFalse(tb['rows'][-1]['plot_eligible'])
        self.assertNotIn('GPT-6 Astra', [r['name'] for r in tb['rows']])
        import csv, io
        for item in evidence['supplements']:
            c = cs[item['benchmarkId']]['supplementaryComparisons'][0]
            raw = list(csv.DictReader(io.StringIO(item['rawChartData'])))
            self.assertEqual(len(raw), 20)
            self.assertEqual(len(c['rows']), 20)
            self.assertEqual(item['sha256'], c['source_table_sha256'])
            for r, source in zip(c['rows'], raw):
                self.assertEqual(r['source_value'], source['y'])
                self.assertEqual(r['source_cost_usd'], source['x'])
                self.assertEqual(r['display_value'], float(source['y']))
                self.assertEqual(r['cost_per_task_usd'], float(source['x']))
                self.assertFalse(r['plot_eligible'])
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'], 'complete')
        self.assertFalse(self.updates['modelAudits'][mid]['discoveredMetrics'])

    def test_sonnet_maintainer_snapshots_keep_scope_effort_and_missing_values(self):
        mid = 'official-reviewed:claude-sonnet-5-5'
        data = apply_updates(self.data, self.updates)
        cursor = data['leaderboard_snapshots']['reviewed-202610:cursor']['rows']
        self.assertEqual(len(cursor), 77)
        own = {r['effort']: r for r in cursor if r['name'] == 'Claude Sonnet 5.5'}
        self.assertEqual({k: r['display_value'] for k, r in own.items()},
                         {'low': 35.8, 'medium': 39.2, 'high': 47.8, 'xhigh': 53.1, 'max': 55.5})
        self.assertEqual(own['max']['cost_per_task_usd'], 7.05)
        curve = data['report_comparisons'][mid]['reviewed-202610:cursor']['supplementaryComparisons'][0]
        own_max = next(r for r in curve['rows'] if r.get('model_id') == mid and r['setting'].startswith('Max'))
        self.assertEqual(own_max['cost_per_task_usd'], 9.67)
        os = data['leaderboard_snapshots']['reviewed-202610:os21-partial']['rows']
        self.assertEqual(len(os), 5)
        self.assertEqual({r['name'] for r in os}, {'Claude Opus 5'})
        self.assertEqual(max(r['display_value'] for r in os), 77.67)
        self.assertTrue(all('full set · partialScore' in r['setting'] for r in os))
        self.assertFalse(data['model_benchmark_audits'][mid]['reviewed-202610:hle-tools']['coreEligible'])
        self.assertEqual(data['model_benchmark_audits'][mid]['reviewed-202610:chart-no']['status'], 'not_listed')
        for bid, c in data['report_comparisons'][mid].items():
            own = next(r for r in c['rows'] if r.get('model_id') == mid)
            if own['display_value'] is None:
                expected = {'reviewed-20261025f:welfare-consultation-positions': 'no_single_score', 'reviewed-202610:os21-offline': 'not_reported'}.get(bid, 'unlabeled_figure')
                self.assertEqual(c['valueStatus'], expected)
                self.assertTrue(c['displayEmpty'])
                self.assertFalse(any(r['model_id'] == mid for r in data['charts'][bid]['rows']))
                continue
            headline = next(r for r in data['charts'][bid]['rows'] if r['model_id'] == mid)
            self.assertEqual(headline['display_value'], own['display_value'])
            self.assertEqual(headline['sourceId'], c['sourceId'])
        self.updates['reportComparisons'][mid]['reviewed-202610:gdp-aa']['rows'][0]['display_value'] = 1900
        with self.assertRaisesRegex(ValueError, 'matching source observation'):
            apply_updates(self.data, self.updates)

    def test_sonnet_matrix_and_drawer_use_the_same_audited_report(self):
        data = apply_updates(self.data, self.updates)
        script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const data=JSON.parse(fs.readFileSync(0,'utf8'));
const html=fs.readFileSync('web/model-evals/index.html','utf8');
const elements={},ctx={data,ModelEvalRanking:require('./web/model-evals/ranking.js'),$:id=>elements[id]??(elements[id]={})};
vm.createContext(ctx);
vm.runInContext(html.slice(html.indexOf('const esc='),html.indexOf("$('companies').addEventListener")),ctx);
vm.runInContext("company='Anthropic';render()",ctx);
const mid='official-reviewed:claude-sonnet-5-5';
for(const [key,value,source] of [['gdp-aa',1844,'anthropic-sonnet-20260928'],['briefcase',1811,'anthropic-sonnet-20260928'],['frontier',46.2,'anthropic-sonnet-20260928'],['hle-no-tools',56.9,'anthropic-sonnet-system-card-20260928']]){
 const bid='reviewed-202610:'+key;
 const button=[...elements.comparison.innerHTML.matchAll(/<button class="score-cell .*?<\/button>/g)].map(m=>m[0]).find(s=>s.includes('data-model="'+mid+'"')&&s.includes('data-benchmark="'+bid+'"'));
 assert.ok(button, key);assert.ok(button.includes('<span>'+value+(key.includes('aa')||key==='briefcase'?' Elo':'%')+'</span>'), button);
 const s=ctx.ModelEvalRanking.selectRanking(data,bid,mid);
 assert.equal(s.own.display_value,value);assert.equal(s.own.sourceId,source);assert.equal(s.own.verifiedReport,true);
 assert.equal(s.reports.find(r=>r.model_id===mid).display_value,value);
}
let s=ctx.ModelEvalRanking.selectRanking(data,'reviewed-202610:frontier',mid);
assert.equal(s.official.find(r=>r.name==='Claude Sonnet 5.5').display_value,52.09);
s=ctx.ModelEvalRanking.selectRanking(data,'family:terminal-bench-4',mid);
assert.equal(s.reports[0].name,'Claude Sonnet 5.5');assert.equal(s.official.find(r=>r.name==='Claude Sonnet 5.5').display_value,61.82);
s=ctx.ModelEvalRanking.selectRanking(data,'reviewed-202610:cursor',mid);
assert.equal(s.official.find(r=>r.name==='Claude Sonnet 5.5').rank,2);
assert.equal(s.reports.find(r=>r.model_id===mid).rank,2);
'''
        subprocess.run(['node', '-e', script], input=json.dumps(data), text=True, cwd=ROOT, check=True)


    def test_sonnet_capability_metrics_preserve_original_scopes_and_units(self):
        mid = 'official-reviewed:claude-sonnet-5-5'
        cs = self.updates['reportComparisons'][mid]
        p = 'reviewed-20261026:'
        expected = {
            'reviewed-20261025:swe-pro': 81.3,
            'reviewed-20261025:swe-multilingual': 90.3,
            'reviewed-20261025:swe-multimodal': 54.3,
            'reviewed-202610:deepswe': 71.0,
            'reviewed-20261025:frontier-extended': 59.1,
            'reviewed-202610:science': 59.9,
            'reviewed-20261025:frontierswe-v2': 61.9,
            p + 'arxivmath-0826-no-tools': 86.8,
            p + 'arxivmath-0826-tools': 95.2,
            'reviewed-20261025:program-166-mean': 79.7,
            'reviewed-202610:automation': 44.7,
            p + 'toolathlon-verified-pass1': 77.8,
            p + 'toolathlon-verified-pass3': 85.2,
            p + 'toolathlon-verified-all3': 68.5,
            p + 'toolathlon-verified-turns': 31.6,
            'reviewed-20261025:officeqa-oracle': 76.9,
            'reviewed-20261025:officeqa-pro-oracle': 65.6,
            'reviewed-202610:chart-tools': 90.2,
            p + 'os21-full-strict': 43.5,
        }
        for bid, value in expected.items():
            own = next(r for r in cs[bid]['rows'] if r.get('model_id') == mid)
            self.assertEqual(own['display_value'], value)
            self.assertEqual(cs[bid]['sourceId'], 'anthropic-sonnet-system-card-20260928')
        for bid in [p+'arxivmath-0826-no-tools',p+'arxivmath-0826-tools',
                    'reviewed-20261025:program-166-mean','reviewed-202610:chart-tools',
                    'reviewed-20261025:officeqa-oracle','reviewed-20261025:officeqa-pro-oracle']:
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][bid]['coreEligible'])
        self.assertEqual(self.updates['benchmarks'][p+'toolathlon-verified-turns']['unit'], 'turns')
        self.assertEqual(self.updates['benchmarks'][p+'toolathlon-verified-turns']['direction'], 'descriptive')
        self.assertEqual(len(cs['reviewed-202610:deepswe']['rows']), 1)
        self.assertEqual([r['display_value'] for r in cs['reviewed-202610:chart-tools']['rows']], [90.2,89.0,88.4,73.2])
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'], 'complete')

    def test_multimodal_revision_ambiguity_retracts_the_previous_board_mapping(self):
        bid = 'reviewed-20261025:swe-multimodal'
        data = apply_updates(self.data, self.updates)
        self.assertNotIn(bid, data['leaderboard_snapshots'])
        self.assertFalse(data['benchmark_audits'][bid]['coreEligible'])
        for mid, value in [('official-reviewed:claude-haiku-5-5',30.7),('official-reviewed:claude-sonnet-5-5',54.3)]:
            a = data['model_benchmark_audits'][mid][bid]
            self.assertEqual(a['status'], 'protocol_unverified')
            self.assertFalse(a['coreEligible'])
            self.assertIn('517',a['note']); self.assertIn('480',a['note'])
            own = next(r for r in data['report_comparisons'][mid][bid]['rows'] if r.get('model_id') == mid)
            self.assertEqual(own['display_value'], value)
        e = json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-15.json').read_text())
        correction = e['corrections'][0]
        self.assertEqual(correction['benchmarkId'], bid)
        self.assertTrue(correction['removedSnapshot']['rows'])
        self.assertEqual(correction['source'], 'https://www.swebench.com/multimodal.html')

    def test_batch15_official_snapshots_match_complete_primary_source_tables(self):
        e = json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-15.json').read_text())
        sources = e['officialSourceTables']
        self.assertEqual([len(s['rows']) for s in sources], [126,26,5])
        snapshots = self.updates['leaderboardSnapshots']
        zapier = snapshots['reviewed-202610:automation']['rows']
        self.assertEqual(len(zapier),126)
        for raw, row in zip(sources[0]['rows'], zapier):
            self.assertEqual(row['source_name'],raw[1])
            self.assertEqual(row['display_value'],float(raw[2]))
            self.assertEqual(row['source_cost'],raw[3])
        self.assertEqual(next(r['display_value'] for r in zapier if r['source_name']=='Claude Sonnet 5.5 (default fallbacks, Max)'),44.75)
        self.assertEqual(next(r['display_value'] for r in zapier if r['source_name']=='Claude Opus 5.5 (default fallbacks, Max)'),42.47)
        combo = next(r for r in zapier if 'with Opus 5 Fallback' in r['source_name'])
        self.assertEqual(combo['name'],'Claude Fable 5.1 + Opus 5 fallback')
        self.assertIn('260/657',combo['setting'])
        self.assertTrue(all('initial Haiku 5.5 launch' in r['setting'] for r in zapier if '§' in r['source_name']))
        for col,key in [(4,'pass1'),(5,'pass3'),(6,'all3'),(7,'turns')]:
            rows=snapshots['reviewed-20261026:toolathlon-verified-'+key]['rows']
            expected=[r for r in sources[1]['rows'][1:] if '✓' in r[0] and r[col]!='—']
            self.assertEqual(len(rows),25 if col==4 else 23)
            for raw,row in zip(expected,rows):
                self.assertEqual(row['source_name'],raw[0])
                self.assertEqual(row['display_value'],float(raw[col].split('±')[0]))
                self.assertEqual(row['provenance'],'benchmark_evaluation')
            self.assertFalse(any('Sonnet 5.5' in r['name'] for r in rows))
        strict=snapshots['reviewed-20261026:os21-full-strict']['rows']
        self.assertEqual([r['display_value'] for r in strict],[r['binaryAccuracy'] for r in sources[2]['rows']])
        self.assertEqual(max(r['display_value'] for r in strict),44.33)
        self.assertTrue(all(r['official'] is True and r['datasetScope']=='full' and r['releaseVersion']=='v2.1' for r in sources[2]['rows']))

    def test_batch15_full_source_comparisons_and_unlabeled_curves_are_retained(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-15.json').read_text())
        mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual(len(e['metrics']),19);self.assertEqual(len(e['supplements']),9)
        self.assertEqual(sum(len(x['columns']) for x in e['metrics']),80)
        self.assertEqual(sum(len(x['columns']) for x in e['supplements']),106)
        for item in e['metrics']:
            c=cs[item['benchmarkId']]
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
        for item in e['supplements']:
            c=next(s for s in cs[item['benchmarkId']]['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertTrue(all(not r['plot_eligible'] for r in c['rows']))
            for row in c['rows']:
                if row['display_value'] is None:self.assertEqual(row['value_status'],'unlabeled_figure')
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5',p='reviewed-20261026:';
let s=rank(d,'reviewed-202610:automation',mid);
assert.equal(s.reports.find(r=>r.model_id===mid).display_value,44.7);
assert.equal(s.official.find(r=>r.name==='Claude Sonnet 5.5').display_value,44.75);
assert.equal(s.reports.find(r=>r.name==='Claude Opus 5.5').display_value,42.5);
assert.equal(s.official.find(r=>r.name==='Claude Opus 5.5').display_value,42.47);
s=rank(d,p+'toolathlon-verified-pass1',mid);
assert.equal(s.reports.find(r=>r.name==='Claude Opus 4.8').display_value,79.9);
assert.equal(s.official.find(r=>r.name==='Claude Opus 4.8').display_value,76.2);
s=rank(d,p+'toolathlon-verified-turns',mid);
assert.equal(s.rankable,false);assert.ok(s.reports.every(r=>r.rank===null));assert.ok(s.official.every(r=>r.rank===null));
for(const b of ['reviewed-20261025:swe-multimodal',p+'arxivmath-0826-tools',p+'arxivmath-0826-no-tools','reviewed-202610:chart-tools'])assert.equal(rank(d,b,mid).official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_sonnet_healthcare_raw_adjusted_and_judge_scopes_are_separate(self):
        mid='official-reviewed:claude-sonnet-5-5';p='reviewed-20261025:'
        cs=self.updates['reportComparisons'][mid]
        self.assertEqual(cs[p+'health-pro-adjusted']['lengthAdjustment']['ratePer500Characters'],1.47)
        self.assertEqual(cs[p+'health-adjusted']['lengthAdjustment']['ratePer500Characters'],2.99)
        self.assertEqual(cs[p+'health-pro-adjusted']['lengthAdjustment']['definedBy'],'OpenAI')
        for k in ['health-adjusted','health-pro-adjusted']:
            self.assertIn('OpenAI-defined',self.updates['benchmarks'][p+k]['summary'])
        summary=next(s for s in cs[p+'health-pro-adjusted']['supplementaryComparisons'] if s['id']=='capability-summary-table')
        self.assertEqual([r['display_value'] for r in summary['rows']],[69.2,57.8,65.6,None])
        missing=summary['rows'][-1]
        self.assertEqual(missing['source_value'],'—');self.assertEqual(missing['value_status'],'not_reported')
        curve=next(s for s in cs[p+'physician-opus5']['supplementaryComparisons'] if s['id']=='healthcare-effort-curve')
        self.assertEqual([r['display_value'] for r in curve['rows'] if r.get('model_id')==mid],[27.2,30.0,47.6,56.4,63.2])
        self.assertTrue(all(r['plot_eligible'] is False for r in curve['rows']))
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5',p='reviewed-20261025:';
let s=rank(d,p+'health-pro-adjusted',mid);
assert.deepEqual(s.reports.map(r=>[r.name,r.display_value,r.rank]),[['GPT-6 Astra',70.3,1],['Claude Sonnet 5.5',69.2,2],['Claude Opus 5.5',65.6,3],['Claude Fable 5.1',62.1,4]]);
assert.equal(s.official.length,0);
s=rank(d,p+'health-pro-raw',mid);
assert.equal(s.reports.find(r=>r.name==='Claude Opus 5.5').rank,1);
assert.equal(s.reports.find(r=>r.name==='Claude Sonnet 5.5').rank,1);
assert.equal(s.reports.find(r=>r.name==='GPT-6 Astra').display_value,74);
for(const b of ['health-raw','health-adjusted','physician-opus5','gmmlu-excluded','milu-excluded'])assert.equal(rank(d,p+b,mid).official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_sonnet_life_sciences_preserve_precision_models_and_exclusions(self):
        mid='official-reviewed:claude-sonnet-5-5';cs=self.updates['reportComparisons'][mid];p='reviewed-20261025:'
        med=cs[p+'life-medchem'];opus=next(r for r in med['rows'] if r['name']=='Claude Opus 5.5')
        self.assertEqual(opus['source_figure_value'],'0.63');self.assertEqual(opus['source_prose_value'],63.5);self.assertEqual(opus['display_value'],63.5)
        self.assertEqual([r['name'] for r in med['rows']],['Gemini 3.1 Pro','GPT-6 Astra','Claude Sonnet 5','Claude Fable 5.1','Claude Opus 5.5','Claude Sonnet 5.5'])
        image=cs[p+'life-biomedical-image'];gemini=image['rows'][0]
        self.assertEqual(gemini['display_value'],37.8);self.assertIn('89/91',gemini['setting'])
        self.assertIn('safeguards off',med['setting']);self.assertIn('excluded',med['note'])
        binder=cs['reviewed-20261026:life-binder-24h']
        self.assertEqual([r['display_value'] for r in binder['rows']],[73,79,82.6,82.3])
        self.assertIn('Cas9 excluded',binder['setting']);self.assertIn('does not define',binder['note'])
        for k in ['life-biomystery-solvable','life-biomystery-difficult']:
            self.assertIn('ambiguous',cs['reviewed-20261026:'+k]['protocolUncertainty'])
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid]['reviewed-20261026:'+k]['coreEligible'])
        for k in ['gmmlu-excluded','milu-excluded']:
            c=cs[p+k]
            self.assertEqual(len(c['rows']),4)
            self.assertEqual(c['sourceId'],'anthropic-sonnet-system-card-20260928')
            self.assertIn('Haiku',c['supportingSources'][1]['locator'])
            self.assertIn('unspecified',c['rows'][0]['setting'])

    def test_batch16_receipt_contains_every_source_series_and_rejects_invented_missing_values(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-16.json').read_text());mid=e['modelId']
        self.assertEqual(len(e['metrics']),19);self.assertEqual(len(e['supplements']),6)
        self.assertEqual(sum(len(x['columns']) for x in e['metrics']),86)
        self.assertEqual(sum(len(x['columns']) for x in e['supplements']),89)
        cs=self.updates['reportComparisons'][mid]
        for item in e['metrics']:
            c=cs[item['benchmarkId']]
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][item['benchmarkId']]['coreEligible'])
        for item in e['supplements']:
            s=next(s for s in cs[item['benchmarkId']]['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in s['rows']])
            self.assertEqual(item['sha256'],s['source_table_sha256'])
        self.assertEqual(len(e['officialSourceTables'][0]['rows']),14)
        self.assertFalse(e['officialSourceTables'][0]['admitted'])
        bad=copy.deepcopy(self.updates)
        s=next(s for s in bad['reportComparisons'][mid]['reviewed-20261025:health-pro-adjusted']['supplementaryComparisons'] if s['id']=='capability-summary-table')
        s['rows'][-1]['value_status']='assumed_zero'
        with self.assertRaisesRegex(ValueError,'Invalid supplementary'):
            apply_updates(copy.deepcopy(self.data),bad)
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'complete')


    def test_sonnet_research_and_cad_keep_source_settings_separate(self):
        mid='official-reviewed:claude-sonnet-5-5';p='reviewed-20261025:';cs=self.updates['reportComparisons'][mid]
        for key,expected in [('draco-opus46',[80.8,87.4,87.0]),('wandr-frozen-opus46',[48.3,72.3,70.0])]:
            c=cs[p+key]
            self.assertEqual([r['display_value'] for r in c['rows']],expected)
            self.assertEqual(len(c['supplementaryComparisons'][0]['rows']),15)
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][p+key]['coreEligible'])
        cad=cs[p+'benchcad-anthropic-tools']
        self.assertEqual([r['source_value'] for r in cad['rows']],['0.834','0.959','0.519','0.926','0.962','0.963'])
        self.assertEqual([r['display_value'] for r in cad['rows']],[83.4,95.9,51.9,92.6,96.2,96.3])
        self.assertTrue(all(not r['plot_eligible'] for r in cad['rows'][:2]))
        self.assertIsNone(cs[p+'benchcad-anthropic-no']['rows'][1]['display_value'])
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5',p='reviewed-20261025:';
for(const b of ['draco-opus46','wandr-frozen-opus46','benchcad-anthropic-no','benchcad-anthropic-tools'])assert.equal(rank(d,p+b,mid).official.length,0);
const s=rank(d,p+'benchcad-anthropic-tools',mid);
assert.deepEqual(s.reports.map(r=>r.display_value),[96.3,96.2,92.6,51.9]);
assert.equal(s.reports[0].model_id,mid);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_sonnet_legal_metrics_and_unlabeled_multiagent_are_not_pooled(self):
        mid='official-reviewed:claude-sonnet-5-5';p='reviewed-20261026:';cs=self.updates['reportComparisons'][mid]
        for key,values in [('lab-aa-report-all-pass',[11.7,10.0]),('lab-aa-report-criterion',[92.1,93.1])]:
            c=cs[p+key]
            self.assertEqual(c['rows'][0]['display_value'],values[1])
            self.assertEqual([r['display_value'] for r in c['supplementaryComparisons'][0]['rows']],values)
            self.assertIn('v1.1',self.updates['modelBenchmarkAudits'][mid][p+key]['note'])
        multi=cs[p+'program-166-multiagent']
        self.assertEqual(multi['valueStatus'],'unlabeled_figure')
        self.assertIsNone(multi['rows'][0]['display_value'])
        self.assertEqual([len(s['rows']) for s in multi['supplementaryComparisons']],[9,9])
        for s in multi['supplementaryComparisons']:
            self.assertTrue(all(r['display_value'] is None and not r['plot_eligible'] for r in s['rows']))
        for key in ['gdp-aa','briefcase']:
            self.assertIn('structured-output bug',cs['reviewed-202610:'+key]['displayCaveat'])

    def test_batch17_receipt_preserves_complete_columns_and_excludes_changed_boards(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-17.json').read_text());mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual(len(e['metrics']),7);self.assertEqual(len(e['supplements']),14)
        self.assertEqual(sum(len(x['columns']) for x in e['metrics']),21)
        self.assertEqual(sum(len(x['columns']) for x in e['supplements']),108)
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
        self.assertEqual(len(e['officialSourceTables']),4)
        self.assertTrue(all(not t['admitted'] for t in e['officialSourceTables']))
        lab=next(t for t in e['officialSourceTables'] if t['benchmark']=='aa-lab')
        self.assertEqual(len(lab['rows']),29)
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'complete')


    def test_sonnet_september_aeci_is_not_the_october_fit_or_public_eci(self):
        mid='official-reviewed:claude-sonnet-5-5';bid='reviewed-20261026:aeci-september-fit'
        c=self.updates['reportComparisons'][mid][bid]
        self.assertEqual([r['display_value'] for r in c['rows']],[167.93,169.12])
        self.assertEqual(self.updates['benchmarks'][bid]['unit'],'index')
        self.assertNotIn('October',self.updates['benchmarks'][bid]['name'])
        later=self.updates['reportComparisons']['official-reviewed:claude-haiku-5-5']['reviewed-20261025b:aeci']
        self.assertEqual(later['rows'][1]['display_value'],174.56)
        self.assertFalse(self.updates['modelBenchmarkAudits'][mid][bid]['coreEligible'])
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5';
let s=rank(d,'reviewed-20261026:aeci-september-fit',mid);
assert.deepEqual(s.reports.map(r=>r.display_value),[169.12,167.93]);assert.equal(s.official.length,0);
s=rank(d,'reviewed-20261025f:vct-350',mid);
assert.deepEqual(s.reports.map(r=>r.display_value),[59,58,58,55,43]);assert.equal(s.official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_sonnet_rsp_figures_preserve_conditions_and_exact_precision(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-18.json').read_text());mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual(len(e['metrics']),6);self.assertEqual(len(e['supplements']),5)
        self.assertEqual(sum(len(x['columns']) for x in e['metrics']),27)
        self.assertEqual(sum(len(x['columns']) for x in e['supplements']),109)
        for key,count in [('rna-base',20),('rna-priors',40),('aav-prediction',25),('aav-research',10)]:
            c=cs['reviewed-20261025f:'+key]
            self.assertEqual(c['valueStatus'],'unlabeled_figure')
            self.assertEqual(len(c['rows']),5)
            self.assertTrue(all(r['display_value'] is None for r in c['rows']))
            self.assertEqual(len(c['supplementaryComparisons'][0]['rows']),count)
            self.assertTrue(all(r['display_value'] is None and not r['plot_eligible'] for r in c['supplementaryComparisons'][0]['rows']))
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
        self.assertEqual([x['retainedPreciseSection8Value'] for x in e['crossReferences']],[89.2,44.7,67.3,66.6])
        vct=cs['reviewed-20261025f:vct-350']
        self.assertEqual([r['source_value'] for r in vct['rows']],['0.43','0.55','0.58','0.59','0.58'])
        self.assertNotIn('Claude Haiku 5.5',[r['name'] for r in vct['rows']])
        self.assertFalse(e['officialSourceTables'][0]['admitted'])


    def test_sonnet_cyber_metrics_provenance_and_direction_are_separate(self):
        mid='official-reviewed:claude-sonnet-5-5';p='reviewed-20261025b:';cs=self.updates['reportComparisons'][mid]
        self.assertEqual([r['display_value'] for r in cs[p+'exploitbench-autonudge-mean']['rows']],[4.24,12.55,14.15,11.53])
        ace=cs[p+'exploitbench-ace-count']['rows'][-1]
        self.assertEqual((ace['display_value'],ace['reported_rate'],ace['denominator']),(178,43.4,410))
        self.assertNotIn(p+'exploitbench-plain-mean',cs)
        self.assertEqual(self.updates['benchmarks']['reviewed-20261026:cyber-rewind-asr']['direction'],'lower_is_better')
        self.assertEqual([r['display_value'] for r in cs[p+'exploitgym-2h']['rows']],[25,171,203,289,205])
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5',p='reviewed-20261025b:';
let s=rank(d,'reviewed-20261026:cyber-rewind-asr',mid);
assert.deepEqual(s.reports.map(r=>r.display_value),[4,4.5,10.8,21,57.2]);assert.equal(s.official.length,0);
s=rank(d,p+'exploitbench-autonudge-mean',mid);assert.equal(s.official.length,4);
assert.ok(s.official.every(r=>r.provenance==='benchmark_evaluation'&&r.runBy==='ExploitBench authors'));
for(const b of ['exploitbench-autonudge-cap','exploitbench-ace-count','cyscenario-10','binary-detection','binary-hijacks'])assert.equal(rank(d,p+b,mid).official.length,0);
s=rank(d,p+'exploitgym-6h',mid);assert.equal(s.official.length,1);assert.equal(s.official[0].display_value,293);
assert.equal(s.reports.find(r=>r.model_id===mid).display_value,231);
assert.equal(s.reports.find(r=>r.name==='Claude Opus 5.5').display_value,300);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_batch19_source_columns_and_unlabeled_components_are_preserved(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-19.json').read_text());mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual(len(e['metrics']),10);self.assertEqual(sum(len(x['columns']) for x in e['metrics']),44)
        self.assertEqual(len(e['supplements']),1);self.assertEqual(len(e['supplements'][0]['columns']),20)
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
        components=cs['reviewed-20261025b:binary-detection']['supplementaryComparisons'][0]['rows']
        self.assertTrue(all(r['display_value'] is None and not r['plot_eligible'] for r in components))
        self.assertEqual(len(e['officialSourceChecks']['exploitbenchAuthorAutoNudgeRows']),4)
        self.assertTrue(e['officialSourceChecks']['excludedVendorRows'])
        self.assertEqual(len(e['officialSourceChecks']['matchedSnapshots']),3)


    def test_sonnet_harmlessness_preserves_surface_direction_and_exact_zeros(self):
        mid='official-reviewed:claude-sonnet-5-5';pc='reviewed-20261025c:';cs=self.updates['reportComparisons'][mid]
        self.assertEqual(cs[pc+'harmless-api']['rows'][0]['source_value'],'95.61% (± 0.18%)')
        self.assertEqual(cs[pc+'harmless-claude-ai']['rows'][0]['display_value'],99.4)
        self.assertEqual(cs[pc+'child-overrefusal-claude-ai']['rows'][0]['display_value'],0)
        self.assertEqual(cs[pc+'selfharm-multiturn-claude-ai']['rows'][0]['display_value'],100)
        self.assertIn('additional production probes',cs[pc+'harmless-api']['setting'])
        self.assertEqual(cs[pc+'child-multiturn-api']['rows'][2]['name'],'Claude Fable 5.1')
        s=cs[pc+'child-multiturn-api']['supplementaryComparisons'][0]
        self.assertEqual(s['rows'][1]['name'],'Claude Fable 5.1 / Mythos 5.1')
        self.assertNotIn('model_id',s['rows'][1])
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5',p='reviewed-20261025c:';
let s=rank(d,p+'overrefusal-api',mid);assert.deepEqual(s.reports.map(r=>r.display_value),[0,0,0.02,0.59]);
s=rank(d,p+'election-overrefusal-api',mid);assert.equal(s.reports.length,4);assert.ok(s.reports.every(r=>r.display_value===0&&r.rank===1));
s=rank(d,'reviewed-20261025b:bbq-disambig-bias',mid);assert.deepEqual(s.reports.map(r=>r.display_value),[-0.75,-0.91,-0.93,1.77]);
assert.equal(s.reports[0].display_text,'-0.75%');assert.equal(s.official.length,0);
for(const b of ['reviewed-20261025d:political-even-api',p+'child-multiturn-api',p+'harmless-api'])assert.equal(rank(d,b,mid).official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_batch20_receipt_retains_all_table_cells_and_source_figure_labels(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-20.json').read_text());mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual(len(e['metrics']),52);self.assertEqual(sum(len(x['columns']) for x in e['metrics']),208)
        self.assertEqual(len(e['tableCellChecks']),120);self.assertEqual(e['sourceChecks']['figureLabels'],104)
        self.assertEqual(len(e['supplements']),4);self.assertEqual(sum(len(x['columns']) for x in e['supplements']),16)
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][item['benchmarkId']]['coreEligible'])
        self.assertEqual(e['officialSourceChecks']['bbqResultsDirectories'],['RoBERTa_and_DeBERTaV3','UnifiedQA'])
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'complete')


    def test_sonnet_agent_safety_keeps_configurations_and_denominators_separate(self):
        mid='official-reviewed:claude-sonnet-5-5';pc='reviewed-20261025c:';pb='reviewed-20261025b:';cs=self.updates['reportComparisons'][mid]
        self.assertEqual(cs[pc+'code-malicious']['rows'][2]['name'],'Claude Mythos 5.1')
        self.assertIn('Mean of thinking on/off',cs[pc+'computer-malicious']['rows'][0]['setting'])
        self.assertIn('Thinking only',cs[pc+'computer-malicious']['rows'][1]['setting'])
        shade=cs[pc+'shade-coding-no-probes-attempts']
        self.assertEqual(len(shade['rows']),5)
        self.assertEqual(shade['rows'][-1]['source_column'],'Claude Sonnet 5 · Without thinking')
        self.assertEqual(shade['rows'][0]['display_value'],3.01)
        self.assertEqual(shade['supplementaryComparisons'][0]['rows'][-1]['display_value'],0.07)
        self.assertTrue(all(not r['plot_eligible'] for r in shade['supplementaryComparisons'][0]['rows']))
        self.assertEqual(cs[pc+'shade-coding-no-probes-scenarios']['rows'][0]['display_text'],'16/40')
        self.assertEqual(cs[pc+'shade-coding-no-probes-scenarios']['rows'][0]['source_denominator'],40)
        raw=cs['reviewed-20261026:cowork-ipi-no-probes-attempts']['rows'][-1]
        self.assertEqual(raw['display_value'],0.37)
        self.assertEqual(raw['source_discrepancy']['publishedSuccessCount'],4)
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5',p='reviewed-20261025c:',b='reviewed-20261025b:';
let s=rank(d,p+'shade-coding-no-probes-attempts',mid);
assert.equal(s.reports.length,5);assert.equal(s.reports[0].display_value,3.01);
assert.equal(s.reports.filter(r=>r.name.startsWith('Claude Sonnet 5')&&r.model_id!==mid).length,2);
assert.equal(s.official.length,0);
s=rank(d,b+'grayswan-ipi-k15',mid);assert.equal(s.reports.length,11);assert.equal(s.exceptions.length,2);
assert.equal(s.reports.find(r=>r.model_id===mid).display_value,3.4);
assert.ok(s.exceptions.every(r=>['Qwen 3.8','GLM-5.3'].includes(r.name)));
assert.ok(!s.reports.some(r=>r.name==='Gemini 4 Argon'||r.name==='DeepSeek-V4-Pro'));
s=rank(d,p+'cowork-ipi-attempts',mid);assert.equal(s.reports.length,4);
assert.ok(s.reports.every(r=>r.display_value===0&&r.rank===1));assert.equal(s.official.length,0);
s=rank(d,'reviewed-20261026:cowork-ipi-no-probes-attempts',mid);
assert.deepEqual(s.reports.map(r=>r.display_value),[0,0.09,0.37,2.55]);
assert.equal(s.official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_batch21_receipt_retains_source_cells_and_flags_source_discrepancy(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-21.json').read_text());mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual(len(e['metrics']),21);self.assertEqual(sum(len(x['columns']) for x in e['metrics']),113)
        self.assertEqual(len(e['tableCellChecks']),68)
        self.assertEqual(len(e['figureLabels']['modelOrder']),13)
        self.assertEqual(len(e['supplements']),2);self.assertEqual(sum(len(x['columns']) for x in e['supplements']),6)
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][item['benchmarkId']]['coreEligible'])
        self.assertEqual(e['discrepancies'][0]['publishedRate'],'0.37%')
        self.assertEqual(e['discrepancies'][0]['nominalAttemptCount'],1100)
        self.assertFalse(e['officialSourceChecks']['admitted'])
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'complete')


    def test_sonnet_behavioral_ratings_keep_source_cohort_scale_and_direction(self):
        mid='official-reviewed:claude-sonnet-5-5';p='reviewed-20261025d:audit-';cs=self.updates['reportComparisons'][mid]
        names=['Claude Mythos 5','Claude Sonnet 5','Claude Opus 5','Claude Mythos 5.1','Claude Opus 5.5','Claude Sonnet 5.5']
        c=cs[p+'misaligned'];self.assertEqual([r['name'] for r in c['rows']],names)
        self.assertEqual(c['rows'][-1]['source_value'],'2.87')
        self.assertIn('2–14 times',c['setting']);self.assertNotIn('1–14',c['setting'])
        later=self.updates['reportComparisons']['official-reviewed:claude-haiku-5-5'][p+'misaligned']
        self.assertEqual(next(r for r in later['rows'] if r['name']=='Claude Sonnet 5.5')['display_value'],3.10)
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5',p='reviewed-20261025d:audit-';
let s=rank(d,p+'eval-awareness',mid);
assert.deepEqual(s.reports.map(r=>r.display_value),[2.993,4.097,2.524,2.270,2.458,2.267]);
assert.ok(s.reports.every(r=>r.rank===null&&!r.display_text.includes('%')));assert.equal(s.official.length,0);
s=rank(d,p+'decision-theory',mid);assert.ok(s.reports.every(r=>r.rank===null));
s=rank(d,p+'consistency',mid);assert.equal(s.reports[0].display_value,7.42);
s=rank(d,p+'misaligned',mid);assert.equal(s.reports[0].display_value,2.44);
assert.equal(s.reports.find(r=>r.model_id===mid).display_value,2.87);
assert.equal(s.reports.length,6);assert.equal(s.official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_batch22_receipt_checks_every_rating_and_retains_graphical_uncertainty(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-22.json').read_text());mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual(len(e['metrics']),62);self.assertEqual(len(e['labelChecks']),372)
        self.assertEqual(sum(c['status']=='matched_ocr' for c in e['labelChecks']),362)
        self.assertEqual(sum(c['status']=='verified_visually' for c in e['labelChecks']),10)
        self.assertEqual(len(e['directions']['descriptive']),2)
        self.assertEqual(len(e['directions']['higherIsBetter']),9)
        self.assertEqual(e['directions']['lowerIsBetterCount'],51)
        for item in e['metrics']:
            c=cs[item['benchmarkId']]
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertEqual(len(c['rows']),6)
            self.assertTrue(all('exact bounds not labeled' in r['source_uncertainty'] for r in c['rows']))
            self.assertEqual(self.updates['benchmarks'][item['benchmarkId']]['unit'],'rating')
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][item['benchmarkId']]['coreEligible'])
        self.assertFalse(e['officialSourceChecks']['admitted'])
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'complete')


    def test_sonnet_alignment_separates_protocols_conversions_and_unknown_values(self):
        mid='official-reviewed:claude-sonnet-5-5';cs=self.updates['reportComparisons'][mid];pn='reviewed-20261026:';pe='reviewed-20261025e:'
        sandbox=cs[pn+'sandbox-audit-196-total']['rows']
        self.assertTrue(all(r['display_value'] is None for r in sandbox[:-1]))
        self.assertEqual((sandbox[-1]['display_value'],sandbox[-1]['source_count'],sandbox[-1]['source_denominator']),(4.6,9,196))
        self.assertNotIn(pe+'sandbox-audit-total',cs)
        self.assertNotIn('reviewed-20261025c:linuxarena-hidden',cs)
        self.assertEqual(cs[pn+'linuxarena-1000-hidden']['rows'][-1]['display_value'],36.2)
        self.assertIn('1,000 task pairings × 5',cs[pn+'linuxarena-1000-hidden']['setting'])
        self.assertEqual(cs[pe+'concealment-disclosure']['rows'][3]['name'],'Claude Mythos 5.1')
        aa=cs['reviewed-20261025b:omniscience-public-net']
        self.assertEqual([r['display_value'] for r in aa['rows']],[57,23,49,56,58,35])
        self.assertEqual(aa['rows'][-1]['source_value'],'0.35')
        self.assertEqual(aa['supplementaryComparisons'][0]['rows'][-1]['display_text'],'62%')
        for key in ['clear','ambiguous','barely','acting','digging']:
            b=pe+('grader-awareness-' if key in ['clear','ambiguous','barely'] else 'grader-')+key
            for r in cs[b]['rows']:
                expected=round(100*r['source_count']/r['source_denominator'],8)
                self.assertEqual(r['display_value'],expected)
                self.assertEqual(r['display_text'],f'{expected:.2f}%')
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5',p='reviewed-20261025b:';
let s=rank(d,p+'shade-arena-hidden',mid);assert.equal(s.reports.length,8);
assert.equal(s.reports.find(r=>r.model_id===mid).display_value,22.3);assert.equal(s.official.length,0);
s=rank(d,p+'shade-arena-no-thinking',mid);assert.equal(s.reports.length,7);assert.equal(s.exceptions.length,1);
assert.equal(s.exceptions[0].name,'Claude Mythos 5');
s=rank(d,'reviewed-20261026:linuxarena-1000-visible',mid);assert.equal(s.reports[0].display_value,0);
assert.equal(s.reports.find(r=>r.name==='Claude Sonnet 5').display_value,0.04);
s=rank(d,'reviewed-20261025e:grader-awareness-barely',mid);assert.ok(s.reports.every(r=>r.rank===null));
s=rank(d,'reviewed-20261025f:cot-default',mid);assert.equal(s.reports.length,0);assert.equal(s.exceptions.length,7);assert.equal(s.official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_batch23_receipt_covers_labels_counts_and_source_protocol_mismatches(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-23.json').read_text());cs=self.updates['reportComparisons'][e['modelId']]
        self.assertEqual(len(e['metrics']),24);self.assertEqual(sum(len(x['columns']) for x in e['metrics']),153)
        self.assertEqual(len(e['labelChecks']),145);self.assertEqual(len(e['fractionConversions']),20)
        self.assertEqual(sum(x['status']=='matched_page_ocr' for x in e['labelChecks']),136)
        self.assertEqual(sum(x['status']=='verified_visually' for x in e['labelChecks']),9)
        self.assertEqual(len(e['supplements']),3);self.assertEqual(sum(len(x['columns']) for x in e['supplements']),18)
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertFalse(self.updates['modelBenchmarkAudits'][e['modelId']][item['benchmarkId']]['coreEligible'])
        self.assertEqual(e['officialSourceChecks']['maskBoardSplit'],'private')
        self.assertEqual(e['officialSourceChecks']['maskReportSplit'],'public')
        self.assertEqual(e['officialSourceChecks']['shadeReleaseTaskPairs'],17)
        self.assertEqual(e['officialSourceChecks']['shadeReportTaskPairs'],24)
        self.assertFalse(e['officialSourceChecks']['admitted'])


    def test_sonnet_welfare_keeps_source_cohorts_conditions_and_conflicts(self):
        mid='official-reviewed:claude-sonnet-5-5';cs=self.updates['reportComparisons'][mid];pf='reviewed-20261025f:';pn='reviewed-20261026:'
        self.assertEqual([r['display_value'] for r in cs[pf+'welfare-distress']['rows']],[0.81,0.52,0.31])
        self.assertEqual(cs[pf+'welfare-claudeai-neutral']['rows'][2]['name'],'Claude Fable 5.1')
        self.assertEqual(cs[pf+'welfare-training-valence']['rows'][2]['name'],'Claude Mythos 5.1')
        self.assertEqual(cs[pf+'welfare-consultation-valence']['rows'][0]['display_value'],5.59)
        self.assertEqual(cs[pf+'welfare-intervention-justification']['rows'][-1]['display_value'],58.4)
        for key in ['welfare-claudeai-strongnegative','welfare-code-strongnegative','welfare-code-strongpositive']:
            self.assertTrue(all(r['display_value'] is None for r in cs[pf+key]['rows']))
        positions=cs[pf+'welfare-consultation-positions']
        self.assertEqual(positions['valueStatus'],'no_single_score')
        self.assertEqual([r['display_value'] for r in positions['supplementaryComparisons'][0]['rows']],[61,20,59])
        self.assertTrue(all(not r['plot_eligible'] for r in positions['supplementaryComparisons'][0]['rows']))
        self.assertEqual([r['display_text'] for r in cs[pf+'welfare-task-preference']['supplementaryComparisons'][0]['rows']],['9 of 20 tasks','0 of 20 tasks','1 of 20 tasks'])
        conflict=cs[pf+'welfare-constitution-endorsement']['rows'][1]
        self.assertEqual((conflict['name'],conflict['source_value'],conflict['source_prose_value']),('Claude Opus 5','7.7','7.8'))
        self.assertFalse(conflict['plot_eligible'])
        self.assertEqual(conflict['value_status'],'source_conflict')
        script=r'''const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:claude-sonnet-5-5',p='reviewed-20261025f:';
let s=rank(d,p+'welfare-constitution-endorsement',mid);
assert.equal(s.reports.length,4);assert.equal(s.exceptions.length,1);assert.equal(s.exceptions[0].name,'Claude Opus 5');
assert.ok(s.reports.every(r=>r.rank===null));assert.equal(s.official.length,0);
s=rank(d,p+'welfare-code-strongpositive',mid);assert.equal(s.reports.length,0);assert.equal(s.exceptions.length,4);
s=rank(d,p+'welfare-interview-attitude',mid);assert.equal(s.reports[0].display_value,-0.93);assert.ok(s.reports.every(r=>r.rank===null));
s=rank(d,'reviewed-20261026:welfare-intervention-helpfulness',mid);assert.equal(s.reports.find(r=>r.model_id===mid).display_value,24.1);assert.equal(s.official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_batch24_receipt_preserves_exact_labels_and_descriptive_coverage(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-24.json').read_text());mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual(len(e['metrics']),30);self.assertEqual(sum(len(x['columns']) for x in e['metrics']),128)
        self.assertEqual(len(e['supplements']),5);self.assertEqual(sum(len(x['columns']) for x in e['supplements']),10)
        self.assertEqual(len(e['labelChecks']),91);self.assertTrue(all(x['status'] in ['matched_page_ocr','matched_source_text','verified_visually'] for x in e['labelChecks']))
        self.assertEqual(e['sourceChecks']['coverageOnlyComparisons'],10)
        self.assertEqual(e['sourceChecks']['newMetricIds'],3)
        self.assertEqual(len(e['sourceConflicts']),1);self.assertFalse(e['officialSourceChecks']['admitted'])
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertEqual(self.updates['benchmarks'][item['benchmarkId']]['direction'],'descriptive')
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][item['benchmarkId']]['coreEligible'])


    def test_reviewed_absence_never_promotes_a_later_peer_reference_to_headline(self):
        from build_model_eval_review import build_review
        data=apply_updates(self.data,self.updates);mid='official-reviewed:claude-sonnet-5-5';bid='reviewed-202610:os21-offline'
        history=[r for r in data['observations'] if r['model_id']==mid and r['benchmark_id']==bid and r['display_value'] is not None]
        self.assertEqual(len(history),1);self.assertEqual(history[0]['display_value'],83.9)
        self.assertEqual(history[0]['sourceId'],'anthropic-haiku-20261007')
        self.assertFalse(any(r['model_id']==mid for r in data['charts'][bid]['rows']))
        c=data['report_comparisons'][mid][bid];self.assertEqual(c['valueStatus'],'not_reported')
        self.assertIsNone(c['rows'][0]['display_value']);self.assertEqual(c['sourceId'],'anthropic-sonnet-system-card-20260928')
        ref=c['supplementaryComparisons'][0]
        self.assertEqual(ref['sourceId'],'anthropic-haiku-20261007')
        self.assertEqual([r['display_value'] for r in ref['rows']],[72.4,15.7,48.9,83.9])
        self.assertTrue(all(not r['plot_eligible'] for r in ref['rows']))
        queue,_=build_review(data,self.updates);m=next(m for m in queue['models'] if m['modelId']==mid)
        pair=next(p for p in m['pairs'] if p['benchmarkId']==bid)
        self.assertEqual(pair['reportStatus'],'source_not_reported');self.assertEqual(pair['status'],'reviewed')
        script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const data=JSON.parse(fs.readFileSync(0,'utf8')),html=fs.readFileSync('web/model-evals/index.html','utf8');
const elements={},ctx={data,ModelEvalRanking:require('./web/model-evals/ranking.js'),$:id=>elements[id]??(elements[id]={})};vm.createContext(ctx);
vm.runInContext(html.slice(html.indexOf('const esc='),html.indexOf("$('companies').addEventListener")),ctx);
vm.runInContext("company='Anthropic';render()",ctx);
const mid='official-reviewed:claude-sonnet-5-5',bid='reviewed-202610:os21-offline';
const button=[...elements.comparison.innerHTML.matchAll(/<button class="score-cell .*?<\/button>/g)].map(m=>m[0]).find(s=>s.includes('data-model="'+mid+'"')&&s.includes('data-benchmark="'+bid+'"'));
assert.ok(button);assert.ok(button.includes('<span>Not reported</span>'));assert.equal(button.includes('83.9'),false);
const selected=ctx.ModelEvalRanking.selectRanking(data,bid,mid);assert.equal(selected.own,null);assert.equal(selected.reports.length,0);assert.equal(selected.official.length,0);
vm.runInContext("focusModel='"+mid+"';selected='"+bid+"';drawPanel()",ctx);
assert.ok(elements.scores.innerHTML.includes('Not reported in Sonnet'));assert.equal(elements.scores.innerHTML.includes('>83.9%<'),false);
const full=ctx.ModelEvalRanking.selectRanking(data,'reviewed-202610:os21-partial',mid);assert.equal(full.own.display_value,80.1);
'''
        subprocess.run(['node','-e',script],input=json.dumps(data),text=True,cwd=ROOT,check=True)

    def test_sonnet_final_source_coverage_and_cursor_series_are_complete(self):
        import re
        from build_model_eval_review import build_review
        mid='official-reviewed:claude-sonnet-5-5';cs=self.updates['reportComparisons'][mid]
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-25.json').read_text())
        coverage=json.loads((ROOT/e['sourceCoverageReceipt']).read_text())
        self.assertEqual(coverage['pages'],148);self.assertEqual(len(coverage['figures']),88)
        self.assertEqual(sum(bool(f['exclusion']) for f in coverage['figures']),1)
        self.assertEqual(len(coverage['capabilitySummaryCellChecks']),44)
        for f in coverage['figures']:
            self.assertTrue(f['evidence'] or f['exclusion'])
            for ref in f['evidence']:
                c=cs[ref['benchmarkId']]
                if ref['kind']=='supplement':c=next(s for s in c['supplementaryComparisons'] if s['id']==ref['supplementId'])
                token=f['figure'].split(' ',1)[1]
                self.assertRegex(c['source_table_label'],r'(?<![\d.])'+re.escape(token)+r'(?![\w.])')
        curve=next(s for s in cs['reviewed-202610:cursor']['supplementaryComparisons'] if s['id']=='system-card-cursor-curve')
        self.assertEqual(len(curve['rows']),28);self.assertEqual(len({r['name'] for r in curve['rows']}),6)
        self.assertEqual(sum(r['display_value'] is not None for r in curve['rows']),4)
        self.assertEqual([r['display_value'] for r in curve['rows'] if r.get('model_id')==mid],[None,39.2,47.8,53.1,55.5])
        self.assertEqual(len([r for r in curve['rows'] if r['name']=='Grok 4.7']),3)
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
        data=apply_updates(self.data,self.updates);queue,_=build_review(data,self.updates);m=next(m for m in queue['models'] if m['modelId']==mid)
        self.assertEqual((m['status'],m['sourceCoverageStatus'],m['reviewedPairs'],m['totalPairs']),('reviewed','complete',260,260))
        self.assertEqual(coverage['primaryComparisons'],len(cs));self.assertEqual(coverage['supplementaryComparisons'],sum(len(c.get('supplementaryComparisons',[])) for c in cs.values()))
        self.assertFalse(m['discoveredMetrics'])


    def test_sol_luna_source_cohorts_and_health_fields_are_not_backfilled(self):
        pg='reviewed-20261025g:'
        for mid,name,gore,adjusted,raw,length in [
            ('official-reviewed:gpt-6-sol','GPT-6 Sol',90,53.2,47.1,977),
            ('official-reviewed:gpt-6-luna','GPT-6 Luna',87.6,54.5,50.0,1255),
        ]:
            cs=self.updates['reportComparisons'][mid]
            own=lambda b:next(r for r in cs[b]['rows'] if r.get('model_id')==mid)
            self.assertEqual(len(cs[pg+'production-gore']['rows']),7)
            self.assertEqual(own(pg+'production-gore')['display_value'],gore)
            self.assertEqual(len(cs[pg+'agentic-age']['rows']),4)
            vision=cs[pg+'vision-hate']['rows']
            self.assertEqual(len(vision),6)
            self.assertNotIn('GPT-6 Astra',[r['name'] for r in vision])
            self.assertEqual(vision[-1]['source_column'],'Gpt-6 Luna')
            self.assertEqual([r['display_value'] for r in cs[pg+'dynamic-selfharm']['rows']], [97.5,86.8,85.6,90.5,98.9,97.3,92.4])
            ci=cs[pg+'jailbreak-bio-high']['rows'][3]
            self.assertEqual((ci['display_value'],ci['source_confidence_interval']),(85.8,[81.8,88.9]))
            a=own('reviewed-202610:health');r=own('reviewed-20261025:health-openai-raw')
            self.assertEqual((a['display_value'],r['display_value'],a['source_mean_response_characters']),(adjusted,raw,length))
            self.assertEqual(a['source_full_cell'],r['source_full_cell'])
            self.assertEqual((a['source_adjusted_score'],a['source_raw_score']),(adjusted,raw))
            for c in cs.values():
                self.assertEqual(c['publishedAt'],'2026-09-22')
                self.assertEqual([r['name'] for r in c['rows'] if r.get('model_id')==mid],[name])
                self.assertTrue(all(r.get('model_id') in [None,mid] for r in c['rows']))
            self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'in_progress')
        sol=self.updates['reportComparisons']['official-reviewed:gpt-6-sol']
        self.assertEqual(sol[pg+'prompt-injection-indirect']['rows'][5]['display_text'],'99.050%')

    def test_sol_luna_unlabeled_factuality_excludes_later_reference_and_keeps_boards_separate(self):
        data=apply_updates(self.data,self.updates);mid='official-reviewed:gpt-6-sol';bid='reviewed-202610:factuality'
        self.assertTrue(any(r['model_id']==mid and r['benchmark_id']==bid and r['display_value']==11.4 for r in data['observations']))
        self.assertFalse(any(r['model_id']==mid for r in data['charts'][bid]['rows']))
        c=data['report_comparisons'][mid][bid]
        self.assertTrue(all(r['display_value'] is None for r in c['rows']))
        later=c['supplementaryComparisons'][0]
        self.assertEqual(later['publishedAt'],'2026-09-29')
        self.assertEqual([r['display_value'] for r in later['rows']],[7.7,11.4])
        self.assertTrue(all(not r['plot_eligible'] for r in later['rows']))
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
for(const mid of ['official-reviewed:gpt-6-sol','official-reviewed:gpt-6-luna']){
 let s=rank(d,'reviewed-202610:factuality',mid);
 assert.equal(s.reports.length,0);assert.equal(s.exceptions.length,5);assert.equal(s.official.length,0);
 s=rank(d,'reviewed-202610:health-pro',mid);
 assert.equal(s.reports.length,7);assert.equal(s.official.length,7);
 assert.ok(s.official.every(r=>!['GPT-6 Sol','GPT-6 Luna'].includes(r.name)));
 for(const bid of ['reviewed-202610:health','reviewed-20261025:health-openai-raw','reviewed-20261025g:vision-hate']){
  s=rank(d,bid,mid);assert.equal(s.official.length,0);
 }
}
'''
        subprocess.run(['node','-e',script],input=json.dumps(data),text=True,cwd=ROOT,check=True)

    def test_batch26_receipt_covers_original_columns_and_separate_dates(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-26.json').read_text())
        self.assertEqual((len(e['metrics']),len(e['supplements'])),(96,1))
        self.assertEqual(e['sourcePublicationDate'],'2026-09-22')
        self.assertEqual(e['summary']['primaryCells'],576)
        self.assertEqual((e['summary']['numericComparisons'],e['summary']['coverageComparisons']),(88,8))
        self.assertEqual(len(e['sourceChecks']),238)
        self.assertEqual(sum(c['status']=='matched_page_ocr_and_visual' for c in e['sourceChecks']),7)
        for item in e['metrics']+e['supplements']:
            c=self.updates['reportComparisons'][item['modelId']][item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])


    def test_sol_luna_alignment_uses_revised_source_and_separate_outcomes(self):
        p='reviewed-20261025h:'
        for mid in ['official-reviewed:gpt-6-sol','official-reviewed:gpt-6-luna']:
            cs=self.updates['reportComparisons'][mid]
            self.assertEqual([r['display_value'] for r in cs[p+'warnings']['rows']],[17.4,64.4,68.2,42.4,76.5])
            self.assertEqual([r['name'] for r in cs[p+'warnings']['rows']],['GPT-6 Astra','GPT-6 Sol','GPT-5.6 Sol','GPT-6 Luna','GPT-5.6 Luna'])
            self.assertIn('September 22 revised',cs[p+'warnings']['setting'])
            self.assertEqual([r['display_value'] for r in cs[p+'autoreview-attempt']['rows']],[0,0,7.3,0.3,4.3])
            self.assertEqual([r['display_value'] for r in cs[p+'autoreview-success']['rows']],[0,0,0.3,0,0.3])
            h=cs[p+'honeypot-legitimate']
            self.assertEqual([r['display_value'] for r in h['rows']],[1.3,0,0.3,0,None])
            self.assertFalse(h['rows'][-1]['plot_eligible'])
            self.assertIn('displayed precision',h['rows'][1]['source_numeric_basis'])
            self.assertEqual(cs[p+'honeypot-failed-attempt']['rows'][2]['display_value'],6.6)
            self.assertEqual(cs[p+'honeypot-success']['rows'][2]['display_value'],53.0)
            self.assertEqual([r['display_value'] for r in cs['reviewed-202610:search']['rows']],[1.50,4.92,77.46,28.67,78.25])
            self.assertEqual(cs[p+'agent-board-engaged']['rows'][0]['display_value'],83.54)
            self.assertEqual(cs[p+'agent-board-misaligned']['rows'][0]['display_value'],51.90)
            self.assertEqual(cs[p+'agent-board-no-action']['rows'][0]['display_value'],31.65)
            self.assertEqual(cs[p+'agent-board-engaged']['rows'][-1]['source_discovery_rate'],'76%')
        # Later report results remain a different experiment, not replacements.
        later=self.updates['reportComparisons']['official-reviewed:gpt-6.1-sol'][p+'honeypot-legitimate']
        self.assertEqual(next(r for r in later['rows'] if r['name']=='GPT-6 Sol')['display_value'],0.1)
        self.assertEqual(later['publishedAt'],'2026-09-29')

    def test_sol_codex_cohorts_keep_counts_and_original_traffic_reference(self):
        p='reviewed-20261025h:';mid='official-reviewed:gpt-6-sol';cs=self.updates['reportComparisons'][mid]
        for key,n,values,counts in [
            ('codex-severe-all',50319,[0.131,0.083,0.058],[66,42,29]),
            ('codex-severe-unaware',43481,[0.113,0.071,0.046],[49,31,20]),
            ('codex-awareness',50336,[2.56,4.76,8.83,0.75],[1287,2394,4446,379]),
        ]:
            rows=cs[p+key]['rows']
            self.assertEqual([r['display_value'] for r in rows],values)
            self.assertEqual([r['source_count'] for r in rows],counts)
            self.assertTrue(all(r['source_denominator']==n for r in rows))
            self.assertTrue(all('endpoints not printed' in r['source_confidence_method'] for r in rows))
            self.assertNotIn('GPT-6 Luna',[r['name'] for r in rows])
        reference=cs[p+'codex-awareness']['rows'][-1]
        self.assertEqual(reference['name'],'Original traffic')
        self.assertEqual(reference['source_role'],'mixed-model original-traffic reference')
        self.assertNotIn('model_id',reference)
        self.assertEqual([r['display_value'] for r in cs[p+'codex-mild-all']['rows']],[19.67,14.80])
        self.assertEqual(cs[p+'codex-mild-exfiltration']['rows'][1]['display_text'],'0.433%')
        self.assertEqual(cs[p+'codex-severe-outbound-prompt-injection']['rows'][1]['source_count'],0)
        self.assertFalse(any(b.startswith(p+'codex-') for b in self.updates['reportComparisons']['official-reviewed:gpt-6-luna']))
        self.assertNotIn('49,650',self.updates['benchmarks'][p+'codex-severe-all']['summary'])
        self.assertIn('49,650',self.updates['reportComparisons']['official-reviewed:gpt-6.1-sol'][p+'codex-severe-all']['setting'])
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:gpt-6-sol',p='reviewed-20261025h:';
let s=rank(d,p+'codex-severe-all',mid);assert.equal(s.reports.length,3);assert.equal(s.official.length,0);
assert.equal(s.reports.find(r=>r.model_id===mid).display_value,0.083);
s=rank(d,p+'codex-awareness',mid);assert.equal(s.reports.length,4);assert.ok(s.reports.every(r=>r.rank===null));
assert.equal(s.reports.at(-1).name,'Original traffic');assert.equal(s.official.length,0);
s=rank(d,p+'honeypot-legitimate',mid);assert.equal(s.reports.length,4);assert.equal(s.exceptions.length,1);
assert.equal(s.exceptions[0].name,'GPT-5.6 Luna');assert.equal(s.official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_batch27_receipts_preserve_source_columns_versions_and_counts(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-27.json').read_text())
        self.assertEqual(len(e['metrics']),45);self.assertEqual(e['summary']['primaryCells'],173)
        self.assertEqual(len(e['labelChecks']),121)
        self.assertEqual(sum(c['countRoundedPercentageMatches'] is True for c in e['labelChecks']),67)
        self.assertEqual(len(e['benchmarkMetadataChanges']),23)
        self.assertIn('revised auto-review',e['sourceVersionNotice'])
        for item in e['metrics']:
            mid,b=item['modelId'],item['benchmarkId'];c=self.updates['reportComparisons'][mid][b]
            self.assertEqual(c['publishedAt'],'2026-09-22')
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertEqual(sum(r.get('model_id')==mid for r in c['rows']),1)
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][b]['coreEligible'])


    def test_sol_monitorability_separates_length_bins_guidance_and_recall(self):
        mid='official-reviewed:gpt-6-sol';p='reviewed-20261025i:';cs=self.updates['reportComparisons'][mid]
        c=cs[p+'cot-control']
        self.assertEqual([r['display_value'] for r in c['rows']],[1.7,16.1,60.9,23.2])
        self.assertIn('750–1,250',c['setting'])
        curves=c['supplementaryComparisons'][0]['rows']
        self.assertEqual(len(curves),48)
        self.assertTrue(all(r['display_value'] is None and not r['plot_eligible'] for r in curves))
        self.assertEqual({r['name'] for r in curves},{'GPT-5.5','GPT-5.6 Sol','GPT-6 Astra','GPT-6 Sol'})
        for key in ['side-task','action','cot','full','p0','p0-p1']:
            c=cs[p+'sabotage-'+key]
            self.assertEqual(len(c['rows']),4);self.assertTrue(all(r['display_value'] is None for r in c['rows']))
            curves=c['supplementaryComparisons'][0]['rows']
            self.assertEqual(len(curves),8)
            self.assertEqual(sum('Task-guided' in r['setting'] for r in curves),4)
            self.assertEqual(sum('Unguided' in r['setting'] for r in curves),4)
            self.assertTrue(all(not r['plot_eligible'] for r in curves))
        for key in ['baseline','aware','hide']:
            rows=cs[p+'honeypot-cot-'+key]['rows']
            self.assertEqual([(r['name'],r['display_value']) for r in rows],[('GPT-6 Sol',100)])
        full=cs[p+'honeypot-full']
        self.assertEqual([r['name'] for r in full['rows']],['GPT-6 Sol','GPT-6 Astra'])
        self.assertEqual([r['display_value'] for r in full['rows']],[100,100])
        self.assertEqual([r['display_value'] for r in full['supplementaryComparisons'][0]['rows']],[100,100,100])
        self.assertTrue(all(r['name']=='GPT-6 Sol' for r in full['supplementaryComparisons'][0]['rows']))
        self.assertTrue(all(r['display_value'] is None for r in cs[p+'honeypot-tokens']['supplementaryComparisons'][0]['rows']))

    def test_sol_math_monitoring_does_not_turn_zero_evasion_into_zero_completion(self):
        mid='official-reviewed:gpt-6-sol';p='reviewed-20261025i:';cs=self.updates['reportComparisons'][mid]
        for key in ['math-cot','math-full','math-joint']:
            self.assertEqual([r['display_value'] for r in cs[p+key]['rows']],[0,0,0])
        completion=cs[p+'math-completion']
        self.assertTrue(all(r['display_value'] is None for r in completion['rows']))
        bars=completion['supplementaryComparisons'][0]['rows']
        self.assertEqual(len(bars),48);self.assertEqual(len({r['source_column'] for r in bars}),48)
        self.assertTrue(all(r['display_value'] is None and not r['plot_eligible'] for r in bars))
        action=cs[p+'math-action'];self.assertEqual(action['valueStatus'],'no_single_score')
        self.assertTrue(all(r['display_value'] is None for r in action['rows']))
        points=action['supplementaryComparisons'][0]['rows']
        self.assertEqual([r['display_value'] for r in points],[.2,0,.2]);self.assertTrue(all(not r['plot_eligible'] for r in points))
        data=apply_updates(self.data,self.updates)
        self.assertFalse(any(r['model_id']==mid for r in data['charts'][p+'math-action']['rows']))
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const d=JSON.parse(fs.readFileSync(0,'utf8')),rank=require('./web/model-evals/ranking.js').selectRanking;
const mid='official-reviewed:gpt-6-sol',p='reviewed-20261025i:';
let s=rank(d,p+'math-joint',mid);assert.equal(s.reports.length,3);assert.ok(s.reports.every(r=>r.display_value===0));
for(const key of ['math-action','math-completion','sabotage-action']){
 s=rank(d,p+key,mid);assert.equal(s.reports.length,0);assert.equal(s.official.length,0);
}
s=rank(d,p+'honeypot-cot-aware',mid);assert.equal(s.reports.length,1);assert.equal(s.reports[0].display_value,100);assert.equal(s.official.length,0);
'''
        subprocess.run(['node','-e',script],input=json.dumps(data),text=True,cwd=ROOT,check=True)

    def test_batch28_monitorability_receipt_and_explicit_luna_omission(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-28.json').read_text());mid=e['modelId']
        self.assertEqual((len(e['metrics']),len(e['supplements'])),(17,11))
        self.assertEqual((e['summary']['primaryCells'],e['summary']['supplementaryCells']),(49,153))
        self.assertEqual((e['summary']['numericComparisons'],e['summary']['coverageComparisons']),(8,9))
        self.assertEqual(e['coverage']['figures'],list(range(71,79)))
        self.assertEqual([x['occurrences'] for x in e['independentChecks']['renderedPageOCR']],[2,2,1,2])
        self.assertEqual([t['table'] for t in e['coverage']['excludedQualitativeTables']],[31,32])
        self.assertIn('explicitly omits GPT-6 Luna',e['coverage']['lunaExclusion'])
        self.assertFalse(any(b.startswith('reviewed-20261025i:') for b in self.updates['reportComparisons']['official-reviewed:gpt-6-luna']))
        for item in e['metrics']+e['supplements']:
            c=self.updates['reportComparisons'][mid][item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(c['publishedAt'],'2026-09-22')
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][item['benchmarkId']]['coreEligible'])
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'in_progress')


    def test_sol_luna_preparedness_preserves_source_cohorts_variants_and_units(self):
        p='reviewed-20261025j:';sol='official-reviewed:gpt-6-sol';luna='official-reviewed:gpt-6-luna'
        cs=self.updates['reportComparisons'];high=cs[sol][p+'bio-virology']
        self.assertEqual([(r['name'],r['display_value']) for r in high['rows']],[('GPT-6 Sol',50.6),('GPT-6 Luna',49.1)])
        self.assertIn('refusal-adjusted',high['setting'])
        self.assertEqual(high['source_threshold']['source_value'],'31%')
        self.assertEqual(cs[sol][p+'bio-tacit']['setting'],'cons@32 · refusal-adjusted capability estimate')
        for key,values in [('bio-aav',[.529,.528,.534]),('bio-shp2',[.30,.40,.273]),('bio-cell-entry',[.43,.45,.463]),('bio-phage',[11.35,12.58,12.9])]:
            c=cs[sol][p+key];self.assertEqual([r['display_value'] for r in c['rows']],values)
            self.assertNotIn(p+key,cs[luna]);self.assertTrue(all('%' not in r['display_text'] for r in c['rows']))
            if key in ['bio-cell-entry','bio-phage']:
                r=c['rows'][1];self.assertEqual(r['name'],'GPT-6 Astra (helpful-only)')
                self.assertEqual(r['source_column'],'GPT-6 Astra');self.assertTrue(r['source_value'].endswith('*'));self.assertNotIn('model_id',r)
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict'),rank=require('./web/model-evals/ranking.js').selectRanking;
const d=JSON.parse(fs.readFileSync(0,'utf8')),mid='official-reviewed:gpt-6-sol',p='reviewed-20261025j:';
let s=rank(d,p+'bio-phage',mid);assert.equal(s.reports[0].name,'GPT-5.6 Sol');assert.equal(s.reports[2].display_value,12.9);
assert.equal(s.official.length,0);assert.equal(s.reports.length,3);
s=rank(d,p+'bio-cell-entry',mid);assert.equal(s.reports[1].name,'GPT-6 Astra (helpful-only)');
assert.ok(!s.reports.some(r=>r.name==='GPT-6 Astra'));
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_sol_luna_sandbox_counts_and_safe_response_fractions(self):
        p='reviewed-20261025j:'
        for mid in ['official-reviewed:gpt-6-sol','official-reviewed:gpt-6-luna']:
            cs=self.updates['reportComparisons'][mid];c=cs[p+'sandbox-overall']
            self.assertEqual([r['display_value'] for r in c['rows']],[45.5,4.5,4.5,4.5])
            self.assertEqual([r['source_value'] for r in c['rows']],['45.5','1/22','1/22','1/22'])
            for key,n,counts in [('overall',22,[10,1,1,1]),('runtime',5,[4,1,1,1]),('parser',14,[5,0,0,0]),('egress',3,[1,0,0,0])]:
                rows=cs[p+'sandbox-'+key]['rows'];self.assertEqual([r['source_count'] for r in rows],counts)
                for r in rows:
                    self.assertEqual(r['source_denominator'],n)
                    self.assertEqual(r['display_value'],round(r['source_count']/n*100,1))
            rows=cs[p+'safeguard-cyber-semisynthetic']['rows']
            self.assertEqual(len(rows),6);self.assertEqual([r['display_value'] for r in rows],[96.3,98.5,None,99.7,98.4,98.7])
            self.assertEqual(rows[2]['name'],'GPT-5.6 Luna');self.assertEqual(rows[2]['value_status'],'not_reported')
            self.assertEqual(rows[2]['source_value'],'—');self.assertFalse(rows[2]['plot_eligible'])
            for r in cs[p+'safeguard-bio-benign']['rows']:self.assertAlmostEqual(float(r['source_value'])*100,r['display_value'])
            self.assertTrue(all(r['name']!='GPT-6.1 Sol' for r in rows))

    def test_sol_luna_cyber_and_ai_results_do_not_mix_token_budgets_or_metrics(self):
        p='reviewed-20261025j:'
        expected={'exploitbench':[100,81.7,43.4,78.5],'internal-port':[31.5,5.5,0,3.5],'sec-pro':[85.4,66.3,34.2,79.1],'exploitgym':[42.4,22.1,11.6,30.3]}
        for mid in ['official-reviewed:gpt-6-sol','official-reviewed:gpt-6-luna']:
            cs=self.updates['reportComparisons'][mid]
            for key,values in expected.items():
                c=cs[p+key];self.assertEqual([r['display_value'] for r in c['rows']],values)
                self.assertEqual([r['name'] for r in c['rows']],['GPT-6 Astra','GPT-6 Sol','GPT-6 Luna','GPT-5.6 Sol'])
                s=c['supplementaryComparisons'][0];self.assertEqual(len(s['rows']),4)
                self.assertTrue(all(r['display_value'] is None and r['plot_eligible'] is False for r in s['rows']))
                self.assertIn('output-token',s['title']);self.assertFalse(self.updates['modelBenchmarkAudits'][mid][p+key]['coreEligible'])
            self.assertEqual([r['display_value'] for r in cs[p+'debugging']['rows']],[78.05,64.20,68.32,46.62,50.8])
            self.assertEqual([r['display_value'] for r in cs[p+'kernelgen']['rows']],[66.72,38.12,61.08,21.83,22.4])
            self.assertIn('rubric reward',cs[p+'kernelgen']['setting'])
        for mid in ['official-reviewed:gpt-6-sol','official-reviewed:gpt-6-luna','official-reviewed:gpt-6.1-sol']:
            a=self.updates['modelBenchmarkAudits'][mid][p+'exploitbench']
            self.assertEqual(a['status'],'protocol_unverified');self.assertIn('confirms ACE',a['note'])

    def test_batch29_receipt_matches_all_source_cells_and_retains_omissions(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-29.json').read_text())
        self.assertEqual((len(e['metrics']),len(e['supplements'])),(44,8))
        self.assertEqual((e['summary']['primaryCells'],e['summary']['supplementaryCells']),(184,32))
        self.assertEqual(len(e['tableCellChecks']),56);self.assertTrue(all(r['htmlExactMatch'] and r['pdfDigitsMatch'] for r in e['tableCellChecks']))
        self.assertEqual(len(e['figureLabelChecks']),42)
        self.assertEqual(e['independentChecks']['figureOCRMatches'],26)
        self.assertEqual(len(e['publicSourceChecks']),5);self.assertEqual(len(e['benchmarkMetadataChanges']),5)
        self.assertEqual(e['coverage']['figures'],list(range(79,86)));self.assertIn('not required',e['coverage']['lunaCriticalOmission'])
        for item in e['metrics']+e['supplements']:
            mid=item['modelId'];c=self.updates['reportComparisons'][mid][item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256']);self.assertEqual(c['publishedAt'],'2026-09-22')
            self.assertEqual(sum(r.get('model_id')==mid for r in c['rows']),1)
        for mid in ['official-reviewed:gpt-6-sol','official-reviewed:gpt-6-luna']:
            self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'in_progress')

    def test_partial_release_comparisons_have_no_rank_and_do_not_count_as_reviewed(self):
        from build_model_eval_review import build_review
        data=apply_updates(self.data,self.updates);queue,_=build_review(data,self.updates)
        mids=['official-reviewed:gpt-6-sol','official-reviewed:gpt-6-luna']
        partial=0
        for model in queue['models']:
            if model['modelId'] not in mids:continue
            for pair in model['pairs']:
                c=data['report_comparisons'][model['modelId']].get(pair['benchmarkId'])
                if c and c.get('comparisonStatus')=='partial':
                    partial+=1;self.assertEqual(pair['reportStatus'],'comparison_partial');self.assertEqual(pair['status'],'in_progress')
        self.assertEqual(partial,7)
        script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict'),rank=require('./web/model-evals/ranking.js').selectRanking;
const d=JSON.parse(fs.readFileSync(0,'utf8')),sol='official-reviewed:gpt-6-sol',luna='official-reviewed:gpt-6-luna',p='reviewed-202610:';
let s=rank(d,p+'deepswe',sol);assert.equal(s.reportRankable,false);assert.ok(s.reports.every(r=>r.rank===null));
assert.deepEqual(s.reports.map(r=>r.display_value),[68.8,69.9,66.6]);
s=rank(d,p+'os20-offline',luna);assert.equal(s.reports.length,2);assert.ok(s.reports.every(r=>r.rank===null));
assert.equal(s.official.length,2);assert.equal(s.official[0].name,'Claude Opus 5');assert.equal(s.official[0].display_value,70.19);assert.equal(s.official[0].rank,1);
s=rank(d,p+'automation',luna);assert.equal(s.reports.length,0);assert.ok(s.official.some(r=>r.model_id===luna&&r.display_value===20.7));
s=rank(d,p+'automation',sol);assert.equal(s.reportRankable,true);assert.equal(s.reports[0].display_value,33.2);
'''
        subprocess.run(['node','-e',script],input=json.dumps(data),text=True,cwd=ROOT,check=True)

    def test_release_table_retains_fallback_identity_and_never_backfills_missing_scores(self):
        p='reviewed-202610:';sol='official-reviewed:gpt-6-sol';luna='official-reviewed:gpt-6-luna';cs=self.updates['reportComparisons']
        rows=cs[sol][p+'automation']['rows']
        self.assertEqual([r['display_value'] for r in rows],[33.2,30.3,26.9,31.4])
        self.assertEqual([r['setting'] for r in rows],['xhigh effort','low effort','max effort','max effort'])
        self.assertEqual(rows[-1]['name'],'Claude Fable 5.1 w/ Opus 5 Fallback');self.assertIn('fallback cost not reported',rows[-1]['source_cost'])
        self.assertTrue(all(r['display_value'] is None for r in cs[luna][p+'automation']['rows']))
        self.assertTrue(all(r['display_value'] is None for r in cs[sol][p+'frontier']['rows']))
        os=cs[luna][p+'os20-offline']['rows']
        self.assertEqual([r['display_value'] for r in os],[60.5,60.3,None,None])
        self.assertEqual(os[2]['value_status'],'source_unavailable');self.assertNotEqual(os[2]['value_status'],'not_reported')
        self.assertNotIn(p+'frontier',cs[luna])

    def test_osworld_legacy_snapshot_and_ale_version_are_isolated(self):
        b='reviewed-202610:os20-offline';s=self.updates['leaderboardSnapshots'][b]
        self.assertEqual(len(s['rows']),11)
        self.assertEqual({r['source_release'] for r in s['rows']},{'v2026.08.08'})
        self.assertEqual({r['source_subset'] for r in s['rows']},{'offline'})
        self.assertEqual({r['source_metric'] for r in s['rows']},{'partialScore'})
        medium=next(r for r in s['rows'] if r['name']=='Claude Opus 5' and r['effort']=='medium')
        self.assertEqual(medium['display_value'],60.26);self.assertNotEqual(medium['display_value'],27.13)
        self.assertFalse(any(r['name'] in ['GPT-6 Sol','GPT-6 Luna'] for r in s['rows']))
        sol='official-reviewed:gpt-6-sol';new='reviewed-20261026:ale-v1-reported-score'
        self.assertFalse(any(r['model_id']==sol and r['benchmark_id']=='reviewed-202610:agents-last' for r in self.updates['observations']))
        r=next(r for r in self.updates['observations'] if r['model_id']==sol and r['benchmark_id']==new)
        self.assertEqual(r['display_value'],56.4);self.assertIn('V1',self.updates['benchmarks'][new]['name'])
        self.assertFalse(self.updates['modelBenchmarkAudits'][sol][new]['coreEligible'])
        self.assertIn('version',self.updates['benchmarks']['reviewed-202610:agents-last']['name'])

    def test_batch30_source_receipt_and_partial_status_validation(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-30.json').read_text())
        self.assertEqual((len(e['metrics']),e['summary']['partialComparisons'],e['summary']['primaryCells']),(8,7,25))
        self.assertEqual(len(e['observationCorrections']),1)
        self.assertEqual(e['observationCorrections'][0]['before']['display_value'],e['observationCorrections'][0]['after']['display_value'])
        for item in e['metrics']:
            c=self.updates['reportComparisons'][item['modelId']][item['benchmarkId']]
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']]);self.assertEqual(item['sha256'],c['source_table_sha256'])
        bad=copy.deepcopy(self.updates)
        c=bad['reportComparisons']['official-reviewed:gpt-6-luna']['reviewed-202610:automation'];c.pop('displayCoverage')
        with self.assertRaisesRegex(ValueError,'visible coverage note'):apply_updates(copy.deepcopy(self.data),bad)
        c['comparisonStatus']='unverified_complete'
        with self.assertRaisesRegex(ValueError,'Unknown source comparison'):apply_updates(copy.deepcopy(self.data),bad)

    def test_ranking_script_url_matches_current_code(self):
        expected=hashlib.sha256((ROOT/'web/model-evals/ranking.js').read_bytes()).hexdigest()[:12]
        self.assertIn(f'<script src="ranking.js?v={expected}">',(ROOT/'web/model-evals/index.html').read_text())

    def test_opus_release_preserves_source_cohorts_and_effort_choices(self):
        mid='official-reviewed:claude-opus-5-5';cs=self.updates['reportComparisons'][mid];p='reviewed-202610:'
        self.assertTrue(set(json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-31.json').read_text())['metrics'][i]['benchmarkId'] for i in range(10)).issubset(cs))
        expected={
            'family:terminal-bench-4':[66.4,55.8,52.3,57.9,37.3],
            p+'frontier':[54.4,50.3,48.0,53.3,47.5],p+'cursor':[57.8,51.8,46.6,None,41.7],
            p+'gdp-aa':[1846,1735,1708,1542,1588],p+'automation':[40,31.4,26.9,41.4,28.8],
            p+'hle-tools':[67.7,65.6,63.6,57.2,None],p+'science':[58.7,52.6,29,64.6,22.4],
            p+'os21-partial':[81.8,80.7,74,None,None],p+'chart-tools':[89,88.4,83.4,None,None]}
        for bid,values in expected.items():
            c=cs[bid];self.assertEqual([r['display_value'] for r in c['rows']],values)
            self.assertEqual([r['source_column'] for r in c['rows']],['Opus 5.5','Fable 5.1','Opus 5','GPT-6 Astra','GPT-5.6 Sol'])
            self.assertEqual(sum(r.get('model_id')==mid for r in c['rows']),1)
        self.assertIn('xhigh',cs['family:terminal-bench-4']['rows'][0]['setting'])
        self.assertIn('High effort',cs['family:terminal-bench-4']['rows'][3]['setting'])
        self.assertEqual(cs[p+'automation']['rows'][1]['name'],'Claude Fable 5.1 w/ Opus 5 Fallback')
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'in_progress')

    def test_opus_release_curves_keep_exact_values_costs_and_no_fallback(self):
        mid='official-reviewed:claude-opus-5-5';cs=self.updates['reportComparisons'][mid];p='reviewed-202610:'
        supplements=[s for c in cs.values() for s in c.get('supplementaryComparisons',[]) if s['sourceId']=='anthropic-opus-20260922']
        self.assertEqual(len(supplements),6);self.assertEqual(sum(len(s['rows']) for s in supplements),130)
        self.assertTrue(all(s['evidenceOnly'] and all(not r['plot_eligible'] for r in s['rows']) for s in supplements))
        rows=cs[p+'frontier']['supplementaryComparisons'][0]['rows']
        self.assertEqual(next(r['display_value'] for r in rows if r.get('model_id')==mid and r['source_effort']=='Med'),54.64)
        peer=next(r for r in rows if r['name']=='Claude Opus 5' and r['source_effort']=='Xhigh')
        self.assertEqual((peer['source_value'],peer['display_value']),('43.65',43.65))
        self.assertTrue(all('without fallback' in r['setting'] for r in cs[p+'automation']['supplementaryComparisons'][0]['rows'] if r.get('model_id')==mid))
        w=cs['reviewed-20261025:wandr-frozen-opus46'];self.assertEqual([r['display_value'] for r in w['rows']],[72.3,68.7,67.2])
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-31.json').read_text())
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']])
            self.assertEqual(item['sha256'],c['source_table_sha256'])

    def test_opus_report_and_official_ranks_remain_independent(self):
        script=r'''
const assert=require('node:assert/strict'),fs=require('node:fs'),rank=require('./web/model-evals/ranking.js').selectRanking;
const d=JSON.parse(fs.readFileSync(0,'utf8')),mid='official-reviewed:claude-opus-5-5',p='reviewed-202610:';
let s=rank(d,'family:terminal-bench-4',mid);
assert.equal(s.reports.find(r=>r.model_id===mid).display_value,66.4);
assert.equal(s.official.find(r=>r.model_id===mid).display_value,64.85);
s=rank(d,p+'frontier',mid);assert.equal(s.reports.find(r=>r.model_id===mid).display_value,54.4);assert.equal(s.official.find(r=>r.model_id===mid).display_value,54.64);
s=rank(d,p+'automation',mid);assert.equal(s.reports[0].name,'GPT-6 Astra');assert.equal(s.reports.find(r=>r.model_id===mid).rank,2);assert.equal(s.official.find(r=>r.model_id===mid).display_value,42.47);
s=rank(d,p+'gdp-aa',mid);assert.equal(s.reports.find(r=>r.model_id===mid).display_value,1846);assert.equal(s.official.find(r=>r.model_id===mid).display_value,1866.27);
for(const bid of [p+'hle-tools',p+'chart-tools','reviewed-20261025:wandr-frozen-opus46'])assert.equal(rank(d,bid,mid).official.length,0);
s=rank(d,p+'os21-partial',mid);assert.ok(s.official.length>0);assert.ok(!s.official.some(r=>r.model_id===mid));
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_opus_card_preserves_full_summary_cohort_and_version_uncertainty(self):
        mid='official-reviewed:claude-opus-5-5';cs=self.updates['reportComparisons'][mid];q='reviewed-20261025:'
        for bid,values in [(q+'swe-pro',[89.9,79.2,81.2,None]),(q+'swe-multilingual',[93.9,89.5,89.1,None]),(q+'swe-multimodal',[61.4,59.4,54.7,None]),('reviewed-202610:hle-no-tools',[64.4,56.6,60.9,None])]:
            rows=cs[bid]['rows'];self.assertEqual([r['display_value'] for r in rows],values)
            self.assertEqual([r['source_column'] for r in rows],['Claude Opus 5.5','Claude Opus 5','Claude Fable 5.1','GPT-6 Astra'])
            self.assertFalse(rows[-1]['plot_eligible']);self.assertNotIn('model_id',rows[-1])
        for bid in [q+'swe-pro',q+'swe-multimodal','reviewed-202610:deepswe']:
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][bid]['coreEligible'])
        self.assertEqual(cs[q+'frontierswe-v2']['rows'][2]['name'],'Claude Fable 5.1 w/ Opus 5 Fallback')
        self.assertEqual(cs[q+'frontierswe-v2']['rows'][2]['source_column'],'Claude Fable 5.1')

    def test_opus_card_does_not_replace_max_cohorts_with_peaks_or_other_sources(self):
        mid='official-reviewed:claude-opus-5-5';cs=self.updates['reportComparisons'][mid];q='reviewed-20261025:'
        ext=cs[q+'frontier-extended'];self.assertEqual([r['display_value'] for r in ext['rows']],[65.3,63.6,64.9,64.5,63.6])
        self.assertIn('medium',ext['rows'][0]['setting'])
        self.assertEqual(next(s for s in ext['supplementaryComparisons'] if s['id']=='system-card-max-effort')['rows'][0]['display_value'],63.6)
        math=cs['reviewed-20261026:arxivmath-0826-tools'];self.assertEqual([r['display_value'] for r in math['rows']],[96.9,92.1,90.4])
        curve=next(s for s in math['supplementaryComparisons'] if s['id']=='system-card-effort-curve')
        self.assertTrue(any(r['name']=='Claude Fable 5.1' and r['display_value']==93.0 and 'Xhigh' in r['setting'] for r in curve['rows']))
        w=cs[q+'wandr-frozen-opus46'];self.assertEqual(w['rows'][2]['display_value'],67.2)
        release=next(s for s in w['supplementaryComparisons'] if s['id']=='release-effort-curve')
        card=next(s for s in w['supplementaryComparisons'] if s['id']=='system-card-effort-curve')
        self.assertEqual(next(r['display_value'] for r in release['rows'] if r['name']=='Claude Opus 5' and r['source_effort']=='Max'),67.2)
        self.assertEqual(next(r['display_value'] for r in card['rows'] if r['name']=='Claude Opus 5' and r['setting'].startswith('Max')),67.1)
        self.assertNotEqual(release['sourceId'],card['sourceId'])

    def test_batch32_receipt_exact_values_and_unknown_coordinates(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-32.json').read_text());mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual((len(e['metrics']),len(e['supplements']),e['summary']['primaryCells'],e['summary']['supplementaryCells']),(11,13,38,123))
        self.assertEqual(len(e['labelChecks']),90);self.assertTrue(all(r['status'].startswith('matched') for r in e['labelChecks']))
        unknown=[]
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:
                c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
                self.assertTrue(c['evidenceOnly']);self.assertTrue(all(not r['plot_eligible'] for r in c['rows']))
                unknown.extend(r for r in c['rows'] if r['display_value'] is None)
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']]);self.assertEqual(item['sha256'],c['source_table_sha256'])
        self.assertEqual(len(unknown),17);self.assertTrue(all(r['value_status']=='unlabeled_figure' for r in unknown))
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'in_progress')

    def test_opus_draco_rank_and_incompatible_official_protocols(self):
        script=r'''
const assert=require('node:assert/strict'),fs=require('node:fs'),rank=require('./web/model-evals/ranking.js').selectRanking;
const d=JSON.parse(fs.readFileSync(0,'utf8')),mid='official-reviewed:claude-opus-5-5',q='reviewed-20261025:';
let s=rank(d,q+'draco-opus46',mid);assert.deepEqual(s.reports.map(r=>r.display_value),[88.3,87.7,87.4]);assert.equal(s.reports.find(r=>r.model_id===mid).rank,3);assert.equal(s.official.length,0);
s=rank(d,q+'frontier-extended',mid);assert.equal(s.reports.find(r=>r.model_id===mid).display_value,65.3);assert.equal(s.official.find(r=>r.model_id===mid).display_value,65.27);
s=rank(d,q+'program-166-mean',mid);assert.equal(s.reports.find(r=>r.model_id===mid).display_value,91.2);assert.equal(s.official.length,0);
for(const b of ['reviewed-20261026:arxivmath-0826-no-tools','reviewed-20261026:arxivmath-0826-tools',q+'swe-pro',q+'swe-multimodal'])assert.equal(rank(d,b,mid).official.length,0);
s=rank(d,'reviewed-202610:hle-no-tools',mid);assert.equal(s.official.length,9);assert.ok(!s.official.some(r=>r.model_id===mid));
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

    def test_opus_multiagent_conditions_and_source_receipts(self):
        e=json.loads((ROOT/'data/model_eval_evidence/2026-10-26-batch-33.json').read_text());mid=e['modelId'];cs=self.updates['reportComparisons'][mid]
        self.assertEqual((len(e['metrics']),len(e['supplements']),e['summary']['primaryCells'],e['summary']['supplementaryCells']),(10,5,26,48))
        self.assertEqual(len(e['labelChecks']),48);self.assertTrue(all(x['status'].startswith('matched_') for x in e['labelChecks']))
        unknown=[]
        for item in e['metrics']+e['supplements']:
            c=cs[item['benchmarkId']]
            if 'supplementId' in item:
                c=next(s for s in c['supplementaryComparisons'] if s['id']==item['supplementId'])
                self.assertTrue(c['evidenceOnly']);self.assertTrue(all(not r['plot_eligible'] for r in c['rows']))
                unknown.extend(r for r in c['rows'] if r['display_value'] is None)
            self.assertEqual(item['columns'],[[r['source_column'],r['source_value']] for r in c['rows']]);self.assertEqual(item['sha256'],c['source_table_sha256'])
            for r in c['rows']:
                if r['display_value'] is not None:self.assertAlmostEqual(r['display_value'],float(r['source_value'])*100)
            self.assertFalse(self.updates['modelBenchmarkAudits'][mid][item['benchmarkId']]['coreEligible'])
        self.assertEqual(len(unknown),24);self.assertTrue(all(r['value_status']=='unlabeled_figure' for r in unknown))
        draco=cs['reviewed-20261026-opus:draco-multiagent-latency']['supplementaryComparisons'][0]
        self.assertEqual(len(draco['rows']),18);self.assertEqual(sum('0.5×' in r['setting'] for r in draco['rows']),3)

    def test_opus_team_scale_ties_and_figure_disagreement_are_preserved(self):
        mid='official-reviewed:claude-opus-5-5';cs=self.updates['reportComparisons'][mid];p='reviewed-20261026-opus:'
        expected={'knowledge-base':[[45,53,53],[64,66,70],[65,69,71],[68,68,74]],'lean':[[19,16,39],[44,33,66],[55,45,66],[58,53,68]]}
        for task,cohorts in expected.items():
            for n,values in zip([1,10,30,100],cohorts):
                c=cs[p+f'{task}-{n}-agents-24h'];self.assertEqual([r['display_value'] for r in c['rows']],values)
                self.assertIn('Experimental Opus snapshot',c['displaySetup']);self.assertIn('three attempts',c['displaySetup'])
        c=cs[p+'knowledge-base-100-agents-24h']['supplementaryComparisons'][0]
        row=next(r for r in c['rows'] if r['setting'].startswith('10 agents · within 24 hours'))
        self.assertEqual((row['source_value'],row['display_value']),('0.71',71))
        primary=cs[p+'knowledge-base-10-agents-24h'];self.assertEqual(primary['rows'][-1]['source_value'],'0.70');self.assertIn('Cause unspecified',primary['displayCaveat'])
        self.assertEqual(self.updates['modelAudits'][mid]['sourceCoverageStatus'],'in_progress')

    def test_opus_experimental_rankings_never_pool_scales_or_official_runs(self):
        script=r'''
const assert=require('node:assert/strict'),fs=require('node:fs'),rank=require('./web/model-evals/ranking.js').selectRanking;
const d=JSON.parse(fs.readFileSync(0,'utf8')),mid='official-reviewed:claude-opus-5-5',p='reviewed-20261026-opus:';
for(const task of ['knowledge-base','lean'])for(const n of [1,10,30,100]){const s=rank(d,p+task+'-'+n+'-agents-24h',mid);assert.equal(s.reports.length,3);assert.equal(s.official.length,0);}
let s=rank(d,p+'knowledge-base-1-agents-24h',mid);assert.equal(s.reports.filter(r=>r.rank===1).length,2);
s=rank(d,p+'knowledge-base-10-agents-24h',mid);assert.equal(s.reports.find(r=>r.model_id===mid).display_value,70);
for(const k of ['program-multiagent-snapshot','draco-multiagent-latency']){s=rank(d,p+k,mid);assert.equal(s.reports.length,0);assert.equal(s.official.length,0);}
assert.equal(rank(d,'reviewed-20261025:program-166-mean',mid).reports.find(r=>r.model_id===mid).display_value,91.2);
'''
        subprocess.run(['node','-e',script],input=json.dumps(apply_updates(self.data,self.updates)),text=True,cwd=ROOT,check=True)

if __name__ == '__main__':
    unittest.main()

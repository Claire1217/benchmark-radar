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

    def test_newer_elo_snapshot_is_selected_even_when_lower(self):
        data = apply_updates(self.data, self.updates)
        bid = 'reviewed-202610:gdp-aa'
        mid = 'official-reviewed:claude-sonnet-5-5'
        rows = [r for r in data['observations'] if r['model_id'] == mid and r['benchmark_id'] == bid]
        self.assertEqual({r['display_value'] for r in rows}, {1840, 1844})
        chart_row = next(r for r in data['charts'][bid]['rows'] if r['model_id'] == mid)
        self.assertEqual(chart_row['display_value'], 1840)
        self.assertEqual(chart_row['reported_at'], '2026-10-07')

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
        self.assertTrue(all(r['agent'].startswith('SWE-agent') for r in
                            data['leaderboard_snapshots'][p + 'swe-multimodal']['rows']))

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
            observations = [r for r in data['observations'] if r['benchmark_id'] == bid]
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


if __name__ == '__main__':
    unittest.main()

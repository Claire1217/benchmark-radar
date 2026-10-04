from datetime import date, datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from signal_history import annotate_growth, record_values, snapshot_growth, star_window_end, value_at


def ts(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())


class SnapshotTests(unittest.TestCase):
    def test_values_are_stored_sparsely_and_idempotently(self):
        h = {}
        rows = lambda v: [{'id': 'a', 'attention': {'hfPaperUpvotes': v, 'githubStars': None}}]
        record_values(h, rows(5), '2026-08-01')
        record_values(h, rows(5), '2026-08-02')       # unchanged -> not stored
        record_values(h, rows(9), '2026-09-01')
        record_values(h, rows(10), '2026-09-01')      # same day -> replaced
        record_values(h, rows(3), '2026-08-15')       # older than last -> ignored
        self.assertEqual(h, {'a': {'hfPaperUpvotes': [['2026-08-01', 5], ['2026-09-01', 10]]}})

    def test_growth_needs_history_that_reaches_the_window(self):
        series = [['2026-08-01', 5], ['2026-09-01', 10], ['2026-10-01', 30]]
        g = snapshot_growth(series, '2026-10-05')
        self.assertEqual(g['current'], 30)
        self.assertEqual(g['1m'], 20)            # value on 2026-09-05 is 10
        self.assertIsNone(g['3m'])               # history starts 2026-08-01, after 2026-07-07
        self.assertEqual(g['stages']['0-1m'], 20)
        self.assertIsNone(g['stages']['1-3m'])
        self.assertIsNone(snapshot_growth([], '2026-10-05'))
        self.assertIsNone(value_at(series, '2026-07-31'))


class StarEventTests(unittest.TestCase):
    def test_stages_from_star_events_only_for_single_benchmark_repos(self):
        end = '2026-10-04'
        weeks = [{'week': ts('2026-09-27'), 'days': [1, 0, 0, 0, 0, 0, 0], 'total': 1},   # 2026-09-27: +1 (0-1m)
                 {'week': ts('2026-08-02'), 'days': [0, 4, 0, 0, 0, 0, 0], 'total': 4},   # 2026-08-03: +4 (1-3m)
                 {'week': ts('2026-05-03'), 'days': [0, 0, 2, 0, 0, 0, 0], 'total': 2}]   # 2026-05-05: +2 (3-6m)
        stars = {'records': [{'url': 'https://github.com/o/a', 'status': 'complete', 'weeks': weeks}]}
        rows = [{'id': 'a', 'attention': {'githubRepo': 'https://github.com/o/a', 'githubScope': 'benchmark_repo', 'githubStars': 7}},
                {'id': 'shared', 'attention': {'githubRepo': 'https://github.com/o/a', 'githubScope': 'hosting_repo'}}]
        annotate_growth(rows, {}, stars, end, end)
        g = rows[0]['growth']['githubStars']
        self.assertEqual((g['1m'], g['3m'], g['6m']), (1, 5, 7))
        self.assertEqual(g['stages'], {'0-1m': 1, '1-3m': 4, '3-6m': 2})
        self.assertEqual(g['repositoryCreated'], '2026-05-03')
        self.assertNotIn('growth', rows[1])

    def test_star_window_end_matches_trends_week_boundary(self):
        self.assertEqual(star_window_end('2026-10-05'), '2026-10-04')   # Monday -> Sunday
        self.assertEqual(star_window_end('2026-10-04'), '2026-10-04')


if __name__ == '__main__':
    unittest.main()


class LibraryGrowthUiTests(unittest.TestCase):
    def test_growing_sort_ranks_by_three_month_stars_once_per_repo(self):
        import subprocess
        root = Path(__file__).resolve().parents[2]
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',hidden:false,replaceChildren(){},append(){},setAttribute(){},removeAttribute(){}});return nodes.get(id)};
const c={console,window:{},URLSearchParams,history:{replaceState(){}},localStorage:{getItem:()=>null},fetch:()=>new Promise(()=>{}),document:{getElementById:node,querySelectorAll:()=>[],addEventListener(){},createElement:()=>({setAttribute(){}})}};
vm.createContext(c);vm.runInContext(fs.readFileSync('web/benchmark-name.js','utf8'),c);vm.runInContext(fs.readFileSync('web/app.js','utf8'),c);
c.payload=JSON.parse(fs.readFileSync('data/library_index.json','utf8'));
vm.runInContext('state.library=payload.records;state.libraryManifest=payload.manifest;state.librarySort="growth";renderLibrary()',c);
const html=node('library-list').innerHTML;
assert(node('library-count').textContent.includes('stars gained in 3 months'));
const ids=[...html.matchAll(/data-id="([^"]+)"/g)].map(m=>m[1]);
const byId=Object.fromEntries(c.payload.records.map(r=>[r.id,r]));
const values=ids.map(i=>byId[i].growth.githubStars['3m']);
assert(values.length>50);
for(let i=1;i<values.length;i++)assert(values[i-1]>=values[i],'sorted');
const repos=ids.map(i=>(byId[i].attention.githubRepo||i).toLowerCase());
assert.equal(new Set(repos).size,repos.length,'one entry per repository');
assert(html.includes('stars · 3 mo'));
"""
        result = subprocess.run(["node", "-e", script], cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr[-800:])

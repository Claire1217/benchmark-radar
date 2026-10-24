"""Cross-surface regressions use actual snapshot data and production adapters."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pipeline'))
from generate_search_policy import render
from search_index import SearchIndex

class SharedEvidenceSearchTests(unittest.TestCase):
    def node(self,script):
        p=subprocess.run(['node','-e',script],cwd=ROOT,capture_output=True,text=True,check=True)
        return json.loads(p.stdout)

    def test_policy_is_generated_from_one_registry(self):
        self.assertEqual((ROOT/'web/search-policy.js').read_text(),render())

    def test_boundaries_identity_hidden_and_subset_explanation(self):
        self.node(r'''
const S=require('./web/search.js'),a=require('assert');
const rows=[{id:'subset',name:'MixedSuite',description:'Broad numerical tasks',searchDocument:{concepts:[{id:'chip-design',scope:'task-subset',quote:'Tasks span chip design and chemistry',sourceUrl:'https://example.org/paper'}]}},
{id:'noise1',name:'REDACT'},{id:'pcb',name:'Board Routing',description:'printed circuit board routing under design constraints'},{id:'noise2',name:'MedAgentBench'},{id:'analysis',name:'TabularAnalysis',description:'exploratory data analysis (EDA)'},
{id:'hidden',name:'Chip design hidden',displayEligible:false},
{id:'h',name:'HumanEval'},{id:'hp',name:'HumanEval+'},
{id:'eda',name:'EDATasks',description:'Evaluating electronic design automation (EDA) workflows'}];
const ids=q=>Object.keys(S.search(rows,q).hits);
a.deepEqual(ids('chip design'),ids('chip deisgn'));
a(ids('EDA').includes('subset'));a(ids('EDA').includes('eda'));
a(!ids('chip design').includes('pcb'));a(!ids('EDA').includes('noise1'));a(!ids('EDA').includes('noise2'));a(!ids('chip design').includes('analysis'));a(!ids('chip design').includes('hidden'));
const hit=S.search(rows,'chip design').hits.subset;a.equal(hit.matchedConcepts[0].scope,'task-subset');a(hit.snippet.includes('chip design'));
a.equal(S.search(rows,'HumanEval+').hits.hp.exactMatch,'name');a.notEqual(S.search(rows,'HumanEval+').hits.h?.exactMatch,'name');
a.deepEqual(ids('zznonexistentzz'),[]);console.log('{}');
''')

    def test_trends_does_not_join_different_members_evidence(self):
        self.node(r'''
const D=require('./web/trends/directions.js'),a=require('assert');
const row=['Family','2026-01-01',[],'','','',[],[],{members:[{id:'a',name:'First',description:'chemical reaction'},{id:'b',name:'Second',description:'robot planning'}]}];
a.equal(D.matches([row],['chemical planning']).length,0);
a.equal(D.matches([row],['robot planning']).length,1);console.log('{}');
''')

    def test_real_browser_cli_and_trends_membership(self):
        library=json.loads((ROOT/'data/library_index.json').read_text())
        queries=['chip design','chip deisgn','EDA','analog circuit design','cybersecurity','VerilogEval','code generation','robotics','speech recognition','information retrieval','protein','chemistry','zznonexistentzz']
        expected=self.node('''
const S=require('./web/search.js'),D=require('./web/trends/directions.js'),L=require('./data/library_index.json'),T=require('./data/trends_search.json');
const queries='''+json.dumps(queries)+''';
console.log(JSON.stringify(queries.map(q=>({q,ids:Object.keys(S.search(L.records,q).hits).sort(),trendIds:D.matches(T.releases,[q]).flatMap(r=>(r[8]?.members||[]).filter(m=>S.match(m,q)).map(m=>m.id)).sort()}))));
''')
        index=SearchIndex(library['records'],lambda r:[])
        try:
            human=next(r for r in library['records'] if r['name']=='HumanEval')
            self.assertIn(human['id'],index.search('code generation')[0])
            for case in expected:
                self.assertEqual(sorted(index.search(case['q'])[0]),case['ids'])
                # Trends deliberately excludes aggregate indices and future-dated families.
                eligible={r['id'] for r in library['records'] if r.get('evaluationRole')!='aggregate-index' and (r.get('releasedAt') or '')<=library['manifest']['dataAsOf']}
                self.assertEqual([i for i in case['ids'] if i in eligible],case['trendIds'],case['q'])
            with tempfile.TemporaryDirectory() as directory:
                p=Path(directory)/'input.json';p.write_text(json.dumps({'library':library,'cases':[{'id':q,'query':q} for q in queries]}))
                result=subprocess.run(['node','pipeline/probe_library_search.cjs','web/app.js',str(p)],cwd=ROOT,capture_output=True,text=True,check=True)
                for actual,case in zip(json.loads(result.stdout),expected):
                    self.assertEqual(sorted(actual['hitIds']),case['ids'],case['q'])
        finally:
            index.close()

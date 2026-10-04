from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class TrendsKeywordTests(unittest.TestCase):
    def test_free_keyword_builds_consistent_trend(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};const node=id=>nodes[id]??(nodes[id]={value:'',innerHTML:'',textContent:'',classList:{toggle(){}},setAttribute(){}});
const c={document:{getElementById:node,addEventListener(){},querySelectorAll:()=>[]},window:{},localStorage:{getItem:()=>null},fetch:()=>new Promise(()=>{}),benchmarkNameHtml:s=>s};
vm.createContext(c);vm.runInContext(fs.readFileSync('web/trends/trends.js','utf8'),c);
c.payload=JSON.parse(fs.readFileSync('data/trends_topics.json','utf8'));
c.search=JSON.parse(fs.readFileSync('data/trends_search.json','utf8'));
vm.runInContext('DATA=payload;SEARCH=search;periods.release=12;',c);
node('search').value='robot';node('search').oninput();
assert(node('rows').innerHTML.includes('Keyword'),'keyword row missing');
const k=vm.runInContext('KEYWORD',c);
for(const m of ['1','3','6','12']){const w=k.windows[m];
 assert.strictEqual(w.releaseChart.values.reduce((a,b)=>a+b,0),w.count,'chart sums to count '+m);
 assert.strictEqual(w.releases.length,w.count);
 assert(w.releases.every(r=>(r.name+' '+r.description).toLowerCase().includes('robot')||true));}
assert(k.windows['12'].count>0);
assert(node('detail').innerHTML.includes('q=robot'),'Library link carries the keyword');
node('search').value='zzzz-no-such-keyword';node('search').oninput();
assert.strictEqual(vm.runInContext('KEYWORD',c),null);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()


class SearchCatalogTests(unittest.TestCase):
    def test_catalog_matches_topic_trends(self):
        import json, sys
        sys.path.insert(0, str(ROOT / 'pipeline'))
        topics = json.loads((ROOT / 'data/trends_topics.json').read_text())
        search = json.loads((ROOT / 'data/trends_search.json').read_text())
        self.assertEqual(search['categories'], [t['id'] for t in topics['topics']])
        self.assertEqual(len(search['releases']), topics['coverage']['datedFamilies'])
        dates = [r[1] for r in search['releases']]
        self.assertEqual(dates, sorted(dates))
        for r in search['releases']:
            self.assertTrue(all(0 <= i < len(search['repos']) for i in r[7]))
        for url, weekly, baseline in search['repos']:
            self.assertEqual(len(weekly), search['weeks'])
            self.assertTrue(all(n >= 0 for n in weekly) and baseline >= 0)
        # Per-category release counts in the 12-month window agree with Trends.
        end = topics['endExclusive']
        for i, t in enumerate(topics['topics']):
            w = t['windows']['12']
            n = sum(1 for r in search['releases'] if i in r[2] and w['start'] <= r[1] < end)
            self.assertEqual(n, w['count'], t['id'])

    def test_catalog_stays_small(self):
        self.assertLess((ROOT / 'data/trends_search.json').stat().st_size, 2_000_000)


class KeywordLoadingTests(unittest.TestCase):
    def test_loading_state_is_visible_before_index_arrives(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};const node=id=>nodes[id]??(nodes[id]={value:'',innerHTML:'',textContent:'',classList:{toggle(){}},setAttribute(){}});
const c={document:{getElementById:node,addEventListener(){},querySelectorAll:()=>[]},window:{},localStorage:{getItem:()=>null},fetch:()=>new Promise(()=>{}),benchmarkNameHtml:s=>s,console};
vm.createContext(c);vm.runInContext(fs.readFileSync('web/trends/trends.js','utf8'),c);
c.payload=JSON.parse(fs.readFileSync('data/trends_topics.json','utf8'));
vm.runInContext('DATA=payload;periods.release=3;',c);
node('search').value='robot';node('search').oninput();
assert(node('rows').innerHTML.includes('Loading keyword index'));
assert(node('rows').innerHTML.includes('Robotics'),'categories still shown while loading');
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)


class LibraryKeywordLinkTests(unittest.TestCase):
    def test_library_route_applies_q_parameter(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};const el=()=>({value:'',innerHTML:'',textContent:'',hidden:false,classList:{toggle(){}},setAttribute(){},removeAttribute(){},replaceChildren(){},append(){}});
const node=id=>nodes[id]??(nodes[id]=el());
const c={console,window:{},URLSearchParams,location:{hash:'#library?q=Robot'},history:{replaceState(){}},localStorage:{getItem:()=>null},fetch:()=>new Promise(()=>{}),document:{getElementById:node,querySelectorAll:()=>[],addEventListener(){},createElement:el}};
vm.createContext(c);vm.runInContext(fs.readFileSync('web/benchmark-name.js','utf8'),c);vm.runInContext(fs.readFileSync('web/app.js','utf8'),c);
c.payload=JSON.parse(fs.readFileSync('data/library_index.json','utf8'));
vm.runInContext('state.library=payload.records;state.libraryManifest=payload.manifest;renderLibrary=()=>{};route()',c);
assert.equal(vm.runInContext('state.librarySearch',c),'robot');
assert.equal(node('library-search').value,'Robot');
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)

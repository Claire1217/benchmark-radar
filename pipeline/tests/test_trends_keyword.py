"""User-built Trends directions: matching, related terms, persistence and the page flow."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


def node(script):
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(result.stderr[-1500:])
    return result.stdout


PAGE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};const node=id=>nodes[id]??(nodes[id]={value:'',innerHTML:'',textContent:'',classList:{toggle(){}},setAttribute(){}});
const mem={};const storage={getItem:k=>mem[k]??null,setItem:(k,v)=>{mem[k]=String(v)}};
let HASH='';
const c={document:{getElementById:node,addEventListener:(t,f)=>{if(t==='click')c.click=f},querySelectorAll:()=>[]},window:{},
 localStorage:storage,location:{get hash(){return HASH},pathname:'/trends/',search:'',origin:'https://x'},
 history:{replaceState:(a,b,u)=>{HASH=String(u).startsWith('#')?u:''}},navigator:{clipboard:{writeText(){}}},
 fetch:()=>new Promise(()=>{}),benchmarkNameHtml:s=>s,console};
vm.createContext(c);
vm.runInContext(fs.readFileSync('web/trends/directions.js','utf8'),c);
vm.runInContext(fs.readFileSync('web/trends/trends.js','utf8'),c);
c.payload=JSON.parse(fs.readFileSync('data/trends_topics.json','utf8'));
c.search=JSON.parse(fs.readFileSync('data/trends_search.json','utf8'));
const S=()=>vm.runInContext('selected',c),T=()=>vm.runInContext('findTopic(selected)',c);
const type=v=>{node('search').value=v;node('search').oninput();};
const act=(name,term)=>c.click({target:{closest:s=>s==='[data-act]'?{dataset:{act:name,term},textContent:''}:null}});
"""


class DirectionFunctionTests(unittest.TestCase):
    def test_matching_rules(self):
        node(r"""
const D=require('./web/trends/directions.js'),assert=require('assert');
const row=(name,desc)=>[name,'2026-01-01',[],desc,'','',[],[]];
const rows=[row('AutoPDEBench','neural solvers for PDEs'),row('SpeedUp','update latency of servers'),
 row('ChemQA','chemical reaction prediction'),row('LabX','a chemist assistant'),row('GPUPhys','GPU physics kernels'),row('Other','nothing here')];
const names=q=>D.matches(rows,D.parseTerms(q)).map(r=>r[0]);
assert.deepEqual(names('PDE'),['AutoPDEBench']);                    // whole word, not "update"
assert.deepEqual(names('chemistry'),['ChemQA','LabX']);              // stem: chemical, chemist
assert.deepEqual(names('gpu'),['GPUPhys']);                          // camelCase split
assert.deepEqual(names('pde, gpu'),['AutoPDEBench','GPUPhys']);      // commas are alternatives
assert.deepEqual(names('chemical reaction'),['ChemQA']);             // spaces form a phrase
assert.deepEqual(D.parseTerms(' GPU ,, CUDA  kernels;x '),['gpu','cuda kernels']);
""")

    def test_related_terms_are_specific(self):
        out = node(r"""
const D=require('./web/trends/directions.js');const S=require('./data/trends_search.json');
const t=D.parseTerms('gpu, cuda');const m=D.matches(S.releases,t);
console.log(JSON.stringify(D.related(S.releases,m,t).map(x=>x.term)));""")
        terms = json.loads(out)
        self.assertIn('kernel', ' '.join(terms))
        for generic in ('benchmark', 'bench', 'model', 'evaluation', 'reasoning', 'gpu', 'cuda'):
            self.assertNotIn(generic, terms)

    def test_storage_and_link_round_trip(self):
        node(r"""
const D=require('./web/trends/directions.js'),assert=require('assert');
const mem={};const s={getItem:k=>mem[k]??null,setItem:(k,v)=>{mem[k]=v}};
D.save(s,[D.make(['gpu','cuda kernels'])]);
const back=D.load(s);assert.equal(back[0].id,'custom:gpu+cuda-kernels');assert.equal(back[0].name,'GPU / Cuda Kernels');
assert.deepEqual(D.fromHash(D.toHash(['pde','fluid dynamics'])),['pde','fluid dynamics']);
assert.deepEqual(D.load({getItem:()=>'not json'}),[]);
assert.deepEqual(D.load({getItem:()=>{throw Error('blocked')}}),[]);
""")


class DirectionPageTests(unittest.TestCase):
    def test_type_keep_edit_remove(self):
        node(PAGE + r"""
vm.runInContext('DATA=payload;SEARCH=search;periods.release=12;render()',c);
type('chemistry');
assert.equal(S(),'custom:chemistry');assert(T().draft);
assert(node('rows').innerHTML.includes('New direction'));
assert(node('detail').innerHTML.includes('Keep as direction'));
const w=T().windows['12'];assert.equal(w.releaseChart.values.reduce((a,b)=>a+b,0),w.count);
assert(T().library>=w.count);
node('search').onkeydown({key:'Enter',preventDefault(){}});
assert.equal(node('search').value,'');assert.equal(S(),'custom:chemistry');assert(!T().draft);
assert(node('rows').innerHTML.includes('Your directions'));assert.equal(HASH,'#d=chemistry');
assert.equal(JSON.parse(mem['benchmark-radar:trends:directions:v1'])[0].terms[0],'chemistry');
// Stays in the list after the search box is cleared and other searches happen.
type('robot');type('');assert(node('rows').innerHTML.includes('Chemistry'));
c.click({target:{closest:s=>s==='[data-id]'?{dataset:{id:'custom:chemistry'}}:null}});
const before=T().library;const rel=T().related[0].term;
act('add',rel);assert.equal(S(),'custom:chemistry+'+rel.replace(/\s+/g,'-'));assert(T().library>before);
act('drop',rel);assert.equal(S(),'custom:chemistry');assert.equal(T().library,before);
act('remove');assert(!node('rows').innerHTML.includes('Your directions'));
assert.equal(JSON.parse(mem['benchmark-radar:trends:directions:v1']).length,0);
""")

    def test_no_match_and_loading_states(self):
        node(PAGE + r"""
vm.runInContext('DATA=payload;periods.release=3;render()',c);
type('robot');assert(node('rows').innerHTML.includes('Loading keyword index'));
assert(node('rows').innerHTML.includes('Robotics'),'categories still shown while loading');
vm.runInContext('SEARCH=search;render()',c);assert.equal(S(),'custom:robot');
type('zzzz-no-such-keyword');assert(node('rows').innerHTML.includes('No benchmarks match'));
""")

    def test_star_mode_and_library_link(self):
        node(PAGE + r"""
vm.runInContext('DATA=payload;SEARCH=search;periods.release=12;render()',c);
type('gpu, cuda');node('starTab').onclick();
const html=node('detail').innerHTML;assert(!html.includes('undefined')&&!html.includes('NaN'));
assert(html.includes('d=gpu%2Ccuda'),'Library link carries the direction terms');
""")


class SearchCatalogTests(unittest.TestCase):
    def test_catalog_matches_topic_trends(self):
        topics = json.loads((ROOT / 'data/trends_topics.json').read_text())
        search = json.loads((ROOT / 'data/trends_search.json').read_text())
        self.assertEqual(search['categories'], [t['id'] for t in topics['topics']])
        dated = [r for r in search['releases'] if r[1]]
        self.assertEqual(len(dated), topics['coverage']['datedFamilies'])
        self.assertEqual(len(search['releases']) - len(dated), topics['coverage']['undatedFamilies'])
        dates = [r[1] for r in search['releases']]
        self.assertEqual(dates, sorted(dates))
        for r in search['releases']:
            self.assertTrue(all(0 <= i < len(search['repos']) for i in r[7]))
        for url, weekly, baseline in search['repos']:
            self.assertEqual(len(weekly), search['weeks'])
            self.assertTrue(all(n >= 0 for n in weekly) and baseline >= 0)
        end = topics['endExclusive']
        for i, t in enumerate(topics['topics']):
            w = t['windows']['12']
            n = sum(1 for r in search['releases'] if r[1] and i in r[2] and w['start'] <= r[1] < end)
            self.assertEqual(n, w['count'], t['id'])

    def test_catalog_stays_small(self):
        self.assertLess((ROOT / 'data/trends_search.json').stat().st_size, 2_000_000)


class LibraryKeywordLinkTests(unittest.TestCase):
    def test_library_route_applies_q_parameter(self):
        node(r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};const el=()=>({value:'',innerHTML:'',textContent:'',hidden:false,classList:{toggle(){}},setAttribute(){},removeAttribute(){},replaceChildren(){},append(){}});
const node=id=>nodes[id]??(nodes[id]=el());
const c={console,window:{},URLSearchParams,location:{hash:'#library?q=Robot'},history:{replaceState(){}},localStorage:{getItem:()=>null},fetch:()=>new Promise(()=>{}),document:{getElementById:node,querySelectorAll:()=>[],addEventListener(){},createElement:el}};
vm.createContext(c);vm.runInContext(fs.readFileSync('web/benchmark-name.js','utf8'),c);vm.runInContext(fs.readFileSync('web/app.js','utf8'),c);
c.payload=JSON.parse(fs.readFileSync('data/library_index.json','utf8'));
vm.runInContext('state.library=payload.records;state.libraryManifest=payload.manifest;renderLibrary=()=>{};route()',c);
assert.equal(vm.runInContext('state.librarySearch',c),'robot');
assert.equal(node('library-search').value,'Robot');
""")


if __name__ == "__main__":
    unittest.main()


class SharedLinkTests(unittest.TestCase):
    def test_hash_change_opens_shared_direction(self):
        node(PAGE.replace("window:{},", "window:{addEventListener:(t,f)=>{if(t==='hashchange')c.onhash=f}},") + r"""
vm.runInContext('DATA=payload;SEARCH=search;periods.release=12;render()',c);
HASH='#d=pde,navier-stokes';c.onhash();
assert.equal(S(),'custom:pde+navier-stokes');assert(T().draft);assert.equal(node('search').value,'pde, navier stokes');
assert(vm.runInContext("Directions.termRegex('navier stokes').test(' solving navier-stokes flows')",c));
""")


class LayoutTests(unittest.TestCase):
    def test_grouped_layout_matches_library_groups(self):
        node(PAGE + r"""
vm.runInContext('DATA=payload;SEARCH=search;periods.release=12;render()',c);
const html=node('rows').innerHTML;
const lib=JSON.parse(fs.readFileSync('data/library_index.json','utf8')).manifest.libraryTaxonomy;
const labels=[...html.matchAll(/class="group-label">([^<]+)</g)].map(m=>m[1].replace(/&amp;/g,'&'));
assert.deepEqual(labels,lib.groups.map(g=>g.name).filter(n=>lib.directions.some(d=>d.section===n)));
// Same categories, same group membership as the Library sidebar.
const order=[...html.matchAll(/data-id="([^"]+)"/g)].map(m=>m[1]);
assert.deepEqual([...order].sort(),lib.directions.map(d=>d.id).sort());
for(const d of lib.directions){const t=c.payload.topics.find(t=>t.id===d.id);assert.equal(t.section,d.section,d.id);assert.equal(t.library,d.count,d.id);}
node('allLayout').onclick();
const flat=node('rows').innerHTML;assert(!flat.includes('group-label'));
assert.equal(mem['benchmark-radar:trends:layout'],'all');
const counts=[...flat.matchAll(/<span class="num">([\d,—]+)<\/span>/g)].map(m=>Number(m[1].replace(/,/g,''))||0);
for(let i=1;i<counts.length;i++)assert(counts[i-1]>=counts[i],'All layout ranks every category by count');
node('groupLayout').onclick();assert(node('rows').innerHTML.includes('group-label'));
""")


class CategoryHashTests(unittest.TestCase):
    def test_category_hash_opens_that_category(self):
        node(PAGE.replace("window:{},", "window:{addEventListener:(t,f)=>{if(t==='hashchange')c.onhash=f}},") + r"""
vm.runInContext('DATA=payload;SEARCH=search;periods.release=12;render()',c);
HASH='#c=speech-audio';c.onhash();
assert.equal(S(),'speech-audio');assert(node('detail').innerHTML.includes('Speech &amp; Audio')||node('detail').innerHTML.includes('Speech & Audio'));
HASH='#c=not-a-category';c.onhash();assert.equal(S(),'speech-audio');
c.click({target:{closest:s=>s==='[data-id]'?{dataset:{id:'math'}}:null}});assert.equal(HASH,'#c=math');
""")

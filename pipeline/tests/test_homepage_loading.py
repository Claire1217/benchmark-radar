"""Exercise first-screen rendering with stalled/failed data requests."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from site_views import bootstrap, presentation

LOADING = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const input=JSON.parse(fs.readFileSync(0,'utf8')),nodes=new Map(),pending=[],requests=[];
const node=id=>{
 if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',hidden:false,value:'',dataset:{},children:[],
  setAttribute(){},removeAttribute(){},replaceChildren(){this.children=[]},append(child){this.children.push(child)}});
 return nodes.get(id);
};
node('radar-bootstrap').textContent=JSON.stringify(input);
const c={console,URLSearchParams,location:{hash:''},history:{replaceState(){}},window:{addEventListener(){}},
 localStorage:{getItem:()=>null,setItem(){}},
 document:{getElementById:node,querySelectorAll:()=>[],querySelector:()=>node('today'),addEventListener(){},
  createElement:()=>node(Symbol()),createTextNode:text=>({textContent:text})},
 fetch:url=>{requests.push(url);return new Promise((resolve,reject)=>pending.push({resolve,reject}))}};
vm.createContext(c);
for(const name of ['benchmark-name.js','trends/directions.js','following.js','app.js'])vm.runInContext(fs.readFileSync('web/'+name,'utf8'),c);
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 assert.equal(requests.length,0,'homepage must not request either full dataset');
 const first=node('benchmark-list').innerHTML;
 assert(first.includes('<article'),'real cards must appear before any data request');
 assert.equal(node('library-list').innerHTML,'','do not render the hidden Library');
 vm.runInContext('withRadar(()=>{window.actionCompleted=true})',c);
 assert.equal(requests.length,1);
 pending.shift().reject(new Error('offline'));await flush();
 assert.equal(node('benchmark-list').innerHTML,first,'keep the usable first screen when data fails');
 assert(node('data-status').children.some(child=>child.textContent==='Retry'));
 vm.runInContext('withRadar(()=>{window.actionCompleted=true})',c);
 pending.shift().resolve({ok:true,json:async()=>({manifest:input.manifest,records:input.records})});await flush();
 assert.equal(c.window.actionCompleted,true,'retry must finish the original action');
 const a=vm.runInContext('ensureLibrary()',c),b=vm.runInContext('ensureLibrary()',c);
 assert.equal(a,b,'concurrent intent and navigation must share one download');
 const records=Array.from({length:180},(_,i)=>({id:'item-'+i,name:'Benchmark '+i,description:'Searchable item',releasedAt:'2026-10-01',attention:{githubStars:i}}));
 pending.shift().resolve({ok:true,json:async()=>({manifest:input.libraryManifest,records})});await a;
 assert.equal(node('library-list').innerHTML,'','warming data must not render a hidden view');
 c.location.hash='#library';vm.runInContext('route()',c);
 assert.equal((node('library-list').innerHTML.match(/<article/g)||[]).length,60);
 assert(node('library-count').textContent.startsWith('180 entries'));
 assert.equal(node('library-more').hidden,false);
 vm.runInContext('state.libraryVisible+=LIBRARY_PAGE_SIZE;renderLibrary()',c);
 assert.equal((node('library-list').innerHTML.match(/<article/g)||[]).length,120);
 vm.runInContext('state.librarySearch="Benchmark 179";state.libraryVisible=LIBRARY_PAGE_SIZE;renderLibrary()',c);
 assert(node('library-list').innerHTML.includes('Benchmark 179'),'search must include unloaded result pages');
 console.log('first screen, offline retry, request deduplication, paging and full-catalog search passed');
})().catch(error=>{console.error(error);process.exitCode=1});
'''


class HomepageLoadingTests(unittest.TestCase):
    def payload(self):
        radar = presentation(json.loads((ROOT / 'data/benchmarks_index.json').read_text()))
        library = presentation(json.loads((ROOT / 'data/library_index.json').read_text()))
        return bootstrap(radar, library)

    def test_first_screen_does_not_wait_for_data_and_failures_are_retryable(self):
        result = subprocess.run(['node', '-e', LOADING], input=json.dumps(self.payload()),
                                text=True, capture_output=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_renderer_emits_real_cards_and_bootstrap_stays_small(self):
        payload = self.payload()
        self.assertLess(len(json.dumps(payload).encode()), 120_000)
        result = subprocess.run(['node', 'pipeline/render_home.cjs'], input=json.dumps(payload),
                                text=True, capture_output=True, cwd=ROOT, check=True)
        rendered = json.loads(result.stdout)
        self.assertEqual(rendered['benchmark-list']['innerHTML'].count('<article'), len(payload['records']))
        self.assertTrue(rendered['summary']['innerHTML'])
        self.assertTrue(payload['previousDate'])

    def test_bootstrap_keeps_complete_days_and_omits_hidden_or_future_records(self):
        records = ([{'id': 'today', 'releasedAt': '2026-10-16'}]
                   + [{'id': str(i), 'releasedAt': '2026-10-15'} for i in range(12)]
                   + [{'id': 'previous', 'releasedAt': '2026-10-14'},
                      {'id': 'future', 'releasedAt': '2026-10-17'},
                      {'id': 'hidden', 'releasedAt': '2026-10-16', 'displayEligible': False}])
        payload = bootstrap({'manifest': {'dataAsOf': '2026-10-16'}, 'records': records}, {'manifest': {}})
        self.assertEqual(len(payload['records']), 13)
        self.assertEqual(payload['previousDate'], '2026-10-14')


if __name__ == '__main__':
    unittest.main()

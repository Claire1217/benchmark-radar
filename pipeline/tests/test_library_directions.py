"""User-built directions appear in the Library sidebar and filter the list."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

SETUP = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',hidden:false,replaceChildren(){},append(){},setAttribute(){},removeAttribute(){}});return nodes.get(id)};
const mem={'benchmark-radar:trends:directions:v1':JSON.stringify([{terms:['gpu','kernel']}])};
let HASH='';
const c={console,window:{},URLSearchParams,location:{get hash(){return HASH},set hash(v){HASH=v}},history:{replaceState:(a,b,u)=>{HASH=u}},
 localStorage:{getItem:k=>mem[k]??null,setItem:(k,v)=>{mem[k]=v}},fetch:()=>new Promise(()=>{}),
 document:{getElementById:node,querySelectorAll:()=>[],addEventListener(){},createElement:()=>({setAttribute(){}})}};
vm.createContext(c);
for(const f of ['web/benchmark-name.js','web/trends/directions.js','web/app.js'])vm.runInContext(fs.readFileSync(f,'utf8'),c);
c.payload=JSON.parse(fs.readFileSync('data/library_index.json','utf8'));
vm.runInContext('state.library=payload.records;state.libraryManifest=payload.manifest;setupLibraryNavigation()',c);
const D=require('./web/trends/directions.js');
const expected=c.payload.records.filter(r=>r.displayEligible!==false&&r.evaluationMode!=='viewpoint_probe')
 .filter(r=>D.matches([[r.name,'',[],[r.description,r.oneLine].filter(Boolean).join(' '),'',(r.aliases||[]).join(' ')]],['gpu','kernel']).length);
"""


def run(script):
    result = subprocess.run(["node", "-e", SETUP + script], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(result.stderr[-1200:])


class LibraryDirectionTests(unittest.TestCase):
    def test_saved_direction_is_listed_with_its_count_and_filters(self):
        run(r"""
const html=node('library-domain-list').innerHTML;
assert(html.includes('Your directions'));
const m=html.match(/data-library-custom="gpu,kernel"[^>]*><span>([^<]+)<\/span><small>(\d+)<\/small>/);
assert(m,'saved direction button');assert.equal(m[1],'GPU / Kernel');assert.equal(Number(m[2]),expected.length);
assert(expected.length>5);
node('library-domain-list').onclick({target:{closest:()=>({dataset:{libraryCustom:'gpu,kernel'}})}});
assert.equal(HASH,'#library?d=gpu%2Ckernel');
assert(node('library-count').textContent.startsWith(expected.length+' entries'));
assert.equal(node('library-title').textContent,'GPU / Kernel');
// A category click clears the direction filter.
node('library-domain-list').onclick({target:{closest:()=>({dataset:{libraryDirection:'math'}})}});
assert.equal(vm.runInContext('state.libraryCustom.length',c),0);
""")

    def test_shared_link_opens_direction_in_library(self):
        run(r"""
HASH='#library?d=gpu,kernel';vm.runInContext('route()',c);
assert.deepEqual(Array.from(vm.runInContext('state.libraryCustom',c)),['gpu','kernel']);
assert.equal(vm.runInContext('state.library.filter(matchesLibraryFilters).length',c),expected.length);
""")

    def test_empty_state_points_to_trends(self):
        run(r"""
mem['benchmark-radar:trends:directions:v1']='[]';vm.runInContext('setupLibraryNavigation()',c);
assert(node('library-domain-list').innerHTML.includes('href="./trends/"'));
""")


if __name__ == '__main__':
    unittest.main()


class TrendLinkTests(unittest.TestCase):
    def test_link_targets(self):
        run(r"""
const link=node('library-trend-link');let href=null;link.setAttribute=(k,v)=>{if(k==='href')href=v};link.removeAttribute=k=>{if(k==='href')href=null};
node('library-domain-list').onclick({target:{closest:()=>({dataset:{libraryDirection:'computer-use'}})}});
assert.equal(href,'./trends/#c=computer-use');assert.equal(link.hidden,false);
node('library-domain-list').onclick({target:{closest:()=>({dataset:{libraryCustom:'gpu,kernel'}})}});
assert.equal(href,'./trends/#d=gpu%2Ckernel');
node('library-domain-list').onclick({target:{closest:()=>({dataset:{libraryScope:''}})}});
assert.equal(href,null);assert.equal(link.hidden,true);
""")

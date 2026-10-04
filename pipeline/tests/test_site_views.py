"""The website's trimmed record files must render exactly like the full ones."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from site_views import referenced_names, slim, write_views

RENDER = r"""
const fs=require('fs'),vm=require('vm');
function render(libraryFile, radarFile){
 const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',hidden:false,dataset:{},replaceChildren(){},append(){},setAttribute(){},removeAttribute(){}});return nodes.get(id)};
 const c={console,window:{},URLSearchParams,history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:()=>new Promise(()=>{}),
  document:{getElementById:node,querySelectorAll:()=>[],querySelector:()=>({textContent:''}),addEventListener(){},createElement:()=>({setAttribute(){}})}};
 vm.createContext(c);for(const f of ['web/benchmark-name.js','web/trends/directions.js','web/following.js','web/github-repositories.js','web/app.js'])vm.runInContext(fs.readFileSync(f,'utf8'),c);
 c.lib=JSON.parse(fs.readFileSync(libraryFile,'utf8'));c.radar=JSON.parse(fs.readFileSync(radarFile,'utf8'));
 vm.runInContext('state.library=lib.records;state.libraryManifest=lib.manifest;state.benchmarks=radar.records;state.manifest=radar.manifest;setupLibraryNavigation()',c);
 const out=[node('library-domain-list').innerHTML];
 for(const d of c.lib.manifest.libraryTaxonomy.directions.slice(0,36)){for(const sort of ['attention','latest','growth']){c.sel=d.id;c.sort=sort;
  vm.runInContext('state.libraryDirection=sel;state.librarySort=sort;state.librarySearch="";renderLibrary()',c);out.push(node('library-list').innerHTML,node('library-count').textContent);}}
 for(const q of ['robot','swe-bench','memory']){c.q=q;vm.runInContext('state.libraryDirection="";state.librarySort="attention";state.librarySearch=q;renderLibrary()',c);out.push(node('library-list').innerHTML);}
 for(const w of ['today','30d','90d']){for(const sort of ['attention','newest']){c.w=w;c.sort=sort;
  vm.runInContext('state.window=w;state.sort=sort;state.visible=500;state.latestFrom=latestAvailableDate();renderRadar()',c);out.push(node('benchmark-list').innerHTML);}}
 return out;
}
const a=render(process.argv[1],process.argv[2]),b=render(process.argv[3],process.argv[4]);
if(a.length!==b.length)throw Error('length');
for(let i=0;i<a.length;i++)if(a[i]!==b[i])throw Error('render differs at '+i+': '+a[i].slice(0,200)+' VS '+b[i].slice(0,200));
console.log('identical',a.length);
"""


class SiteViewTests(unittest.TestCase):
    def test_slim_keeps_only_referenced_fields(self):
        payload = {'manifest': {'x': 1}, 'records': [{'id': 'a', 'name': 'A', 'unusedBlob': {'big': 1}, 'links': {'code': 'u'}}]}
        self.assertEqual(slim(payload, {'id', 'name', 'links'}),
                         {'manifest': {'x': 1}, 'records': [{'id': 'a', 'name': 'A', 'links': {'code': 'u'}}]})
        names = referenced_names()
        for field in ('libraryCategories', 'attention', 'links', 'modelReportReferences', 'growth', 'aliases'):
            self.assertIn(field, names)

    def test_library_renders_identically_from_view(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            for name in ('library_index.json', 'benchmarks_index.json'):
                (data / name).write_text((ROOT / 'data' / name).read_text())
            sizes = write_views(data)
            full = (data / 'library_index.json').stat().st_size
            self.assertLess(sizes['library_view.json'], full * 0.8, 'view should be meaningfully smaller')
            result = subprocess.run(['node', '-e', RENDER, str(data / 'library_index.json'), str(data / 'benchmarks_index.json'),
                                     str(data / 'library_view.json'), str(data / 'radar_view.json')],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])


if __name__ == '__main__':
    unittest.main()

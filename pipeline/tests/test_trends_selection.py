import subprocess
import unittest
from pathlib import Path

class TrendsSelectionTests(unittest.TestCase):
    def test_search_selection_and_empty_details(self):
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};const node=id=>nodes[id]??(nodes[id]={value:'',innerHTML:'',textContent:'',classList:{toggle(){}},setAttribute(){}});
const c={document:{getElementById:node,addEventListener(){},querySelectorAll:()=>[]},window:{},localStorage:{getItem:()=>null},fetch:()=>new Promise(()=>{}),benchmarkNameHtml:s=>s};
vm.createContext(c);vm.runInContext(fs.readFileSync('web/trends/trends.js','utf8'),c);
c.payload=JSON.parse(fs.readFileSync('data/trends_topics.json','utf8'));
vm.runInContext('DATA=payload;periods.release=3;render()',c);
node('search').value='Multi-Agent';node('search').oninput();
assert(node('detail').innerHTML.includes('Multi-Agent Systems'));
assert(node('detail').innerHTML.includes('direction=multi-agent'));
assert(!node('detail').innerHTML.includes('direction=coding-agents'));
node('search').value='no-matching-topic-xyz';node('search').oninput();
assert(node('detail').innerHTML.includes('No matching'));
assert(!node('detail').innerHTML.includes('View in Library'));
node('search').value='';node('search').oninput();
assert(node('detail').innerHTML.includes('View in Library'));
for(const modeName of ['release','star']){
 node(modeName+'Tab').onclick();
 for(const m of [1,3,6]){
  node('window').value=String(m);node('window').onchange();
  const html=node('detail').innerHTML;
  assert(!html.includes('undefined'));assert(!html.includes('NaN'));
  const v=vm.runInContext('values(DATA.topics.find(t=>t.id===selected))',c);
  assert.strictEqual(v.bars.reduce((a,b)=>a+b,0),v.n);
  assert(html.includes(m===1?'Daily totals':m===3||modeName==='star'?'Weekly totals':'Monthly totals'));
  assert(html.includes('Change '));
 }
}
'''
        subprocess.run(['node','-e',script],cwd=Path(__file__).resolve().parents[2],check=True,capture_output=True,text=True)

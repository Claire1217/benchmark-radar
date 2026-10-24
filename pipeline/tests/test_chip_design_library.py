"""Exercise the actual Library filter and source-backed chip coverage."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pipeline'))
from search_index import SearchIndex

EXPECTED=[
 'review_build_a_chip_bench','review_hwe_bench_riscv_v2',
 'bm_analog-design-bench_8213864b','review_sganalog','bm_parasgb_cd57a968',
 'review_tapeoutbench_v01','review_perfreasoning',
 'bm_veribugbench-an-empirically-grounded-frame_9ddf8887',
 'bm_vhdl-repobench_0a758628','review_gatetruth','review_chipverilog',
 'bm_agenticbbo-bench_7edbb260','review_verilog_design_flows',
 'catalog_d0b03ebbcb611ba0','catalog_e86e142377807e7b','catalog_f7bd3cbea6ce8294']

class ChipDesignLibraryTests(unittest.TestCase):
 def test_real_library_filter_chinese_english_and_scope(self):
  script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const data=JSON.parse(fs.readFileSync('data/library_index.json','utf8'));
const app=fs.readFileSync('web/app.js','utf8');
const c={state:{},displayEligible:r=>r.displayEligible!==false&&r.evaluationMode!=='viewpoint_probe',topicIds:r=>r.libraryCategories||[],allResearchDefinitions:()=>data.manifest.libraryTaxonomy.directions};
vm.createContext(c);
vm.runInContext(app.slice(app.indexOf('function matchesSearch('),app.indexOf('function card(')),c);
const expected=JSON.parse(process.argv[1]);
for(const q of ['芯片设计','chip design','EDA']){
 c.state.librarySearch=q;const hits=data.records.filter(c.matchesLibraryFilters);const ids=new Set(hits.map(r=>r.id));
 for(const id of expected)assert(ids.has(id),q+' missing '+id);
 assert(!c.matchesSearch('CAD benchmark for mechanical gears and buildings',q));
 assert(!c.matchesSearch('Exploratory data analysis for financial spreadsheets',q));
 console.log(q+': '+hits.length+' results; all '+expected.length+' audited targets visible');
}
assert(c.matchesSearch('FrontierSWE v2','frontier swe'));
const rows=new Map(data.records.map(r=>[r.id,r]));
assert(!rows.has('bm_long-horizon-analog-design-bench_66fde81d'));
assert(rows.get('bm_analog-design-bench_8213864b').aliases.includes('Long-Horizon Analog Design Bench'));
assert.notEqual(rows.get('review_hwe_bench_riscv_v2').links.code,rows.get('catalog_8a6ea8076d447a90').links.code);
for(const id of expected.slice(-3)){
 const r=rows.get(id);assert(r.searchProvenance[0].sources[0].includes('/tasks/'));
 assert(/subset|within a broader|only part/i.test(r.description));
}
'''
  subprocess.run(['node','-e',script,json.dumps(EXPECTED)],cwd=ROOT,check=True)
 def test_cli_retrieves_chip_design_without_identity_alias_abuse(self):
  rows=json.loads((ROOT/'data/library_index.json').read_text())['records']
  index=SearchIndex(rows,lambda r:r.get('libraryCategories',[]))
  try:
   hits,meta=index.search('芯片设计')
   self.assertTrue(set(EXPECTED)<=set(hits),set(EXPECTED)-set(hits))
   self.assertIn('verilog',meta['expandedTerms'])
   for r in rows:
    if r['id'] in EXPECTED:self.assertNotIn('芯片设计',r.get('aliases',[]))
  finally:index.close()

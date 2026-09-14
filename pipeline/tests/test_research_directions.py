"""Research navigation must remain multi-label, reproducible and uncluttered."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from research_directions import DIRECTIONS, annotate_records, classify_directions, direction_manifest


class ResearchDirectionTests(unittest.TestCase):
    def test_stable_unique_definitions(self):
        ids = [d["id"] for d in DIRECTIONS]
        self.assertEqual(len(ids), 23)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(d["description"] for d in DIRECTIONS))

    def test_multi_label_and_no_mutation(self):
        record = {"name": "Scientific Agent", "description": "Scientific discovery agents with tool calling and persistent memory."}
        before = copy.deepcopy(record)
        result = classify_directions(record)
        self.assertTrue({"ai-for-science", "ai-scientist", "tool-use", "agent-memory"} <= result.keys())
        self.assertEqual(record, before)

    def test_naturebench_is_science_even_with_condensed_description(self):
        record = {"name": "NatureBench", "description": "AI coding agents on 90 tasks distilled from Nature-family publications across 6 scientific domains."}
        result = classify_directions(record)
        self.assertIn("coding-agents", result)
        self.assertIn("ai-for-science", result)
        self.assertEqual(result["ai-for-science"]["sourceUrl"], "https://arxiv.org/abs/2606.24530")
        annotate_records([record])
        annotate_records([record])
        self.assertEqual(record["researchDirections"].count("ai-for-science"), 1)

    def test_no_unknown_fallback(self):
        self.assertEqual(classify_directions({"name": "Unspecified", "description": ""}), {})

    def test_known_exclusions(self):
        result = classify_directions({"name": "AuthMem-Bench", "description": "Agent memory and self-improvement"})
        self.assertNotIn("self-improvement-rsi", result)
        self.assertIn("agent-memory", result)
        self.assertNotIn("mathematical-reasoning", classify_directions({
            "name": "ScreenSpot", "source": {"type": "catalog"},
            "area": "Mathematical Reasoning", "catalogCategories": ["spatial reasoning"],
            "description": "GUI grounding evaluation"}))

    def test_counts_visible_only_and_idempotency(self):
        rows = [{"name": "A", "description": "Tool calling"},
                {"name": "B", "description": "Tool calling", "displayEligible": False},
                {"name": "C", "description": "Tool calling", "evaluationMode": "viewpoint_probe"}]
        annotate_records(rows)
        before = copy.deepcopy(rows)
        annotate_records(rows)
        self.assertEqual(rows, before)
        manifest = direction_manifest(rows)
        self.assertEqual(next(d["count"] for d in manifest["directions"] if d["id"] == "tool-use"), 1)

    def test_generated_manifest_matches_records(self):
        payload = json.loads((ROOT / "data/library_index.json").read_text())
        self.assertEqual(payload["manifest"]["researchTaxonomy"], direction_manifest(payload["records"]))
        for r in payload["records"]:
            self.assertEqual(r["researchDirections"], list(r["researchDirectionEvidence"]))

    def test_real_client_filters_chips_and_counts(self):
        script = r"""
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const nodes=new Map();
const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',hidden:false,replaceChildren(){},append(){},setAttribute(){},removeAttribute(){}});return nodes.get(id)};
const context={console,window:{},URLSearchParams,history:{replaceState(){}},localStorage:{getItem:()=>null},fetch:()=>new Promise(()=>{}),document:{getElementById:node,querySelectorAll:()=>[],addEventListener(){},createElement:()=>({setAttribute(){}})}};
vm.createContext(context);vm.runInContext(fs.readFileSync('web/app.js','utf8'),context);
context.payload=JSON.parse(fs.readFileSync('data/library_index.json','utf8'));
vm.runInContext('state.library=payload.records.map(publicResearchRecord);state.libraryManifest=payload.manifest;setupLibraryNavigation()',context);
assert(node('library-domain-list').innerHTML.includes('Self-Improvement &amp; RSI'));
assert(!node('library-domain-list').innerHTML.includes('data-library-capability'));
assert(!node('library-domain-list').innerHTML.includes('data-library-direction="ai-scientist"'));
assert(!node('library-domain-list').innerHTML.includes('data-library-direction="ai-r-d"'));
assert.equal(context.researchDefinitions().filter(d=>d.section==='Featured topics').length,2);
for(const d of context.researchDefinitions()){
  context.selected=d.id;
  vm.runInContext('state.libraryDirection=selected;renderLibrary()',context);
  const ids=d.id==='ai-for-science'?['ai-for-science','ai-scientist','ai-r-d']:[d.id];
  const count=context.payload.records.filter(r=>r.displayEligible!==false&&r.evaluationMode!=='viewpoint_probe'&&(r.researchDirections||[]).some(id=>ids.includes(id))).length;
  assert(node('library-count').textContent.startsWith(count+' results'));
  assert.equal(node('library-title').textContent,d.name);
}
vm.runInContext('state.libraryDirection="";state.librarySearch="";',context);
for(const r of context.payload.records){
  context.record=context.publicResearchRecord(r);
  const chips=vm.runInContext('directionChips(record)',context);
  assert(chips.length<=2);
}
vm.runInContext('state.libraryDirection=publicDirection("ai-scientist");',context);
context.record=context.publicResearchRecord({researchDirections:['ai-scientist','ai-for-science','tool-use']});
assert.equal(context.record.researchDirections.length,2);
assert.deepEqual(Array.from(vm.runInContext('directionChips(record,state.libraryDirection)',context)),['Tool Use']);
context.record=context.publicResearchRecord({domainScope:'domain-specific',applicationDomains:['Science & Research'],researchDirections:['ai-scientist']});
assert(vm.runInContext('matchesLibraryFilters(record)',context));
context.record.displayEligible=false;
assert(!vm.runInContext('matchesLibraryFilters(record)',context));
vm.runInContext('state.libraryDirection="";state.librarySort="latest";renderLibrary()',context);
assert(node('library-count').textContent.includes('latest releases'));
assert(!/<h2>\s*<a/.test(node('library-list').innerHTML));
vm.runInContext('state.librarySearch="no-such-benchmark-xyz";renderLibrary()',context);
assert(node('library-count').textContent.startsWith('0 results'));
assert(node('library-more').hidden);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()

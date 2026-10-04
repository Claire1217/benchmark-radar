import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pipeline'))
from library_categories import annotate_categories, category_manifest


class LibraryCategoryTests(unittest.TestCase):
    def test_reviewed_assignment_puts_primary_first_and_counts_secondary(self):
        import library_categories as lc
        reviewed={'a':{'primary':'tool-use','secondary':['professional-work']},'b':{'primary':'other','secondary':[]}}
        original=lc.assignments
        lc.assignments=lambda:reviewed
        try:
            records=[{'id':'a','name':'A'},{'id':'b','name':'B'},
                     {'id':'a-variant','name':'A Lite','variantOf':'a'},
                     {'id':'hidden','name':'H','variantOf':'a','displayEligible':False}]
            annotate_categories(records)
            manifest=category_manifest(records)
        finally:
            lc.assignments=original
        by={d['id']:d for d in manifest['directions']}
        self.assertEqual(records[0]['libraryCategories'],['tool-use','professional-work'])
        self.assertEqual(records[1]['libraryCategories'],[])  # reviewed as outside every category
        self.assertEqual(records[2]['categoryAssignment']['basis'],'inherited-from-family')
        self.assertEqual(by['tool-use']['count'],2)
        self.assertEqual(by['professional-work']['count'],2)
        self.assertEqual(by['professional-work']['primaryCount'],0)
        self.assertEqual(manifest['unclassifiedCount'],1)

    def test_unreviewed_record_gets_flagged_keyword_assignment(self):
        records=[{'id':'new-today','name':'GUIBench','description':'Agents operate desktop applications from screenshots.'}]
        annotate_categories(records)
        self.assertEqual(records[0]['libraryCategories'][0],'computer-use')
        self.assertEqual(records[0]['categoryAssignment']['basis'],'keyword-provisional')
        self.assertEqual(category_manifest(records)['provisionalCount'],1)

    def test_retired_categories_redirect_to_v5(self):
        aliases=category_manifest([])['aliases']
        for old,new in {'vision-language-models':'visual-reasoning','data-analysis-agents':'professional-work',
                        'software-engineering':'agentic-coding','ai-for-science':'science','gui-grounding':'computer-use'}.items():
            self.assertEqual(aliases[old],new)
        ids={d['id'] for d in category_manifest([])['directions']}
        legacy=category_manifest([])['legacyFilters']
        for kind in ('domain','capability'):
            self.assertTrue(set(legacy[kind].values()) <= ids, kind)
        self.assertFalse({'vision-language-models','data-analysis-agents','software-engineering'} & ids)

    def test_sidebar_search_and_route_agree_for_every_public_category(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const payload=JSON.parse(fs.readFileSync('data/library_index.json','utf8'));
const state={library:payload.records,libraryManifest:payload.manifest,librarySearch:''};
const nodes={};
function el(){return {value:'',children:[],attrs:{},hidden:false,innerHTML:'',setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},replaceChildren(){this.children=[]},append(b){this.children.push(b)},scrollIntoView(){}}}
const c={state,URLSearchParams,LIBRARY_PAGE_SIZE:120,location:{hash:''},history:{replaceState(){}},
 document:{querySelectorAll:()=>[],createElement:el,addEventListener(){}},$:id=>nodes[id]??(nodes[id]=el()),
 escapeHtml:s=>s,renderLibrary(){},renderRadar(){},renderTrend(){}};
vm.createContext(c);const app=fs.readFileSync('web/app.js','utf8');
for(const prefix of ['function route()','function displayEligible('])vm.runInContext(app.split('\n').find(l=>l.startsWith(prefix)),c);
vm.runInContext(app.slice(app.indexOf('function normalizeLibraryQuery('),app.indexOf('function taxonomyDetails(')),c);
vm.runInContext(app.slice(app.indexOf('function matchesSearch('),app.indexOf('function card(')),c);
vm.runInContext(app.slice(app.indexOf('let typeOptions='),app.indexOf('Promise.all([')),c);
c.setupLibraryNavigation();
const html=nodes['library-domain-list'].innerHTML;
assert(!html.includes('More benchmark categories'));
const buttons=[...html.matchAll(/data-library-direction="([^"]+)"[^>]*><span>([^<]+)<\/span><small>(\d+)<\/small>/g)];
assert.equal(buttons.length,payload.manifest.libraryTaxonomy.directions.length);
assert.equal(new Set(buttons.map(b=>b[1])).size,buttons.length);
assert.equal(new Set(buttons.map(b=>b[2].toLowerCase())).size,buttons.length);
for(const [_,id,name,count] of buttons){
 nodes['library-domain-list'].onclick({target:{closest:()=>({dataset:{libraryDirection:id}})}});
 const clicked=state.library.filter(c.matchesLibraryFilters).map(r=>r.id);
 assert.equal(clicked.length,Number(count),id+' click count');
 c.location.hash='#library?direction='+id;c.route();
 assert.equal(state.libraryDirection,id,id+' changed on reload');
 assert.deepEqual(state.library.filter(c.matchesLibraryFilters).map(r=>r.id),clicked,id+' reload members');
 const def=c.typeDefinitions().find(d=>d.id===id&&d.kind==='direction');assert.equal(def.name,name);
}
for(const [alias,canonical] of Object.entries(payload.manifest.libraryTaxonomy.aliases)){
 c.location.hash='#library?direction='+alias;c.route();assert.equal(state.libraryDirection,canonical);
 assert.equal(state.library.filter(c.matchesLibraryFilters).length,Number(buttons.find(b=>b[1]===canonical)[3]));
}
// The old Application fields section is gone; its links open the matching v5 category.
assert(!html.includes('data-library-domain'),'no second classification in the sidebar');
for(const [kind,map] of Object.entries(payload.manifest.libraryTaxonomy.legacyFilters)){
 for(const [label,target] of Object.entries(map)){
  c.location.hash='#library?'+kind+'='+encodeURIComponent(label);c.route();
  assert.equal(state.libraryDirection,target,kind+'='+label);
  assert.equal(state.libraryDomain||'','',kind+'='+label+' left a domain filter');
  assert.equal(state.library.filter(c.matchesLibraryFilters).length,Number(buttons.find(b=>b[1]===target)[3]));
 }
}
state.libraryDomain='';
state.libraryDirection='';nodes['library-search'].value='Computer Use';c.showTypes();
assert.match(nodes['type-options'].children[0].textContent,/^Computer Use & GUI Agents · Type · /);
nodes['type-options'].children[0].onclick();assert.equal(state.libraryDirection,'computer-use');
console.log('Verified all '+buttons.length+' categories: unique sidebar names, search, counts, click/reload membership and legacy links.');
'''
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)


if __name__=='__main__':unittest.main()

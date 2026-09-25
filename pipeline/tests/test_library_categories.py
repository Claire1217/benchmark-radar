import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pipeline'))
from library_categories import annotate_categories, category_manifest


class LibraryCategoryTests(unittest.TestCase):
    def test_retired_data_analysis_keeps_records_and_agent_topic(self):
        records=[{'id':'data','researchDirections':['data-analysis']},
                 {'id':'agent','researchTopics':['data-analysis-agents']}]
        annotate_categories(records)
        manifest=category_manifest(records)
        self.assertEqual(len(records),2)
        self.assertNotIn('data-analysis',[d['id'] for d in manifest['directions']])
        self.assertNotIn('data-analysis',manifest['aliases'])
        self.assertIn('data-analysis',manifest['retiredIds'])
        self.assertEqual(records[0]['libraryCategories'],[])
        self.assertEqual(records[1]['libraryCategories'],['data-analysis-agents'])

    def test_science_parent_is_broad_and_counts_each_record_once(self):
        records=[{'id':'broad','researchDirections':['ai-for-science']},
                 {'id':'agent','researchTopics':['scientific-agents']},
                 {'id':'both','researchTopics':['scientific-agents'],'researchDirections':['ai-for-science']},
                 {'id':'hidden','displayEligible':False,'researchTopics':['scientific-agents']}]
        annotate_categories(records)
        manifest=category_manifest(records);by={d['id']:d for d in manifest['directions']}
        self.assertEqual(by['ai-for-science']['count'],3)
        self.assertEqual(by['scientific-agents']['count'],2)
        self.assertEqual(by['ai-for-science']['name'],'AI for Science')
        self.assertEqual(by['scientific-agents']['name'],'Scientific Agents')
        ids=[d['id'] for d in manifest['directions']]
        self.assertEqual(ids.index('scientific-agents'),ids.index('ai-for-science')+1)
        self.assertEqual(by['ai-for-science']['section'],'Agent research')
        self.assertNotEqual(by['ai-for-science']['name'],by['scientific-agents']['name'])
        self.assertNotIn('ai-for-science',manifest['aliases'])

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
const fields=[...html.matchAll(/data-library-domain="([^"]+)"[^>]*><span>([^<]+)<\/span><small>(\d+)<\/small>/g)];
for(const [_,domain,name,count] of fields){
 nodes['library-domain-list'].onclick({target:{closest:()=>({dataset:{libraryDomain:domain}})}});
 const clicked=state.library.filter(c.matchesLibraryFilters).map(r=>r.id);
 assert.equal(clicked.length,Number(count));
 c.location.hash='#library?domain='+encodeURIComponent(domain);c.route();
 assert.equal(state.libraryDomain,domain,'Application field changed on reload');
 assert.equal(state.libraryDirection,'');
 assert.deepEqual(state.library.filter(c.matchesLibraryFilters).map(r=>r.id),clicked);
}
assert(fields.some(f=>f[1]==='Science & Research'));
assert.equal(new Set([...buttons,...fields].map(b=>b[2].toLowerCase())).size,buttons.length+fields.length);
state.libraryDomain='';
state.libraryDirection='';nodes['library-search'].value='AI for Science';c.showTypes();
assert.match(nodes['type-options'].children[0].textContent,/^AI for Science · Type · /);
nodes['type-options'].children[0].onclick();assert.equal(state.libraryDirection,'ai-for-science');
console.log('Verified all '+buttons.length+' categories: unique sidebar names, search, counts, click/reload membership and legacy links.');
'''
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)


if __name__=='__main__':unittest.main()

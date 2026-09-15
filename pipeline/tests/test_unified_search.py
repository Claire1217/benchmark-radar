import pathlib
import subprocess
import unittest

class UnifiedSearchTests(unittest.TestCase):
    def test_search_type_selection_and_keyboard(self):
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};
function element(){return {value:'',hidden:true,children:[],attrs:{},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},replaceChildren(){this.children=[]},append(b){this.children.push(b);nodes[b.id]=b},scrollIntoView(){}}}
for(const id of ['library-search','type-options','selected-type'])nodes[id]=element();
const state={library:[{researchDirections:['science'],applicationDomains:[]}],librarySearch:''};
const context={state,$:id=>nodes[id],document:{createElement:element,addEventListener(){}},
researchDefinitions:()=>[{id:'science',name:'AI for Science',description:'Scientific tasks',searchAliases:['AI Scientist']},{id:'self-improvement-rsi',name:'Self-Improvement & RSI',description:'Improving AI',searchAliases:['AI R&D']}],
displayEligible:()=>true,history:{replaceState(){}},renderLibrary(){},URLSearchParams,LIBRARY_PAGE_SIZE:120};
context.allResearchDefinitions=context.researchDefinitions;context.matchesDirection=(r,id)=>(r.researchDirections||[]).includes(id);
vm.createContext(context);
const app=fs.readFileSync('web/app.js','utf8');
vm.runInContext(app.slice(app.indexOf('let typeOptions='),app.indexOf('function setupLibraryNavigation')),context);
context.setupTypePicker();
const input=nodes['library-search'],list=nodes['type-options'];
function type(value){input.value=value;input.oninput({target:input})}
function key(key){input.onkeydown({key,preventDefault(){}})}
type('science');assert.equal(state.librarySearch,'science');assert.equal(list.hidden,false);assert.match(list.children[0].textContent,/AI for Science/);
key('Enter');assert.equal(state.librarySearch,'science');assert.equal(state.libraryDirection,undefined); // Plain Enter keeps text search.
type('science');list.children[0].onclick();assert.equal(state.libraryDirection,'science');assert.equal(input.value,'');assert.equal(state.librarySearch,'');assert.equal(list.hidden,true);
type('protein');assert.equal(state.librarySearch,'protein');assert.equal(state.libraryDirection,'science');assert.equal(list.hidden,true);
context.chooseType(null);assert.equal(state.libraryDirection,'');assert.equal(state.librarySearch,'protein');
type('science');key('ArrowDown');assert.equal(input.attrs['aria-activedescendant'],'type-option-0');key('Enter');assert.equal(state.libraryDirection,'science');
type('science');key('Escape');assert.equal(list.hidden,true);assert.equal(input.attrs['aria-expanded'],'false');
type('科学');assert.equal(list.hidden,false);key('Tab');assert.equal(list.hidden,true);
type('AI R&D');assert.match(list.children[0].textContent,/Self-Improvement/);
type('AI Scientist');assert.match(list.children[0].textContent,/AI for Science/);
assert(!fs.readFileSync('web/index.html','utf8').includes('id="type-query"'));
console.log('Unified search: text, click, keyboard, selected type, clear, aliases, dismissal passed');
'''
        subprocess.run(['node', '-e', script], cwd=pathlib.Path(__file__).resolve().parents[2], check=True)

/* Shared Library, Trends and CLI retrieval. Queries never alter entity identity. */
(function(root,factory){const policy=typeof module==='object'&&module.exports?require('./search-policy.js'):root.BenchmarkSearchPolicy;const api=factory(policy);if(typeof module==='object'&&module.exports)module.exports=api;root.BenchmarkSearch=api;})(typeof globalThis!=='undefined'?globalThis:this,function(policy){
'use strict';
const concepts=new Map(policy.concepts.map(c=>[c.id,c]));
const STOP=new Set('a an the for of in on and to with find benchmark benchmarks'.split(' '));
const SUFFIXES=['istry','ically','ical','ics','ing','ers','ies','ist','er','es','al','s','y'];
const normalize=s=>String(s||'').normalize('NFKC').replace(/([a-z0-9])([A-Z])/g,'$1 $2').replace(/([A-Z]+)([A-Z][a-z])/g,'$1 $2').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim().replace(/\s+/g,' ');
const identity=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}+.]+/gu,'');
const stem=w=>{for(const suffix of SUFFIXES)if(w.endsWith(suffix)&&w.length-suffix.length>=4)return w.slice(0,-suffix.length);return w;};
const aliases=policy.concepts.flatMap(c=>[c.label,...(c.aliases||[])].map(a=>({id:c.id,text:normalize(a)}))).sort((a,b)=>b.text.length-a.text.length||a.id.localeCompare(b.id));
const vocabulary=new Set(aliases.flatMap(a=>a.text.split(' ')).filter(t=>/^[a-z]{5,}$/.test(t)));
function oneEdit(a,b){if(a===b)return false;if(a.length===b.length){const dif=[];for(let i=0;i<a.length;i++)if(a[i]!==b[i])dif.push(i);return dif.length===1||(dif.length===2&&dif[1]===dif[0]+1&&a[dif[0]]===b[dif[1]]&&a[dif[1]]===b[dif[0]]);}if(Math.abs(a.length-b.length)!==1)return false;if(a.length>b.length)[a,b]=[b,a];let i=0,j=0,skip=0;while(i<a.length&&j<b.length){if(a[i]===b[j]){i++;j++;}else{j++;if(++skip>1)return false;}}return true;}
function compile(query,alternatives=[]){
 let normalized=normalize(query),corrections=[];
 normalized=normalized.split(' ').map(t=>{if(!/^[a-z]{5,}$/.test(t)||vocabulary.has(t))return t;const near=[...vocabulary].filter(v=>oneEdit(t,v));if(near.length===1){corrections.push({from:t,to:near[0]});return near[0];}return t;}).join(' ');
 const joined=aliases.find(a=>a.text.includes(' ')&&a.text.replace(/ /g,'')===normalized);if(joined)normalized=joined.text;
 let remainder=' '+normalized+' ';const groups=[],used=new Set(),expanded=[];
 for(const a of aliases){const chinese=/[^\x00-\x7f]/.test(a.text),needle=chinese?a.text:' '+a.text+' ';if(!a.text||!remainder.includes(needle))continue;if(!used.has(a.id)){used.add(a.id);groups.push({concept:a.id});const c=concepts.get(a.id);expanded.push(c.label,...(c.aliases||[]));}remainder=remainder.split(needle).join(' ');}
 for(const t of normalize(remainder).split(' ').filter(t=>t&&!STOP.has(t)))groups.push({term:stem(t)});
 const variants=alternatives.map(q=>compile(q));
 return {original:query,normalized,groups,corrections,expandedTerms:[...new Set(expanded.map(x=>x.toLowerCase()))],variants,empty:!String(query||'').trim()&&!alternatives.length};
}
const prepared=new WeakMap(),queries=new Map();
function queryFor(q){if(typeof q!=='string')return q;if(!queries.has(q)){if(queries.size>128)queries.clear();queries.set(q,compile(q));}return queries.get(q);}
function prepare(record){
 if(prepared.has(record))return prepared.get(record);
 const d=record.searchDocument||{},facts=d.concepts||[],ids=new Set(facts.map(f=>typeof f==='string'?f:f.id));
 for(const id of [...ids]){let c=concepts.get(id);while(c&&c.parent){ids.add(c.parent);c=concepts.get(c.parent);}}
 const raw={name:record.name||d.name||'',aliases:[...(record.aliases||d.aliases||[])].join(' '),description:record.description||d.description||record.oneLine||'',evidence:d.sourceText||(record.evidence||{}).snippet||''};
 const fields=Object.fromEntries(Object.entries(raw).map(([k,v])=>[k,{text:normalize(v),tokens:new Set(normalize(v).split(' ').map(stem))}]));
 const result={raw,fields,ids,facts};prepared.set(record,result);return result;
}
const conceptForms=new Map(policy.concepts.map(c=>[c.id,[c.label,...(c.aliases||[])].map(normalize).filter(a=>a.length>3&&a!=='code').map(text=>({text,tokens:text.split(' ').map(stem)}))]));
function conceptInField(id,field){return (conceptForms.get(id)||[]).some(a=>a.tokens.length>1?(' '+field.text+' ').includes(' '+a.text+' '):a.tokens.every(t=>field.tokens.has(t)));}

function match(record,query){
 if(record.displayEligible===false||record.evaluationMode==='viewpoint_probe')return null;
 const q=queryFor(query),p=prepare(record);if(p.lastQuery===q)return p.lastMatch;if(q.empty)return {score:0,exactMatch:null,matchedFields:[],matchedConcepts:[],snippet:''};
 const qid=identity(q.original),name=identity(record.name),alias=(record.aliases||[]).some(a=>identity(a)===qid);
 let exact=null,score=0;if(String(record.id||'').toLowerCase()===String(q.original||'').trim().toLowerCase()){exact='id';score=2000;}else if(qid&&qid===name){exact='name';score=1000;}else if(qid&&alias){exact='alias';score=950;}
 let matched=0;const fields=new Set(),matchedConcepts=[];
 for(const group of q.groups){let yes=false;
  if(group.concept&&p.ids.has(group.concept)){yes=true;score+=25;fields.add('evidence');matchedConcepts.push(...p.facts.filter(f=>f.id===group.concept));}
  for(const [key,field] of Object.entries(p.fields)){if(group.concept&&key==='domains')continue;const ok=group.concept?conceptInField(group.concept,field):field.tokens.has(group.term);if(ok){yes=true;score+=({name:10,aliases:8,description:4,evidence:3,domains:1})[key];fields.add(key);}}
  if(yes)matched++;
 }
 const required=q.groups.length>=4?Math.ceil(q.groups.length*.7):q.groups.length;
 const compact=normalize(record.name).replace(/ /g,''),needle=q.normalized.replace(/ /g,'');
 const joinedName=needle.length>=5&&compact.includes(needle);
 let result=null;
 if(exact||(q.groups.length&&matched>=required)||joinedName){score+=matched*20+(q.groups.length?matched/q.groups.length*20:0)+(joinedName?50:0);result={score,exactMatch:exact,matchedFields:[...fields],matchedConcepts,snippet:matchedConcepts[0]?.quote||p.raw.description||p.raw.evidence||record.name};}
 for(const variant of q.variants){const other=match(record,variant);if(other&&(!result||other.score>result.score))result=other;}
 p.lastQuery=q;p.lastMatch=result;return result;
}
function search(records,query,alternatives=[]){const compiled=compile(query,alternatives),hits={};for(const record of records){const m=match(record,compiled);if(m)hits[record.id]=m;}return {hits,meta:{original:query,normalized:compiled.normalized,corrections:compiled.corrections,expandedTerms:[...new Set([...compiled.expandedTerms,...compiled.variants.flatMap(v=>[v.normalized,...v.expandedTerms])])],method:'shared-evidence-search-v1',matchPolicy:'All concepts for short queries; at least 70% for queries with four or more concepts. Explicit alternatives are OR.',languageSupport:'Controlled concepts, Unicode normalization and conservative vocabulary typo recovery.'}};}
function compare(a,b,query){return (match(b,query)?.score||0)-(match(a,query)?.score||0)||String(a.name).localeCompare(String(b.name))||String(a.id).localeCompare(String(b.id));}
return {normalize,identity,compile,prepare,match,search,compare,matchesText:(text,query)=>!!match({name:text,description:text},query)};
});

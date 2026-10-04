// User-built Trends directions: a keyword (or several) gathers related benchmarks
// into an entry that stays in the list. Pure functions; trends.js owns the DOM.
const Directions=(()=>{
const STORE='benchmark-radar:trends:directions:v1';
const SUFFIXES=['istry','ically','ical','ics','ing','ers','ies','er','es','al','s','y'];
const STOP=new Set('a an and are as at be by for from in into is it its of on or that the their this to with via using use used based new across over under than more most both each such can which while within without between toward towards benchmark benchmarks benchmarking evaluate evaluates evaluated evaluating evaluation evaluations model models llm llms language large task tasks dataset datasets data test tests testing suite performance capability capabilities ability abilities agent agents ai system systems set sets problem problems question questions answer answers real world realworld level levels multiple different covering covers including includes measure measures measuring assess assesses assessing study we our paper introduce introduces proposed propose provides provide human humans score scores scoring bench through long term short high low large small general generating generated generate production correctness curated experts expert five four three two one dimensions choice domain diverse comprehensive novel challenging hard open various specific realistic'.split(' '));
// Split camelCase and acronym joins so "PDEBench" also reads as "PDE Bench".
const words=text=>String(text||'').replace(/([a-z0-9])([A-Z])/g,'$1 $2').replace(/([A-Z]+)([A-Z][a-z])/g,'$1 $2').toLowerCase().match(/[a-z0-9]+/g)||[];
function stem(word){word=word.toLowerCase();for(const s of SUFFIXES)if(word.endsWith(s)&&word.length-s.length>=4)return word.slice(0,-s.length);return word;}
const escapeRe=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
// Long words match by stem ("chemistry" ~ chemical, chemist); short ones (PDE, GPU) match whole words or plurals.
function wordPattern(w){const s=stem(w);return s.length>=4?escapeRe(s)+'[a-z0-9]*':escapeRe(w)+'s?(?![a-z0-9])';}
function termRegex(term){const parts=words(term);if(!parts.length)return null;return new RegExp('(?:^|[^a-z0-9])'+parts.map(wordPattern).join('[^a-z0-9]+'));}
// "GPU, CUDA kernels" -> ["gpu","cuda kernels"]: commas separate terms, spaces form a phrase.
const parseTerms=q=>[...new Set(String(q||'').split(/[,;|]/).map(t=>words(t).join(' ')).filter(t=>t.length>=2))];
const haystack=row=>words(row[0]+' '+row[5]+' '+row[3]).join(' ');
function matches(rows,terms){const res=terms.map(termRegex).filter(Boolean);if(!res.length)return [];return rows.filter(r=>{const h=' '+(r._hay??=haystack(r));return res.some(re=>re.test(h))});}
// Words that are frequent in the matched benchmarks but rare overall, offered as extra terms.
function related(all,matched,terms,limit=8){
 if(matched.length<2)return [];
 const df=all._df??=(()=>{const m=new Map();for(const r of all)for(const w of new Set((r._hay??=haystack(r)).split(' ')))m.set(w,(m.get(w)||0)+1);return m})();
 const inMatch=new Map();for(const r of matched)for(const w of new Set(r._hay.split(' ')))inMatch.set(w,(inMatch.get(w)||0)+1);
 const taken=new Set(terms.flatMap(t=>words(t).map(stem)));
 const scored=[];
 for(const [w,n] of inMatch){if(n<2||w.length<4||STOP.has(w)||/^\d+$/.test(w)||taken.has(stem(w)))continue;
  if(df.get(w)>all.length*0.05)continue;// too general to define a direction
  const extra=(df.get(w)||0)-n;if(extra<1)continue;// must add benchmarks, not only restate the current ones
  scored.push([w,(n/matched.length)*Math.log(all.length/df.get(w)),extra]);}
 const seen=new Set();return scored.sort((a,b)=>b[1]-a[1]).filter(([w])=>{const s=stem(w);if(seen.has(s))return false;seen.add(s);return true}).slice(0,limit).map(([w,,extra])=>({term:w,adds:extra}));
}
const slug=terms=>terms.join('+').replace(/\s+/g,'-');
const title=terms=>terms.map(t=>t.length<=4?t.toUpperCase():t.replace(/\b[a-z]/g,c=>c.toUpperCase())).join(' / ');
const make=terms=>({id:'custom:'+slug(terms),name:title(terms),terms});
function load(storage){try{const list=JSON.parse(storage.getItem(STORE)||'[]');return Array.isArray(list)?list.filter(d=>Array.isArray(d.terms)&&d.terms.length).map(d=>make(d.terms)):[]}catch{return []}}
function save(storage,list){try{storage.setItem(STORE,JSON.stringify(list.map(d=>({terms:d.terms}))))}catch{}}
// Shareable link: #d=gpu,cuda
const toHash=terms=>'#d='+terms.map(encodeURIComponent).join(',');
const fromHash=hash=>{const m=/^#d=(.+)$/.exec(hash||'');return m?parseTerms(m[1].split(',').map(decodeURIComponent).join(',')):[]};
return {words,stem,termRegex,parseTerms,matches,related,make,load,save,toHash,fromHash,STORE};
})();
if(typeof module!=='undefined')module.exports=Directions;

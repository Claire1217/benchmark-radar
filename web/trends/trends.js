const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// Radar, Library and Trends share one title renderer.
const titleHtml=benchmarkNameHtml;

const fmt=n=>n==null?'—':n.toLocaleString('en-US'), signed=n=>n==null?'—':(n>0?'+':'')+fmt(n);
const day=86400000, date=(s,offset=0)=>new Date(Date.parse(s+'T00:00:00Z')+offset*day).toISOString().slice(0,10), short=s=>s.slice(5).replace('-','/');

// User-built directions: keywords gather related benchmarks into an entry that stays in the list.
let SEARCH=null,DRAFT=null,wantDraft=false;const store=(()=>{try{return localStorage}catch{return null}})();
let SAVED=store?Directions.load(store):[];
const shiftMonths=(s,m)=>{const d=new Date(s+'T00:00:00Z'),n=d.getUTCFullYear()*12+d.getUTCMonth()+m,y=Math.floor(n/12),mo=n%12,last=new Date(Date.UTC(y,mo+1,0)).getUTCDate();return new Date(Date.UTC(y,mo,Math.min(d.getUTCDate(),last))).toISOString().slice(0,10)};
const topicCache=new Map();
function directionTopic(dir,draft=false){if(!SEARCH)return null;const key=dir.id+'|'+draft;if(topicCache.has(key))return topicCache.get(key);
const all=Directions.matches(SEARCH.releases,dir.terms),rows=all.filter(r=>r[1]);
const relEnd=DATA.endExclusive,starEnd=DATA.starEndExclusive,ws=SEARCH.weekStart,windows={};
const repoIds=[...new Set(all.flatMap(r=>r[7]))];
const weekDate=i=>date(ws,7*i);
for(const m of [1,3,6,12]){const rs=shiftMonths(relEnd,-m),rp=shiftMonths(rs,-m);const cur=rows.filter(r=>r[1]>=rs&&r[1]<relEnd),prior=rows.filter(r=>r[1]>=rp&&r[1]<rs);
let b=[];if(m>=6){for(let i=0;i<=m;i++)b.push(shiftMonths(relEnd,-m+i))}else{b=[rs];while(b[b.length-1]<relEnd){const n=date(b[b.length-1],m===1?1:7);b.push(n<relEnd?n:relEnd)}}
const relValues=b.slice(0,-1).map((a,i)=>cur.filter(r=>r[1]>=a&&r[1]<b[i+1]).length);
const ss=shiftMonths(starEnd,-m),sp=shiftMonths(ss,-m);const inWin=(i,a,z)=>{const d=weekDate(i);return d>=a&&d<z};
const repos=repoIds.map(k=>{const [url,weekly,base]=SEARCH.repos[k];let stars=0,prev=0,before=base;weekly.forEach((n,i)=>{if(inWin(i,ss,starEnd))stars+=n;else if(weekDate(i)<ss){before+=n;if(weekDate(i)>=sp)prev+=n}});return {url,name:url.replace(/^https:\/\/github\.com\//,''),names:all.filter(r=>r[7].includes(k)).map(r=>r[0]),stars,previous:prev,baseline:before}}).sort((a,b)=>b.stars-a.stars);
const sb=[];for(let i=0;i<SEARCH.weeks;i++)if(inWin(i,ss,starEnd))sb.push(i);
const starValues=sb.map(i=>repoIds.reduce((s,k)=>s+SEARCH.repos[k][1][i],0));
const total=repos.reduce((s,r)=>s+r.stars,0),base=repos.reduce((s,r)=>s+r.baseline,0);
windows[m]={start:rs,previousStart:rp,starStart:ss,starPreviousStart:sp,count:cur.length,observedCount:cur.length,previous:prior.length,delta:cur.length-prior.length,
releaseChart:{values:relValues,dates:b,unit:m>=6?'monthly':m===1?'daily':'weekly'},
starChart:{values:repos.length?starValues:sb.map(()=>null),dates:[...sb.map(weekDate),starEnd],unit:'weekly'},
releases:cur.slice().reverse().map(r=>({name:r[0],date:r[1],description:r[3],url:r[4],dateBasis:'released'})),repos,stars:repos.length?total:null,baseline:repos.length?base:null}}
const used=all.filter(r=>r[6].length).sort((a,b)=>b[6].length-a[6].length).map(r=>({name:r[0],reports:r[6].map(provider=>({provider,url:'../#library?q='+encodeURIComponent(r[0])}))}));
const cats={};all.forEach(r=>r[2].forEach(i=>cats[i]=(cats[i]||0)+1));
const top=Object.entries(cats).sort((a,b)=>b[1]-a[1]).slice(0,3).map(([i])=>DATA.topics.find(t=>t.id===SEARCH.categories[i])?.name).filter(Boolean);
const undated=all.length-rows.length;
const topic={...dir,custom:true,draft,windows,trackedUse:used,library:all.length,undated,related:Directions.related(SEARCH.releases,all,dir.terms),
description:`${all.length} Library benchmarks match ${dir.terms.map(t=>'“'+t+'”').join(' or ')}${undated?` (${undated} without an exact date are listed but not charted)`:''}.${top.length?' Mostly in: '+top.join(', ')+'.':''}`};
topicCache.set(key,topic);return topic;}
function loadSearch(){if(SEARCH)return Promise.resolve(SEARCH);return fetch('../data/trends_search.json').then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(d=>SEARCH=d)}
const customTopics=()=>SEARCH?[...(DRAFT?[directionTopic(DRAFT,true)]:[]),...SAVED.filter(d=>!DRAFT||d.id!==DRAFT.id).map(d=>directionTopic(d))].filter(Boolean):[];
const findTopic=id=>customTopics().find(t=>t.id===id)||DATA.topics.find(t=>t.id===id);
function setHash(terms){try{history.replaceState(null,'',terms?Directions.toHash(terms):location.pathname+location.search)}catch{}}
function keep(){if(!DRAFT)return;if(!SAVED.some(d=>d.id===DRAFT.id))SAVED.unshift(DRAFT);if(store)Directions.save(store,SAVED);selected=DRAFT.id;setHash(DRAFT.terms);DRAFT=null;$('search').value='';render()}
function removeSaved(id){SAVED=SAVED.filter(d=>d.id!==id);if(store)Directions.save(store,SAVED);topicCache.clear();if(selected===id)selected=null;setHash(null);render()}
function editTerms(id,terms){terms=[...new Set(terms)];if(!terms.length)return;const next=Directions.make(terms);
 if(DRAFT&&DRAFT.id===id){$('search').value=terms.join(', ');wantDraft=true;}
 else{SAVED=SAVED.map(d=>d.id===id?next:d);if(store)Directions.save(store,SAVED);setHash(terms);}
 selected=next.id;render()}
let layout=(()=>{try{return localStorage.getItem('benchmark-radar:trends:layout')||'group'}catch{return 'group'}})();
let DATA,mode='release',selected='agentic-coding',sort='count',ascending=false,showAll=false;
const periods={release:12,star:3}, current=t=>t.windows[String(periods[mode])];
function values(t){const w=current(t),star=mode==='star',series=star?w.starChart:w.releaseChart;
const p=star?(w.stars==null?null:w.repos.reduce((s,r)=>s+r.previous,0)):w.previous;
return {n:star?w.stars:w.count,p,delta:star?(w.stars==null?null:w.stars-p):w.delta,bars:series.values,dates:series.dates,unit:series.unit};}
function spark(v){if(v.n==null)return '<small>No history</small>';const max=Math.max(1,...v.bars);
return `<span class="spark" aria-label="${v.unit} counts; each row uses its own scale">${v.bars.map((n,i)=>`<i style="height:${n===0?1:n/max*30}px;opacity:${n===0?.3:1}" title="${short(v.dates[i])}–${short(date(v.dates[i+1],-1))}: ${fmt(n)}"></i>`).join('')}</span>`;}
function render(){if(!DATA)return;const star=mode==='star',w=current(DATA.topics[0]);$('window').value=String(periods[mode]);$('rankingTitle').textContent='Research directions · '+(star?'Attention growth':'New releases');$('countLabel').textContent=star?'New stars':'New';$('window').title=`Data through ${star?DATA.starAsOf:DATA.asOf}`;$('trendLabel').textContent='Recent trend';$('comparisonLabel').textContent='vs. previous period';['release','star'].forEach(m=>{$(m+'Tab').classList.toggle('active',mode===m);$(m+'Tab').setAttribute('aria-pressed',String(mode===m))});['group','all'].forEach(l=>{const b=$(l+'Layout');if(b){b.classList.toggle('active',layout===l);b.setAttribute('aria-pressed',String(layout===l))}});for(const key of ['count','delta']){const active=sort===key;$(key+'Arrow').textContent=active?(ascending?'↑':'↓'):'↕';$(key+'Sort').setAttribute('aria-pressed',String(active));$(key+'Sort').title=(key==='delta'?`${short(star?w.starStart:w.start)}–${short(star?DATA.starAsOf:DATA.asOf)} vs. ${short(star?w.starPreviousStart:w.previousStart)}–${short(date(star?w.starStart:w.start,-1))}. `:'')+'Click to sort '+(active&&!ascending?'ascending':'descending')}
const q=$('search').value.trim();const terms=Directions.parseTerms(q);DRAFT=q.length>=2&&terms.length?Directions.make(terms):null;
if(DRAFT&&SEARCH&&!Directions.matches(SEARCH.releases,DRAFT.terms).length)DRAFT=null;
const mine=customTopics(),lq=q.toLowerCase();
const topics=DATA.topics.filter(t=>!lq||t.name.toLowerCase().includes(lq)||(t.description||'').toLowerCase().includes(lq)).sort((a,b)=>{const x=values(a)[sort==='count'?'n':'delta'],y=values(b)[sort==='count'?'n':'delta'];return x==null?(y==null?a.name.localeCompare(b.name):1):y==null?-1:(ascending?1:-1)*(x-y)||a.name.localeCompare(b.name)});
const rows=[...mine,...topics];
if(DRAFT&&wantDraft&&SEARCH){selected=DRAFT.id;wantDraft=false;}if(!rows.some(t=>t.id===selected)){selected=rows[0]?.id||null;showAll=false;}
const total=DATA.releaseTotals[String(periods.release)];
const row=t=>{const v=values(t),w=current(t);const tag=t.draft?'<em class="tag-new">New direction</em> ':t.custom?'<em class="tag-mine">Yours</em> ':'';return `<button class="direction ${selected===t.id?'selected':''}" data-id="${esc(t.id)}" aria-pressed="${selected===t.id}"><span class="name">${tag}${esc(t.name)}${star?'':`<small>${t.custom?`${t.library} in Library · `:''}${v.n!=null&&total?`${(v.n/total*100).toFixed(1)}% of indexed releases`:`${w.observedCount} observed · partial coverage`}</small>`}</span><span class="num">${fmt(v.n)}</span><span title="${star?'Change in new stars':'Indexed releases: '+v.n+' this period; '+v.p+' previous period. Historical coverage may differ.'}" class="num delta ${v.delta>0?'':'down'}">${signed(v.delta)}</span>${spark(v)}</button>`};
const loading=q.length>=2&&!SEARCH?'<div class="empty load-error">Loading keyword index…</div>':'';
const noMatch=q.length>=2&&SEARCH&&!DRAFT?`<div class="empty load-error">No benchmarks match “${esc(q)}”. Try a broader word, or separate alternatives with commas.</div>`:'';
$('rows').innerHTML=loading+noMatch+(mine.length?'<div class="group-label">Your directions</div>'+mine.map(row).join('')+(topics.length&&!(layout==='group'&&DATA.groups?.length)?'<div class="group-label">Categories</div>':''):'')+(layout==='group'&&DATA.groups?.length?DATA.groups.map(g=>{const ts=topics.filter(t=>t.group===g.id);return ts.length?`<div class="group-label">${esc(g.name)}</div>`+ts.map(row).join(''):''}).join(''):topics.map(row).join(''))||'<div class="empty load-error">No matching categories or benchmarks.</div>';
$('tableNote').textContent=star?`Star history through ${DATA.starAsOf}. ${DATA.coverage.includedHistories} repositories included; ${DATA.coverage.fetchedCompleteHistories}/${DATA.coverage.requestedHistories} histories fetched. Each repository counts once per topic. Charts show recorded new stars within the selected period; the final weekly bin may be shorter. Mini charts use a separate scale for each direction. Change compares new stars with the preceding calendar period, not a loss of existing stars. Topics overlap; missing history is not zero.`:`Indexed benchmark families, deduplicated. Topics overlap; counts are not additive. Mini charts use a separate scale for each direction. Weekly bins start at the period boundary; the final bin may be shorter. Changes compare indexed counts, not overall research activity; historical coverage and later backfills can affect comparisons. ${DATA.coverage.familiesMissingExactDate} families lack an exact release date; ${DATA.coverage.familiesExcludedAsVariantsOrDisclosures} variants or disclosures are excluded from independent release counts.`;detail()}
function chart(t){const v=values(t),w=current(t),star=mode==='star',start=star?w.starStart:w.start,end=star?DATA.starAsOf:DATA.asOf,prior=star?w.starPreviousStart:w.previousStart;
if(v.n==null)return '<div class="compact-chart empty">No complete repository history available.</div>';
const max=Math.max(1,...v.bars),scale=Math.max(1,Math.ceil(max/4)*4),dense=v.bars.length>16;
const label=star?'new stars':'releases';
return `<div class="compact-chart"><div class="charttitle"><strong>${star?'New stars':'New releases'}</strong><span>${v.unit[0].toUpperCase()+v.unit.slice(1)} totals</span></div>
<div class="period-summary"><strong>${fmt(v.n)}</strong> ${label} · ${short(start)}–${short(end)}<br><span>${short(prior)}–${short(date(start,-1))}: ${fmt(v.p)} · Change ${signed(v.delta)}</span></div>
<div class="plot"><div class="plot-scale"><span>${fmt(scale)}</span><span>${fmt(scale/2)}</span><span>0</span></div><div class="bars ${dense?'dense-bars':''}" role="img" aria-label="${label} from ${start} to ${end}; total ${v.n}">${v.bars.map((n,i)=>`<div class="bar ${n===0?'zero-bar':''}" style="height:${n/scale*100}%" title="${short(v.dates[i])}–${short(date(v.dates[i+1],-1))}: ${fmt(n)} ${label}"><b>${fmt(n)}</b></div>`).join('')}</div></div>
<div class="axis"><span>${short(start)}</span><span>${short(end)}</span></div></div>`;}
function customControls(t){const chips=t.terms.map(x=>`<span class="chip">${esc(x)}${t.terms.length>1?`<button type="button" data-act="drop" data-term="${esc(x)}" aria-label="Remove ${esc(x)}">×</button>`:''}</span>`).join('');
const rel=t.related.length?`<div class="related"><span>Add related:</span>${t.related.map(r=>`<button type="button" class="chip add" data-act="add" data-term="${esc(r.term)}" title="Adds ${r.adds} more benchmarks">+ ${esc(r.term)}</button>`).join('')}</div>`:'';
const actions=t.draft?`<button type="button" class="secondary primary" data-act="keep">Keep as direction</button>`:`<button type="button" class="secondary" data-act="share">Copy link</button><button type="button" class="secondary" data-act="remove">Remove</button>`;
return `<div class="custom-controls"><div class="chips">${chips}</div>${rel}<div class="custom-actions">${actions}</div></div>`}
function detail(){const t=findTopic(selected);if(!t){$('detail').innerHTML='<div class="empty">No matching research directions.</div>';return;}const w=current(t),star=mode==='star';const items=star?w.repos.filter(r=>r.stars>0):w.releases;const list=items.slice(0,showAll?items.length:5).map(r=>star?`<article class="record"><div class="record-top"><a href="${esc(r.url)}" target="_blank" rel="noopener"><strong>${titleHtml(r.name)}</strong></a><span class="delta">+${fmt(r.stars)}</span></div><p>${esc(r.names.join(' · '))}</p></article>`:`<article class="record"><div class="record-top"><strong><a href="${esc(r.url||'../#library?'+(t.custom?'d='+encodeURIComponent(t.terms.join(',')):'direction='+t.id))}" target="_blank" rel="noopener">${titleHtml(r.name)}</a></strong><time title="${r.dateBasis==='paper-v1'?'First paper publication':r.dateBasis==='official-announcement'?'Official announcement':'Release date'}">${esc(r.date)}</time></div><p>${esc(r.description)}</p></article>`).join('');$('detail').innerHTML=`<div class="detail-top"><div class="eyebrow">${t.draft?'New direction':t.custom?'Your direction':'Direction focus'}</div><span class="pill">${star?'GitHub history':'Indexed releases'}</span></div><h2 style="margin-top:12px;font-size:25px">${esc(t.name)}</h2><p class="direction-description">${esc(t.description)}</p>${t.custom?customControls(t):''}${chart(t)}<div class="sectionline"><h3>${star?'Repositories driving attention':'Recent releases'}</h3>${list||'<p>No recorded activity in this period.</p>'}<div class="detail-footer">${items.length>5?`<button class="secondary" id="more">${showAll?'Show less':'Show all'}</button>`:'<span></span>'}<a class="secondary" href="../#library?${t.custom?'d='+encodeURIComponent(t.terms.join(',')):'direction='+encodeURIComponent(t.id)}">View in Library ↗</a></div></div><div class="sectionline"><h3>Adoption in model reports</h3><p>Current snapshot · Tracked sources</p>${t.trackedUse.slice(0,3).map(r=>`<div class="record"><strong>${titleHtml(r.name)}</strong><div class="links" style="margin-top:9px">${r.reports.map(x=>`<a href="${esc(x.url||x.sourceUrl)}" target="_blank" rel="noopener">${esc(x.provider)} ↗</a>`).join('')}</div></div>`).join('')||'<p>No model-report references linked to this topic yet.</p>'}</div>`;if($('more'))$('more').onclick=()=>{showAll=!showAll;detail()}}
document.addEventListener('click',e=>{const act=e.target.closest('[data-act]');if(act){const t=findTopic(selected);if(!t)return;const term=act.dataset.term;
 if(act.dataset.act==='keep')keep();else if(act.dataset.act==='remove')removeSaved(t.id);else if(act.dataset.act==='add')editTerms(t.id,[...t.terms,term]);else if(act.dataset.act==='drop')editTerms(t.id,t.terms.filter(x=>x!==term));
 else if(act.dataset.act==='share'){const url=location.origin+location.pathname+Directions.toHash(t.terms);setHash(t.terms);try{navigator.clipboard.writeText(url);act.textContent='Link copied'}catch{act.textContent=url}}return;}
 const row=e.target.closest('[data-id]');if(row&&String(row.dataset.id).startsWith('custom:')){const d=findTopic(row.dataset.id);if(d&&!d.draft)setHash(d.terms);}if(!row)return;selected=row.dataset.id;showAll=false;document.querySelectorAll('#rows [data-id]').forEach(el=>{const active=el.dataset.id===selected;el.classList.toggle('selected',active);el.setAttribute('aria-pressed',String(active))});detail()});
['release','star'].forEach(m=>$(m+'Tab').onclick=()=>{mode=m;showAll=false;render()});['group','all'].forEach(l=>{const b=$(l+'Layout');if(b)b.onclick=()=>{layout=l;try{localStorage.setItem('benchmark-radar:trends:layout',l)}catch{}render()}});$('window').onchange=()=>{periods[mode]=Number($('window').value);showAll=false;render()};$('search').onkeydown=e=>{if(e.key==='Enter'&&DRAFT){e.preventDefault();keep()}};$('search').oninput=()=>{wantDraft=$('search').value.trim().length>=2;if($('search').value.trim().length>=2&&!SEARCH)loadSearch().then(render).catch(e=>console.error('Keyword index failed:',e));render()};['count','delta'].forEach(k=>$(k+'Sort').onclick=()=>{ascending=sort===k?!ascending:false;sort=k;render()});

// A pasted share link (#d=...) opens that direction even when the page is already loaded.
function openShared(){const terms=Directions.fromHash(location.hash);if(!terms.length||!DATA)return;const id=Directions.make(terms).id;if(SAVED.some(d=>d.id===id)){selected=id;render();return}$('search').value=terms.join(', ');wantDraft=true;render();loadSearch().then(render).catch(e=>console.error('Keyword index failed:',e))}
if(typeof window.addEventListener==='function')window.addEventListener('hashchange',openShared);
$('rows').innerHTML='<div class="empty load-error">Loading Trends…</div>';
fetch('../data/trends_topics.json').then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(data=>{DATA=data;window.trendsData=data;periods.release=data.defaultReleaseMonths;periods.star=data.defaultStarMonths;$('window').title=`Data through ${data.asOf}`;const shared=typeof location!=='undefined'?Directions.fromHash(location.hash):[];if(shared.length){$('search').value=shared.join(', ');wantDraft=true;}render();if(shared.length||SAVED.length)loadSearch().then(render).catch(e=>console.error('Keyword index failed:',e))}).catch(e=>{console.error('Trends initialization failed:',e);$('rows').innerHTML='<div class="empty load-error">Unable to load Trends. Please refresh.</div>'});
try{$('saved-count').textContent=JSON.parse(localStorage.getItem('benchmark-radar:watchlist:v1')||'[]').length}catch{}

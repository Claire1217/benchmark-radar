const FOLLOWING_KEY='benchmark-radar:interest-list:v1';
let following={ids:[],view:'all'};
let filterAfterSave=false;
try{const stored=JSON.parse(localStorage.getItem(FOLLOWING_KEY)||'null');if(stored&&Array.isArray(stored.ids)){following.ids=[...new Set(stored.ids.filter(x=>typeof x==='string'))];following.view=following.ids.length&&stored.view==='following'?'following':'all';}}catch{}
function followsRecord(r){return following.ids.some(id=>matchesDirection(r,id));}
function followingRows(rows){const unique=[...new Map(rows.map(r=>[r.id,r])).values()];return state.savedOnly||following.view==='all'||!following.ids.length?unique:unique.filter(followsRecord);}
function storeFollowing(){try{localStorage.setItem(FOLLOWING_KEY,JSON.stringify(following));$('following-storage').hidden=true;}catch{$('following-storage').hidden=false;}}
function followingEmpty(){return following.view==='following'&&following.ids.length?'No new benchmarks from your interests in this time range.<div class="field-empty-actions"><button class="following-inline" onclick="event.stopPropagation();openFollowing()">Edit interests</button><button class="following-inline" onclick="clearFields()">View all updates</button></div>':'No benchmarks in this view.';}
function clearFields(){following.view='all';storeFollowing();renderRadar();}
function updateFollowing(){
 $('following-bar').hidden=state.savedOnly;
 const names=researchDefinitions().filter(d=>following.ids.includes(d.id)).map(d=>d.name);
 $('following-label').textContent=names.length?'Edit interests':'Create my list';
 $('following-edit').title=names.length?names.join(', '):'Save the research directions you care about';
 $('following-edit').setAttribute('aria-label',names.length?'Edit interests':'Create my interest list');
 $('interest-only').checked=following.view==='following';
 $('interest-list-summary').textContent=names.length?names.join(' · '):'Save your interests. Come back for new benchmarks.';
 $('interest-list-summary').title=names.join(', ');

}
function closeFields(){ filterAfterSave=false;$('following-dialog').hidden=true;$('following-edit').setAttribute('aria-expanded','false');$('following-edit').focus(); }
function openFollowing(){
 const panel=$('following-dialog');
 $('following-options').innerHTML=researchDefinitions().map(d=>`<label class="following-option"><input type="checkbox" value="${escapeHtml(d.id)}" ${following.ids.includes(d.id)?'checked':''}><span>${escapeHtml(d.name)}</span></label>`).join('');
 $('following-selected').textContent=following.ids.length?`${following.ids.length} selected`:'Select directions for your list';
 panel.hidden=false;$('following-edit').setAttribute('aria-expanded','true');panel.querySelector('input')?.focus();
}
function setupFollowing(){
 following.ids=following.ids.filter(id=>researchDefinitions().some(d=>d.id===id));
 if(!following.ids.length)following.view='all';
 $('following-edit').onclick=()=>$('following-dialog').hidden?openFollowing():closeFields();
 $('interest-only').onchange=()=>{if($('interest-only').checked&&!following.ids.length){$('interest-only').checked=false;openFollowing();filterAfterSave=true;return;}following.view=$('interest-only').checked?'following':'all';storeFollowing();renderRadar();};
 $('following-options').onchange=()=>{const count=$('following-options').querySelectorAll('input:checked').length;$('following-selected').textContent=count?`${count} selected`:'Select directions for your list';};
 $('following-apply').onclick=()=>{following.ids=[...document.querySelectorAll('#following-options input:checked')].map(el=>el.value);if(!following.ids.length)following.view='all';else if(filterAfterSave)following.view='following';state.visible=RADAR_PAGE_SIZE;storeFollowing();closeFields();renderRadar();};
 $('following-clear').onclick=()=>{document.querySelectorAll('#following-options input').forEach(el=>el.checked=false);$('following-selected').textContent='Select directions for your list';};
 $('following-cancel').onclick=closeFields;
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('following-dialog').hidden){e.preventDefault();closeFields();}});
 document.addEventListener('click',e=>{if(!$('following-dialog').hidden&&!$('following-bar').contains(e.target))closeFields();});
 window.addEventListener('hashchange',()=>{if(!$('following-dialog').hidden)closeFields();});
}

function interestChips(r){
 const followed=researchDefinitions().filter(d=>following.ids.includes(d.id)&&matchesDirection(r,d.id)).map(d=>d.name);
 const names=[...new Set([...directionChips(r),...followed])];
 const tags=names.map(name=>`<span>${escapeHtml(name)}</span>`).join('');
 return tags+(followed.length?`<span class="interest-marker" title="Matches your interests: ${escapeHtml(followed.join(', '))}">Interested</span>`:'');
}

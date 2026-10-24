// Build real first-screen cards with the same renderer used by the browser.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const nodes = new Map();
const node = id => {
  if (!nodes.has(id)) nodes.set(id, {innerHTML:'', textContent:'', hidden:false, dataset:{}, setAttribute(){}});
  return nodes.get(id);
};
const context = {
  console, URLSearchParams, location:{hash:''}, window:{},
  localStorage:{getItem:()=>null}, fetch:()=>new Promise(()=>{}),
  document:{getElementById:node, querySelectorAll:()=>[]},
};
vm.createContext(context);
for (const name of ['search-policy.js', 'search.js', 'benchmark-name.js', 'trends/directions.js', 'following.js', 'app.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, 'web', name), 'utf8'), context);
}
context.input = input;
vm.runInContext(`state.benchmarks=input.records; state.manifest=input.manifest;
  state.libraryManifest=input.libraryManifest; state.bootstrapPreviousDate=input.previousDate;
  state.radarComplete=false; state.latestFrom=latestAvailableDate(); renderRadar();`, context);
process.stdout.write(JSON.stringify(Object.fromEntries(
  ['benchmark-list','summary','result-count','updated','feed-title','load-more'].map(id=>[id,node(id)])
)));

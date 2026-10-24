// Diagnostic adapter for the actual Library predicate. No alternate search implementation.
// Fails loudly if the browser function layout changes; does not silently use a replica.
const fs = require('node:fs');
const vm = require('node:vm');
const app = fs.readFileSync(process.argv[2], 'utf8');
const {library, cases} = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const state = {libraryManifest: library.manifest};
const context = vm.createContext({state});
for (const name of ['displayEligible', 'researchDefinitions', 'allResearchDefinitions', 'topicIds']) {
  const lines = app.split('\n').filter(line => line.startsWith(`function ${name}(`));
  if (lines.length !== 1) throw new Error(`Browser adapter needs updating: ${name}`);
  vm.runInContext(lines[0], context);
}
const start = app.indexOf('function matchesSearch('), end = app.indexOf('function card(');
if (start < 0 || end <= start) throw new Error('Browser search boundaries changed');
vm.runInContext(app.slice(start, end), context);
const byId = new Map(library.records.map(row => [row.id, row]));
const results = cases.map(test => {
  state.librarySearch = test.query;
  const hits = library.records.filter(context.matchesLibraryFilters);
  const ids = new Set(hits.map(r => r.id));
  const expected = (test.expectedIds || []).map(id => ({id,
    stage: !byId.has(id) ? 'absent_from_library_snapshot' : !context.displayEligible(byId.get(id)) ? 'hidden_before_search' : ids.has(id) ? 'retrieved' : 'visible_but_not_retrieved'}));
  const forbiddenHits = (test.forbiddenIds || []).filter(id => ids.has(id));
  return {id: test.id, query: test.query, basis: test.basis, sourceUrls: test.sourceUrls,
    expected, hitCount: hits.length, hitIds: [...ids], forbiddenHits,
    passes: expected.every(r => r.stage === 'retrieved') && forbiddenHits.length === 0,
    scope: 'Browser predicate, all scopes, no category filter; ranking and DOM behavior are not evaluated.'};
});
process.stdout.write(JSON.stringify(results));

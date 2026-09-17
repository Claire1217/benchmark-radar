"""Fail the build on ambiguous public IDs, names, aliases or category counts."""
import json
from pathlib import Path
from library_categories import annotate_categories, category_manifest, PARENTS
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]


def audit():
    payload = json.loads((ROOT / 'data/library_index.json').read_text())
    records = payload['records']
    manifest = payload['manifest']['libraryTaxonomy']
    assert manifest == category_manifest(records), 'Public category counts/definitions drift'
    rebuilt = deepcopy(records)
    annotate_categories(rebuilt)
    assert [r['libraryCategories'] for r in records] == [r['libraryCategories'] for r in rebuilt], 'Public membership drift'
    definitions = manifest['directions']
    ids = {d['id'] for d in definitions}
    assert len(ids) == len(definitions)
    assert len({d['name'].casefold() for d in definitions}) == len(definitions), 'Duplicate public category name'
    fields = {field.casefold() for r in records for field in r.get('applicationDomains', [])}
    assert not fields.intersection(d['name'].casefold() for d in definitions), 'Ambiguous category/application-field name'
    assert not set(manifest['aliases']) & ids, 'A public category is also a redirect'
    assert set(manifest['aliases'].values()) <= ids, 'Dangling category redirect'
    for record in records:
        members = record['libraryCategories']
        assert len(members) == len(set(members)) and set(members) <= ids
        for child, parent in PARENTS.items():
            assert child not in members or parent in members, (record['id'], child, parent)
    # Discovery topics keep identical names and counts across Library and Trends.
    by_id = {d['id']: d for d in definitions}
    for topic in payload['manifest']['topicTaxonomy']['directions']:
        assert all(topic[k] == by_id[topic['id']][k] for k in ('name', 'count')), topic['id']
    public = json.loads((ROOT / 'data/benchmarks_index.json').read_text())
    library_by_id = {r['id']: r for r in records}
    for record in public['records']:
        if record['id'] in library_by_id:
            assert record['libraryCategories'] == library_by_id[record['id']]['libraryCategories']
    receipt = {'version': manifest['version'], 'categoryCount': len(definitions),
               'duplicateNames': [], 'redirectConflicts': [], 'membershipMismatches': [],
               'categories': [{k:d[k] for k in ('id', 'name', 'section', 'count')} for d in definitions],
               'parents': PARENTS, 'redirects': manifest['aliases'],
               'notes': ['Counts are unique visible benchmark entries within each category.',
                         'Categories overlap; parent categories include their children.',
                         'This audits taxonomy consistency, not full-paper verification of every underlying classification.']}
    (ROOT / 'data/library_category_audit.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print('Library categories verified:', len(definitions), 'unique IDs/names; counts, redirects, parents and surfaces consistent')


if __name__ == '__main__':
    audit()

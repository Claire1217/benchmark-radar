"""Top-10 overlap between public categories; pairs at >=50% go to merge review.

Top-10 = category members ranked by number of frontier labs reporting the
benchmark, then report count, catalog model count and GitHub stars.
Usage: python3 pipeline/category_overlap.py [-v]
"""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REVIEW_THRESHOLD = 0.5


def visible(r):
    return r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe'


def usage_score(r):
    refs = r.get('modelReportReferences') or []
    return (len({x.get('provider') for x in refs}), len(refs), r.get('catalogModelCount') or 0,
            (r.get('attention') or {}).get('githubStars') or 0, r['name'])


def top_members(records, size=10):
    members = defaultdict(list)
    for r in filter(visible, records):
        for c in r.get('libraryCategories') or []:
            members[c].append(r)
    return {c: [r['name'] for r in sorted(rows, key=usage_score, reverse=True)[:size]] for c, rows in members.items()}


def overlaps(records):
    top = top_members(records)
    pairs = []
    for a, b in combinations(sorted(top), 2):
        shared = set(top[a]) & set(top[b])
        if shared:
            pairs.append({'a': a, 'b': b, 'overlap': len(shared) / min(len(top[a]), len(top[b])), 'shared': sorted(shared)})
    return top, sorted(pairs, key=lambda p: -p['overlap'])


def main():
    library = json.loads((ROOT / 'data/library_index.json').read_text())
    names = {d['id']: d['name'] for d in library['manifest']['libraryTaxonomy']['directions']}
    top, pairs = overlaps(library['records'])
    for p in pairs:
        if p['overlap'] >= 0.3:
            flag = 'REVIEW ' if p['overlap'] >= REVIEW_THRESHOLD else ''
            print(f"{flag}{p['overlap']:.0%}  {names[p['a']]} <> {names[p['b']]} :: {p['shared']}")
    if '-v' in sys.argv:
        for c in names:
            print(f"{names[c]:40s} {top.get(c, [])}")
    print('max overlap', f"{pairs[0]['overlap']:.0%}" if pairs else '0%')


if __name__ == '__main__':
    main()

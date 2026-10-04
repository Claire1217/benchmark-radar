"""One public category registry (taxonomy-v5) shared by Library, Trends and README.

Membership comes from reviewed assignments in data/taxonomy_v5_assignments.json.
Records without a review (for example, today's new Radar admissions) receive a
provisional keyword assignment and are flagged so they can be reviewed later.
Legacy researchTopics/researchDirections remain internal evidence only.
"""
from functools import lru_cache
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = ROOT / 'data' / 'taxonomy_v5.json'
ASSIGNMENTS_PATH = ROOT / 'data' / 'taxonomy_v5_assignments.json'
MAX_SECONDARY = 2
# Kept for callers that import it; v5 categories are flat within their group.
PARENTS: dict[str, str] = {}


@lru_cache(maxsize=1)
def taxonomy() -> dict:
    return json.loads(TAXONOMY_PATH.read_text())


@lru_cache(maxsize=1)
def assignments() -> dict:
    if not ASSIGNMENTS_PATH.exists():
        return {}
    return json.loads(ASSIGNMENTS_PATH.read_text()).get('records', {})


@lru_cache(maxsize=1)
def _patterns() -> dict:
    return {c['id']: re.compile(c['keywords'], re.I) for c in taxonomy()['categories']}


def definitions() -> list[dict]:
    groups = {g['id']: g['name'] for g in taxonomy()['groups']}
    result = []
    for c in taxonomy()['categories']:
        result.append({
            'id': c['id'], 'name': c['name'], 'description': c['description'],
            'group': c['group'], 'section': groups[c['group']],
            'anchors': c.get('anchors', []), 'searchAliases': c.get('searchAliases', []),
        })
    ids = {d['id'] for d in result}
    assert len(ids) == len(result)
    assert len({d['name'].casefold() for d in result}) == len(result)
    assert not ids.intersection(aliases()), 'Canonical IDs cannot also be redirects'
    assert set(aliases().values()) <= ids
    return result


def aliases() -> dict:
    return {old: item['redirect'] for old, item in taxonomy().get('retired', {}).items()}


def keyword_assignment(record: dict) -> dict | None:
    """Provisional placement for unreviewed records; name matches count double."""
    name = record.get('name') or ''
    text = ' '.join(filter(None, [record.get('description'), record.get('oneLine')]))
    scores = {}
    for identity, pattern in _patterns().items():
        score = 2 * len(pattern.findall(name)) + len(pattern.findall(text))
        if score:
            scores[identity] = score
    if not scores:
        return None
    order = [c['id'] for c in taxonomy()['categories']]
    ranked = sorted(scores, key=lambda k: (-scores[k], order.index(k)))
    secondary = [k for k in ranked[1:] if scores[k] >= 2][:MAX_SECONDARY]
    return {'primary': ranked[0], 'secondary': secondary, 'basis': 'keyword-provisional'}


def assignment_for(record: dict) -> dict | None:
    reviewed = assignments()
    for key in (record['id'], record.get('variantOf'), record.get('familyId')):
        if key and key in reviewed:
            item = reviewed[key]
            basis = item.get('basis', 'reviewed') if key == record['id'] else 'inherited-from-family'
            return {'primary': item['primary'], 'secondary': item.get('secondary', []), 'basis': basis}
    return keyword_assignment(record)


def annotate_categories(records):
    valid = {d['id'] for d in definitions()}
    for record in records:
        item = assignment_for(record)
        if not item or item['primary'] not in valid:
            record['libraryCategories'] = []
            record['categoryAssignment'] = {'basis': 'unclassified'}
            continue
        members = [item['primary']] + [s for s in item['secondary'] if s in valid and s != item['primary']]
        record['libraryCategories'] = list(dict.fromkeys(members))[:1 + MAX_SECONDARY]
        record['categoryAssignment'] = {'primary': item['primary'], 'basis': item['basis']}


def category_manifest(records):
    visible = [r for r in records if r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe']
    return {
        'version': taxonomy()['version'],
        'retiredIds': [],
        'method': 'One primary category plus up to two secondary categories per benchmark, from reviewed assignments; unreviewed records use a provisional keyword match. Categories overlap through secondary membership.',
        'groups': taxonomy()['groups'],
        'aliases': aliases(),
        'directions': [{**d,
                        'count': sum(d['id'] in r.get('libraryCategories', []) for r in visible),
                        'primaryCount': sum((r.get('libraryCategories') or [None])[0] == d['id'] for r in visible)}
                       for d in definitions()],
        'unclassifiedCount': sum(not r.get('libraryCategories') for r in visible),
        'provisionalCount': sum((r.get('categoryAssignment') or {}).get('basis') == 'keyword-provisional' for r in visible),
    }

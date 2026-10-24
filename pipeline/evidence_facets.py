"""Evidence-grounded, multi-axis facets independent of navigation/card copy."""
from __future__ import annotations
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from source_identity import source_key, updated_at
from source_coverage import save

ROOT = Path(__file__).resolve().parents[1]
CONCEPT_PATH = ROOT / 'data/evidence_concepts.json'
EVIDENCE_PATH = ROOT / 'data/source_evidence.json'
POLICY_VERSION = 'evidence-facets-1'


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@lru_cache(maxsize=1)
def registry() -> dict:
    payload = json.loads(CONCEPT_PATH.read_text())
    ids = {c['id'] for c in payload['concepts']}
    if len(ids) != len(payload['concepts']):
        raise ValueError('Duplicate evidence concept IDs')
    for c in payload['concepts']:
        ancestors, parent = {c['id']}, c.get('parent')
        by_id = {c['id']: c for c in payload['concepts']}
        while parent:
            if parent not in ids or parent in ancestors:
                raise ValueError('Missing or cyclic evidence concept parent')
            ancestors.add(parent); parent = by_id[parent].get('parent')
    return payload


def source_url(record: dict) -> str:
    source, links = record.get('source') or {}, record.get('links') or {}
    url = source.get('url') or links.get('report') or links.get('paper') or links.get('code') or links.get('data') or links.get('project')
    if not url and source.get('type') == 'arxiv' and source.get('id'):
        url = 'https://arxiv.org/abs/' + source['id']
    return str(url or '')


def retain_sources(records: list[dict], path: Path | None = None) -> None:
    path = path or EVIDENCE_PATH
    archive = json.loads(path.read_text()) if path.exists() else {'schemaVersion':1, 'bySource':{}}
    changed = False
    for record in records:
        text = str((record.get('reviewContext') or {}).get('abstract') or '').strip()
        key = source_key(record)
        if not text or not key or not source_url(record):
            continue
        item = {'text':text[:16000], 'comments':str((record.get('reviewContext') or {}).get('comments') or '')[:2000],
                'url':source_url(record), 'sourceUpdatedAt':updated_at(record), 'basis':'primary-source-text'}
        item['contentHash'] = digest(item)
        old = archive['bySource'].get(key, {})
        if old.get('sourceUpdatedAt') and (not item['sourceUpdatedAt'] or old['sourceUpdatedAt'] > item['sourceUpdatedAt']):
            continue
        if old.get('contentHash') != item['contentHash']:
            archive['bySource'][key] = item; changed = True
    if changed:
        save(path, archive)


def evidence_units(record: dict, archive: dict | None = None) -> list[dict]:
    result = []
    retained = (archive or {}).get('bySource', {}).get(source_key(record), {})
    url = source_url(record)
    def add(text, basis, evidence_url=url):
        text = ' '.join(str(text or '').split())[:16000]
        if text and not text.startswith('Listed in a public benchmark catalog;'):
            item = {'text':text, 'url':evidence_url, 'basis':basis}
            if item not in result: result.append(item)
    if retained:
        add(retained.get('text'), 'primary-source-text', retained['url'])
        add(retained.get('comments'), 'primary-source-text', retained['url'])
    add((record.get('reviewContext') or {}).get('abstract'), 'primary-source-text')
    if (record.get('source') or {}).get('type') in {'arxiv','github','huggingface','openreview'}:
        add((record.get('evidence') or {}).get('snippet'), 'primary-source-excerpt')
        add(((record.get('curation') or {}).get('evaluationEvidence') or {}).get('task'), 'reviewed-source-excerpt')
    add(record.get('description') or record.get('oneLine'), 'editorial-description')
    return result


def input_fingerprint(record: dict, archive: dict | None = None) -> str:
    return digest({'policyVersion':POLICY_VERSION, 'conceptRegistry':digest(registry()),
                   'name':record.get('name'), 'sourceKey':source_key(record), 'evidence':evidence_units(record, archive)})


def sentence_scope(sentence: str, record: dict, basis: str) -> str:
    # A multi-domain benchmark mentioning chip design does not become a dedicated
    # chip benchmark; model reports and family labels are never scope evidence.
    if re.search(r'\b(?:cross-domain|multi-domain|spanning|includes?\s+.*(?:track|subset)|track|task subset)\b', sentence, re.I):
        return 'task-subset'
    if basis.startswith('primary') and str(record.get('name') or '').casefold() in sentence.casefold():
        if re.search(r'\b(?:benchmark|suite)\b.*\b(?:evaluat|assess|for|of)', sentence, re.I):
            return 'benchmark'
    return 'unspecified'


@lru_cache(maxsize=1)
def patterns() -> dict:
    return {c['id']: [re.compile(p, re.I) for p in (c.get('evidencePatterns') or
            [r'(?<!\w)' + re.escape(term).replace(r'\ ', r'[ -]+') + r'(?!\w)' for term in [c['label'], *c.get('aliases', [])]])]
            for c in registry()['concepts']}


def extract(record: dict, archive: dict | None = None) -> dict:
    units = evidence_units(record, archive)
    by_id = {c['id']:c for c in registry()['concepts']}
    facts = {}
    for unit in units:
        # Treat quoted primary material separately from an editorial paraphrase.
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', unit['text'])
        for sentence in sentences:
            if re.search(r'\b(?:does not evaluate|not designed to evaluate|unrelated to)\b', sentence, re.I):
                continue
            for identity, compiled in patterns().items():
                match = next((m for p in compiled if (m := p.search(sentence))), None)
                if not match:
                    continue
                quote = sentence if len(sentence) <= 500 else sentence[max(0,match.start()-160):match.end()+200]
                c = by_id[identity]
                fact = {'id':identity,'axis':c['axis'],'label':c['label'],
                        'scope':sentence_scope(sentence, record, unit['basis']),
                        'basis':unit['basis'],'reviewState':'provisional','quote':quote,'sourceUrl':unit['url']}
                # Prefer original-source evidence over card copy; never overwrite
                # a subset scope with a more general editorial description.
                facts.setdefault(identity, fact)
    for identity, fact in list(facts.items()):
        parent = by_id[identity].get('parent')
        while parent:
            c = by_id[parent]
            facts.setdefault(parent, {**fact, 'id':parent,'axis':c['axis'],'label':c['label'],
                                      'derivedFrom':identity})
            parent = c.get('parent')
    return {'policyVersion':POLICY_VERSION,'inputHash':input_fingerprint(record, archive),
            'facts':[facts[k] for k in sorted(facts)]}


def annotate(records: list[dict], archive: dict | None = None, reviewed: dict | None = None) -> None:
    for record in records:
        record['evidenceFacets'] = extract(record, archive)
        units = evidence_units(record, archive)
        # Models get primary text, not only the 220-character card description.
        record['classificationEvidence'] = units[:4]
        decision = (reviewed or {}).get(record['id'], {})
        if 'facets' in decision:
            from classify_categories import classification_hash
            if decision.get('inputHash') == classification_hash(record):
                record['evidenceFacets']['facts'] = decision['facets']
                record['evidenceFacets']['reviewMethod'] = 'model'

        primary = [u['text'] for u in units if u['basis'] != 'editorial-description']
        record['searchDocument'] = {
            'version':1, 'inputHash':record['evidenceFacets']['inputHash'],
            'name':record.get('name',''), 'aliases':record.get('aliases',[]),
            'description':record.get('description') or record.get('oneLine') or '',
            'sourceText':' '.join(primary)[:2400],
            'concepts':[{'id':f['id'],'label':f['label'],'scope':f['scope'],'basis':f['basis'],
                         'quote':f['quote'],'sourceUrl':f['sourceUrl']} for f in record['evidenceFacets']['facts']],
        }

#!/usr/bin/env python3
"""Review taxonomy-v5 categories for Library records that only have a keyword placement.

New Radar admissions get a provisional keyword category during generation. This
step asks the editorial model to place them with the same brief used for the
initial review, validates every answer, and records it in
data/taxonomy_v5_assignments.json. Invalid answers are dropped, so a record
simply stays provisional until the next run.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys
import time

from evidence_facets import registry as concept_registry, digest, POLICY_VERSION, evidence_units
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = ROOT / 'data/taxonomy_v5.json'
ASSIGNMENTS_PATH = ROOT / 'data/taxonomy_v5_assignments.json'
LIBRARY_PATH = ROOT / 'data/library_index.json'
API_URL = 'https://api.deepseek.com/chat/completions'
BATCH_SIZE = 8


def brief(taxonomy: dict) -> str:
    lines = ['Assign each AI benchmark ONE primary category and 0-2 secondary categories, using ids exactly.', '']
    for group in taxonomy['groups']:
        lines.append(f"## {group['name']}")
        for c in taxonomy['categories']:
            if c['group'] == group['id']:
                lines.append(f"- {c['id']}: {c['name']}. {c['description']} (e.g. {', '.join(c['anchors'][:4])})")
    lines += ['', 'Rules:',
              '- Classify by what is evaluated (the task), not by words in the name.',
              '- Secondary only when the benchmark genuinely tests that too. Do not pad.',
              '- Image understanding -> visual-reasoning; documents/OCR -> document-ocr; video -> video-understanding.',
              '- Office, spreadsheet, data-analysis and enterprise workflows -> professional-work.',
              '- OS/desktop/mobile/browser GUI operation -> computer-use; web information seeking -> deep-research.',
              '- Repository, terminal or issue-resolution work -> agentic-coding; function-level or competitive programming -> code-generation.',
              '- Use primary "other" only when nothing fits.',
              'Return json: {"records":[{"id":..., "primary":..., "secondary":[...], "confidence":"high"|"medium"|"low"}]} with one item per input id.']
    lines += ['', 'Evidence facets:',
              'Return evidenceQuote and sourceUrl supporting the category; copy from supplied evidence exactly.',
              'Also return facets:[{conceptId,scope,evidenceQuote,sourceUrl}], only for evaluated tasks/domains/tools.',
              'scope is benchmark, task-subset, or unspecified. A subset does not characterize the whole benchmark.',
              'Do not classify from a related-work mention, publisher field, model coverage or family membership.',
              'Use only these facet concept IDs: ' + ', '.join(c['id'] + ' (' + c['axis'] + ': ' + c['label'] + ')' for c in concept_registry()['concepts'])]
    return '\n'.join(lines)


def classification_hash(record: dict) -> str:
    return digest({'policyVersion':POLICY_VERSION, 'taxonomy':json.loads(TAXONOMY_PATH.read_text()),
                   'concepts':concept_registry(), 'name':record.get('name'),
                   'evidence':record.get('classificationEvidence') or evidence_units(record)})


def pending(records: list[dict], assigned: dict) -> list[dict]:
    rows = []
    for r in records:
        stored = assigned.get(r['id'], {})
        if r.get('displayEligible') is False or r.get('evaluationMode') == 'viewpoint_probe':
            continue
        if stored.get('basis') in {'anchor-review', 'human-review', 'manual-review'}:
            continue
        evidence = r.get('classificationEvidence') or evidence_units(r)
        if not any(unit.get('url') for unit in evidence):
            continue
        fingerprint = classification_hash(r)
        if stored.get('inputHash') == fingerprint:
            continue
        rows.append({'id':r['id'],'name':r['name'],
                     'description':' '.join(str(r.get('description') or r.get('oneLine') or '').split())[:500],
                     'evidence':evidence[:4], 'inputHash':fingerprint,
                     'previous':{'primary':stored.get('primary'),'secondary':stored.get('secondary',[])}})
    return rows


def grounded_quote(item: dict, source: dict) -> bool:
    quote = ' '.join(str(item.get('evidenceQuote') or '').split())
    url = str(item.get('sourceUrl') or '')
    return len(quote) >= 12 and bool(url) and any(
        unit.get('url') == url and quote.casefold() in ' '.join(unit.get('text','').split()).casefold()
        for unit in source.get('evidence', []))


def validate(batch: list[dict], answers: list, valid: set[str]) -> dict:
    """Keep only well-formed answers for ids that were asked."""
    asked = {row['id'] for row in batch}
    sources = {row['id']:row for row in batch}
    concepts = {c['id']:c for c in concept_registry()['concepts']}
    accepted = {}
    for item in answers if isinstance(answers, list) else []:
        if not isinstance(item, dict) or item.get('id') not in asked or item['id'] in accepted:
            continue
        source = sources[item['id']]
        if source.get('evidence') and not grounded_quote(item, source):
            continue
        primary = item.get('primary')
        secondary = item.get('secondary') or []
        if primary not in valid | {'other'} or not isinstance(secondary, list):
            continue
        secondary = [s for s in dict.fromkeys(secondary) if s in valid and s != primary][:2]
        confidence = item.get('confidence') if item.get('confidence') in ('high', 'medium', 'low') else 'low'
        accepted[item['id']] = {'primary': primary, 'secondary': [] if primary == 'other' else secondary,
                                'confidence': confidence}
        if source.get('evidence'):
            accepted[item['id']]['evidenceQuote'] = item['evidenceQuote']
            accepted[item['id']]['sourceUrl'] = item['sourceUrl']
            facets = []
            for fact in item.get('facets', []) if isinstance(item.get('facets', []), list) else []:
                if (not isinstance(fact, dict) or fact.get('conceptId') not in concepts
                        or fact.get('scope') not in {'benchmark','task-subset','unspecified'}
                        or not grounded_quote(fact, source)):
                    continue
                c = concepts[fact['conceptId']]
                facets.append({'id':c['id'],'axis':c['axis'],'label':c['label'],'scope':fact['scope'],
                               'basis':next(unit['basis'] for unit in source['evidence'] if unit.get('url') == fact['sourceUrl'] and ' '.join(fact['evidenceQuote'].split()).casefold() in ' '.join(unit['text'].split()).casefold()),
                               'reviewMethod':'model','reviewState':'model-reviewed','quote':fact['evidenceQuote'],'sourceUrl':fact['sourceUrl']})
            accepted[item['id']]['facets'] = facets
    return accepted


def deepseek(api_key: str, model: str) -> Callable[[str, list[dict]], list]:
    def post(system: str, batch: list[dict]) -> list:
        body = {'model': model, 'messages': [{'role': 'system', 'content': system},
                                             {'role': 'user', 'content': json.dumps(batch, ensure_ascii=False)}],
                'thinking': {'type': 'disabled'}, 'response_format': {'type': 'json_object'},
                'max_tokens': 8192, 'stream': False}
        request = Request(API_URL, data=json.dumps(body).encode(), method='POST',
                          headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'})
        for attempt in range(3):
            try:
                with urlopen(request, timeout=120) as response:
                    content = json.loads(response.read())['choices'][0]['message']['content']
                    return json.loads(content).get('records', [])
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise
            except (TimeoutError, URLError, json.JSONDecodeError, KeyError, IndexError):
                if attempt == 2:
                    raise
            time.sleep(2 ** attempt)
        return []
    return post


def run(post: Callable[[str, list[dict]], list], limit: int = 0, today: str | None = None,
        model: str = '') -> dict:
    taxonomy = json.loads(TAXONOMY_PATH.read_text())
    payload = json.loads(ASSIGNMENTS_PATH.read_text())
    assigned = payload['records']
    rows = pending(json.loads(LIBRARY_PATH.read_text())['records'], assigned)
    if limit:
        rows = rows[:limit]
    valid = {c['id'] for c in taxonomy['categories']}
    system = brief(taxonomy)
    stats = {'pending': len(rows), 'accepted': 0, 'rejected': 0}
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        try:
            accepted = validate(batch, post(system, batch), valid)
        except Exception as exc:  # one failed batch must not lose the others
            print(f'warning: category review batch failed: {exc}', file=sys.stderr)
            accepted = {}
        for rid, item in accepted.items():
            assigned[rid] = {**item, 'basis': 'model-review-daily', 'reviewedAt': today or date.today().isoformat(),
                             **({'model': model} if model else {}),
                             'inputHash':next(row['inputHash'] for row in batch if row['id']==rid),
                             'policyVersion':POLICY_VERSION}
        stats['accepted'] += len(accepted)
        stats['rejected'] += len(batch) - len(accepted)
    if stats['accepted']:
        payload['records'] = dict(sorted(assigned.items()))
        ASSIGNMENTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=0) + '\n')
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--model', default=os.environ.get('DEEPSEEK_COPY_MODEL', 'deepseek-v4-flash'))
    args = parser.parse_args()
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        print('DEEPSEEK_API_KEY is not configured; new records keep their provisional category.')
        return
    print('category_review', run(deepseek(key, args.model), args.limit, model=args.model))


if __name__ == '__main__':
    main()

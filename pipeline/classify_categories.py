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
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = ROOT / 'data/taxonomy_v5.json'
ASSIGNMENTS_PATH = ROOT / 'data/taxonomy_v5_assignments.json'
LIBRARY_PATH = ROOT / 'data/library_index.json'
API_URL = 'https://api.deepseek.com/chat/completions'
BATCH_SIZE = 25


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
    return '\n'.join(lines)


def pending(records: list[dict], assigned: dict) -> list[dict]:
    rows = []
    for r in records:
        if r.get('displayEligible') is False or r.get('evaluationMode') == 'viewpoint_probe' or r['id'] in assigned:
            continue
        if (r.get('categoryAssignment') or {}).get('basis') in ('keyword-provisional', 'unclassified'):
            rows.append({'id': r['id'], 'name': r['name'],
                         'description': ' '.join(str(r.get('description') or r.get('oneLine') or '').split())[:500]})
    return rows


def validate(batch: list[dict], answers: list, valid: set[str]) -> dict:
    """Keep only well-formed answers for ids that were asked."""
    asked = {row['id'] for row in batch}
    accepted = {}
    for item in answers if isinstance(answers, list) else []:
        if not isinstance(item, dict) or item.get('id') not in asked or item['id'] in accepted:
            continue
        primary = item.get('primary')
        secondary = item.get('secondary') or []
        if primary not in valid | {'other'} or not isinstance(secondary, list):
            continue
        secondary = [s for s in dict.fromkeys(secondary) if s in valid and s != primary][:2]
        confidence = item.get('confidence') if item.get('confidence') in ('high', 'medium', 'low') else 'low'
        accepted[item['id']] = {'primary': primary, 'secondary': [] if primary == 'other' else secondary,
                                'confidence': confidence}
    return accepted


def deepseek(api_key: str, model: str) -> Callable[[str, list[dict]], list]:
    def post(system: str, batch: list[dict]) -> list:
        body = {'model': model, 'messages': [{'role': 'system', 'content': system},
                                             {'role': 'user', 'content': json.dumps(batch, ensure_ascii=False)}],
                'thinking': {'type': 'disabled'}, 'response_format': {'type': 'json_object'},
                'max_tokens': 4096, 'stream': False}
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
                             **({'model': model} if model else {})}
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

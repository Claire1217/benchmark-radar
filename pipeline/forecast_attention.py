#!/usr/bin/env python3
"""Refresh experimental attention estimates without changing admission or copy."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from classify_categories import deepseek
from review_scheduler import source_key

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data/benchmarks.json'
OUTPUT_PATH = ROOT / 'data/attention_forecasts.json'
POLICY_VERSION = 1
PROMPT = '''Estimate likely public attention during the first seven days after release from supplied evidence only.
Attention is not quality or eligibility. Do not infer publisher prestige, social activity or metrics not supplied.
Return JSON {"records":[{"id":"input id","score":0,"confidence":"Low","horizon":"7d","reason":"neutral explanation"}]}.
Scores are integers 0-100, confidence Low or Medium, horizon always 7d. Return one record per input id.
Do not return publication decisions, new names, descriptions or category assignments.'''


def source_input(record: dict) -> dict:
    return {'id': source_key(record), 'name': record.get('name'),
            'description': record.get('description'), 'readiness': record.get('readiness'),
            'evidence': (record.get('evidence') or {}).get('snippet'),
            'publishers': record.get('publishers', [])}


def fingerprint(record: dict) -> str:
    return hashlib.sha256(json.dumps([POLICY_VERSION, source_input(record)], sort_keys=True).encode()).hexdigest()


def validated(rows: list, asked: set[str]) -> dict:
    result = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or row.get('id') not in asked or row['id'] in result:
            continue
        if (type(row.get('score')) is not int or not 0 <= row['score'] <= 100
                or row.get('confidence') not in {'Low', 'Medium'} or row.get('horizon') != '7d'
                or not isinstance(row.get('reason'), str) or not row['reason'].strip()):
            continue
        result[row['id']] = {key: row[key] for key in ('score', 'confidence', 'horizon', 'reason')}
        result[row['id']]['reason'] = result[row['id']]['reason'].strip()[:500]
    return result


def apply_forecasts(records: list[dict], payload: dict) -> list[dict]:
    for record in records:
        row = payload.get('bySource', {}).get(source_key(record))
        # A newer source needs a new forecast; stale estimates must not overwrite it.
        if row and row.get('inputHash') == fingerprint(record):
            forecast = validated([{'id': source_key(record), **row.get('forecast', {})}], {source_key(record)})
            if forecast:
                record['attentionForecast'] = forecast[source_key(record)]
    return records


def run(records: list[dict], existing: dict, post, *, now: str, model: str, limit: int = 24) -> int:
    selected = [r for r in records if r.get('displayEligible') is not False
                and r.get('evaluationMode') != 'viewpoint_probe'
                and existing.get('bySource', {}).get(source_key(r), {}).get('inputHash') != fingerprint(r)]
    selected.sort(key=lambda r: (r.get('releasedAt', ''), source_key(r)), reverse=True)
    if limit > 0:
        selected = selected[:limit]
    updated = 0
    for start in range(0, len(selected), 8):
        batch = selected[start:start + 8]
        accepted = validated(post(PROMPT, [source_input(r) for r in batch]), {source_key(r) for r in batch})
        for record in batch:
            key = source_key(record)
            if key in accepted:
                existing.setdefault('bySource', {})[key] = {'forecast': accepted[key], 'inputHash': fingerprint(record),
                    'generatedAt': now, 'model': model, 'policyVersion': POLICY_VERSION}
                updated += 1
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--released-from')
    parser.add_argument('--released-through')
    parser.add_argument('--limit', type=int, default=24)
    args = parser.parse_args()
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        print('DEEPSEEK_API_KEY is not configured; existing forecasts preserved.')
        return
    records = [r for r in json.loads(DATA_PATH.read_text())['records']
               if (not args.released_from or r.get('releasedAt', '') >= args.released_from)
               and (not args.released_through or r.get('releasedAt', '') <= args.released_through)]
    existing = json.loads(OUTPUT_PATH.read_text()) if OUTPUT_PATH.exists() else {'schemaVersion': 1, 'bySource': {}}
    model = os.environ.get('DEEPSEEK_COPY_MODEL', 'deepseek-v4-flash')
    count = run(records, existing, deepseek(key, model), now=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), model=model, limit=args.limit)
    if count:
        temporary = OUTPUT_PATH.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(OUTPUT_PATH)
    print(f'attention_forecasts_updated={count}')


if __name__ == '__main__':
    main()

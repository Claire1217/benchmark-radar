#!/usr/bin/env python3
"""Refresh opted-in Library seeds; preserve failed signals as dated stale values."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from enrich_metrics import enrich_one, preserve_last_known, summarize_observation

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/library_metrics.json'


def metric_input(seed):
    record = dict(seed)
    paper = seed.get('links', {}).get('paper') or ''
    match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', paper)
    record['source'] = {'type': 'arxiv', 'id': match[1]} if match else {'type': 'library', 'id': seed['id']}
    return record


def scope_observation(raw, seed):
    """Keep shared resource counters as evidence, never as a subset's popularity."""
    scopes = seed.get('metricScopes', {})
    if scopes.get('github'):
        raw['githubScope'] = scopes['github']
    shared = {}
    for provider, signals in [('hfPaper', ['hfPaperUpvotes']), ('hfDataset', ['hfDatasetDownloads', 'hfDatasetLikes'])]:
        if scopes.get(provider):
            shared[provider] = {'scope': scopes[provider], **{key: raw.get(key) for key in signals}}
            for key in signals:
                raw[key] = None
                raw['signalStatus'][key] = {'state': 'not_applicable', 'reason': scopes[provider]}
    if shared:
        raw['sharedResourceSignals'] = shared
    return raw


def finish_observations(results, seeds, previous, now):
    results = preserve_last_known(results, seeds, previous)
    summarize_observation(results, now, previous)
    for raw in results:
        statuses = raw['signalStatus'].values()
        fresh = any(s['state'] == 'fresh' for s in statuses)
        old = next((r for r in previous.get('records', []) if r['benchmarkId'] == raw['benchmarkId']), {})
        raw.update(asOf=now[:10], attemptedAt=now,
                   observedAt=now if fresh else old.get('observedAt'),
                   status='fresh' if fresh else 'stale' if any(s['state'] == 'stale' for s in statuses) else 'unavailable')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only-ids', help='Comma-separated Library seed IDs')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    seeds = json.loads((ROOT / 'data/library_seed_records.json').read_text())['records']
    selected = set(args.only_ids.split(',')) if args.only_ids else None
    seeds = [r for r in seeds if r.get('refreshMetrics') and (selected is None or r['id'] in selected)]
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'records': []}
    now = datetime.now(timezone.utc).isoformat()
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    def refresh(seed):
        return scope_observation(enrich_one(metric_input(seed), token, True), seed)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = finish_observations(list(pool.map(refresh, seeds)), seeds, previous, now)
    retained = {r['benchmarkId']: r for r in previous['records']}
    retained.update({r['benchmarkId']: r for r in results})
    OUTPUT.write_text(json.dumps({'schemaVersion': '1.0', 'date': now[:10], 'observedAt': now,
                                 'records': sorted(retained.values(), key=lambda r: r['benchmarkId'])}, ensure_ascii=False, indent=2) + '\n')
    print('Library metric observations refreshed:', len(results))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Refresh opted-in Library seeds; preserve failed signals as dated stale values."""
from __future__ import annotations
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


def library_input(record):
    """A visible Library record as an enrich_one input (any record, not only seeds)."""
    from audit_signal_coverage import arxiv_id
    paper = arxiv_id(record)
    links = dict(record.get('links') or {})
    repo = (record.get('attention') or {}).get('githubRepo')
    if repo and not links.get('code'):
        links['code'] = repo
    return {'id': record['id'], 'links': links, 'metricScopes': record.get('metricScopes', {}),
            'githubIndex': record.get('githubIndex'), 'attention': record.get('attention') or {},
            'source': {'type': 'arxiv', 'id': paper} if paper else {'type': 'library', 'id': record['id']}}


def stalest(records, previous, limit, today):
    """Visible records ordered by how long ago they were last attempted (never first)."""
    from audit_signal_coverage import visible
    attempted = {r['benchmarkId']: (r.get('attemptedAt') or '')[:10] for r in previous.get('records', [])}
    rows = [r for r in records if visible(r)]
    rows.sort(key=lambda r: (attempted.get(r['id'], ''), r['id']))
    rows = [r for r in rows if attempted.get(r['id'], '') < today]
    return rows[:limit] if limit else rows


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
    parser.add_argument('--all-visible', action='store_true',
                        help='Refresh every visible Library record, stalest first')
    parser.add_argument('--max', type=int, default=0, help='With --all-visible: records per run (0 = all)')
    parser.add_argument('--missing', choices=['hfPaperUpvotes', 'githubStars', 'hfDatasetDownloads'],
                        help='With --all-visible: only records still lacking this signal, regardless of last attempt')
    args = parser.parse_args()
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'records': []}
    now = datetime.now(timezone.utc).isoformat()
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if args.all_visible:
        library = json.loads((ROOT / 'data/library_index.json').read_text())['records']
        if args.missing:
            from audit_signal_coverage import visible
            pool = [r for r in library if visible(r) and (r.get('attention') or {}).get(args.missing) is None]
            pool = pool[:args.max] if args.max else pool
        else:
            pool = stalest(library, previous, args.max, now[:10])
        seeds = [library_input(r) for r in pool]
        prepare = lambda seed: seed
    else:
        seeds = json.loads((ROOT / 'data/library_seed_records.json').read_text())['records']
        selected = set(args.only_ids.split(',')) if args.only_ids else None
        seeds = [r for r in seeds if r.get('refreshMetrics') and (selected is None or r['id'] in selected)]
        prepare = metric_input
    def refresh(seed):
        return scope_observation(enrich_one(prepare(seed), token, True), seed)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = finish_observations(list(pool.map(refresh, seeds)), seeds, previous, now)
    retained = {r['benchmarkId']: r for r in previous['records']}
    retained.update({r['benchmarkId']: r for r in results})
    OUTPUT.write_text(json.dumps({'schemaVersion': '1.0', 'date': now[:10], 'observedAt': now,
                                 'records': sorted(retained.values(), key=lambda r: r['benchmarkId'])}, ensure_ascii=False, indent=2) + '\n')
    print('Library metric observations refreshed:', len(results))


if __name__ == '__main__':
    main()

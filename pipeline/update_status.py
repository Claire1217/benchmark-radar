"""Publication receipts, bounded catch-up and honest public freshness.

Receipts are staged with data and only become durable after validation and push.
Attention refreshes never advance discovery coverage. Partial source coverage is
reported separately, so one unavailable source does not stop all other sources.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

from scheduled_source_date import previous_calendar_day

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / 'data/update_status.json'


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def baseline(manifest):
    # Never use dataAsOf: attention-only runs advance it without discovery.
    return (manifest.get('latestReportDate') or
            (manifest.get('run') or {}).get('sourceDate'))


def coverage_through(state):
    current = date.fromisoformat(state['trackingStartedAfter'])
    receipts = state.get('publications', {})
    while (current + timedelta(days=1)).isoformat() in receipts:
        current += timedelta(days=1)
    return current.isoformat()


def next_date(state, manifest, target):
    through = coverage_through(state) if state else baseline(manifest)
    if not through:
        return target
    return min(target, (date.fromisoformat(through) + timedelta(days=1)).isoformat())


def catchup_end(start, target, days):
    if not 1 <= days <= 7 or start > target:
        raise ValueError('Catch-up requires 1–7 days and a start no later than target')
    return min(date.fromisoformat(target), date.fromisoformat(start) + timedelta(days=days - 1)).isoformat()


def record(state, manifest, source_date, run, run_url, editorial_status='success'):
    if run.get('sourceDate') != source_date or 'externalDiscovery' not in run:
        raise ValueError('Cannot publish a receipt without the matching discovery run')
    if not state:
        raise ValueError('Initialize the coverage baseline before running discovery')
    state = {**state, 'publications': dict(state.get('publications', {}))}
    state['publications'][source_date] = {
        'completedAt': datetime.now(timezone.utc).isoformat(),
        'runUrl': run_url,
        'sourceFailures': run['externalDiscovery'].get('failures', {}),
        'editorialStatus': editorial_status,
    }
    return state


def public_status(manifest, state=None, target=None):
    target = target or previous_calendar_day()
    through = coverage_through(state) if state else baseline(manifest)
    publications = (state or {}).get('publications', {})
    latest = max(publications, default=through or '')
    receipt = publications.get(latest, {})
    metrics = manifest.get('metrics') or {}
    observations = [metrics.get(k) for k in ('observedAt', 'todayObservedAt') if metrics.get(k)]
    lag = max(0, (date.fromisoformat(target) - date.fromisoformat(through)).days) if through else None
    return {
        'discoveryThrough': through,
        'expectedThrough': target,
        'lagDays': lag,
        'status': 'unknown' if lag is None else 'delayed' if lag else 'current',
        'lastDiscoveryDate': latest or None,
        'lastDiscoveryRunUrl': receipt.get('runUrl'),
        'sourceFailures': receipt.get('sourceFailures', {}),
        'editorialStatus': receipt.get('editorialStatus', 'unknown'),
        'attentionObservedAt': max(observations, default=None),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'next-date', 'catchup-end', 'record', 'check'])
    parser.add_argument('--days', type=int, default=1)
    parser.add_argument('--target', default=previous_calendar_day())
    parser.add_argument('--date')
    parser.add_argument('--run-url', default='')
    parser.add_argument('--editorial-status', default='success')
    args = parser.parse_args()
    manifest = load(ROOT / 'data/benchmarks.json', {})['manifest']
    state = load(STATUS, {})
    if args.command == 'init':
        if not state:
            start = baseline(manifest) or (date.fromisoformat(args.target) - timedelta(days=1)).isoformat()
            STATUS.write_text(json.dumps({'trackingStartedAfter': start, 'publications': {}}, indent=2) + '\n')
    elif args.command == 'next-date':
        print(next_date(state, manifest, args.target))
    elif args.command == 'catchup-end':
        print(catchup_end(args.date, args.target, args.days))
    elif args.command == 'record':
        run = load(ROOT / f'data/runs/{args.date}.json', {})
        state = record(state, manifest, args.date, run, args.run_url, args.editorial_status)
        STATUS.write_text(json.dumps(state, indent=2, sort_keys=True) + '\n')
    else:
        status = public_status(manifest, state, args.target)
        print(json.dumps(status, indent=2))
        if status['lagDays'] is None or status['lagDays'] > 1:
            raise SystemExit('Discovery publication is overdue; attention refresh is not discovery. Check Daily benchmark index logs and recovery artifacts.')


if __name__ == '__main__':
    main()

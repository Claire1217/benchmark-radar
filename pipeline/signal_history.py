#!/usr/bin/env python3
"""Per-benchmark signal history and growth by stage (0-1, 1-3, 3-6 months).

GitHub stars: growth comes from recorded star events (data/github_star_history.json),
which go back to each repository's creation. Only repositories scoped to one
benchmark count; shared hosting repositories would credit one benchmark with
another's attention.

Hugging Face upvotes, dataset downloads and likes: providers keep no history,
so every generate stores the current value in data/signal_history.json (only
when it changes). Growth is reported once the stored history reaches back to
the start of the window; before that it is None, never 0.

Usage:
  python3 pipeline/signal_history.py           # record today's values, annotate growth
  python3 pipeline/signal_history.py --seed    # first run: import past daily Radar snapshots
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

from generate_trends_comparison import repo_key

ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = ROOT / 'data/signal_history.json'
SNAPSHOT_SIGNALS = ('githubStars', 'hfPaperUpvotes', 'hfDatasetDownloads', 'hfDatasetLikes')
STAGES = {'0-1m': (0, 30), '1-3m': (30, 90), '3-6m': (90, 180)}
WINDOWS = {'1m': 30, '3m': 90, '6m': 180}


def visible(r):
    return r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe'


def record_values(history: dict, records: list[dict], day: str) -> int:
    """Store today's value for each signal when it differs from the last stored one."""
    changed = 0
    for r in records:
        attention = r.get('attention') or {}
        for signal in SNAPSHOT_SIGNALS:
            value = attention.get(signal)
            if value is None:
                continue
            series = history.setdefault(r['id'], {}).setdefault(signal, [])
            if series and series[-1][0] == day:
                if series[-1][1] != value:
                    series[-1][1] = value
                    changed += 1
            elif not series or series[-1][1] != value:
                if series and series[-1][0] > day:
                    continue  # never rewrite a later observation with an older one
                series.append([day, value])
                changed += 1
    return changed


def value_at(series: list, day: str):
    """Last stored value on or before day, or None when history starts later."""
    found = None
    for d, v in series:
        if d <= day:
            found = v
        else:
            break
    return found


def snapshot_growth(series: list, as_of: str) -> dict | None:
    if not series:
        return None
    end = date.fromisoformat(as_of)
    now = value_at(series, as_of)
    if now is None:
        return None
    windows = {}
    for label, days in WINDOWS.items():
        base = value_at(series, (end - timedelta(days=days)).isoformat())
        windows[label] = None if base is None else now - base
    stages = {}
    for label, (a, b) in STAGES.items():
        hi = value_at(series, (end - timedelta(days=a)).isoformat())
        lo = value_at(series, (end - timedelta(days=b)).isoformat())
        stages[label] = None if hi is None or lo is None else hi - lo
    return {'current': now, **windows, 'stages': stages, 'basis': 'snapshots', 'historyFrom': series[0][0]}


def star_events(history: dict) -> dict:
    """repo key -> list of (day, new stars) from complete star histories."""
    events = {}
    for h in history.get('records', []):
        if h.get('status') != 'complete':
            continue
        days = []
        for week in h.get('weeks', []):
            start = datetime.fromtimestamp(week['week'], timezone.utc).date()
            days += [(start + timedelta(days=i), n) for i, n in enumerate(week['days']) if n]
        events[repo_key(h['url'])] = days
    return events


def event_growth(days: list, end: date, created: date | None) -> dict:
    def gained(a, b):  # stars created in [end-b, end-a)
        lo, hi = end - timedelta(days=b), end - timedelta(days=a)
        return None if created and created > lo else sum(n for d, n in days if lo <= d < hi)
    return {**{label: gained(0, n) for label, n in WINDOWS.items()},
            'stages': {label: gained(a, b) for label, (a, b) in STAGES.items()}, 'basis': 'star-events'}


def annotate_growth(records: list[dict], history: dict, star_history: dict, as_of: str, star_end: str) -> None:
    events = star_events(star_history)
    created = {repo_key(h['url']): min((datetime.fromtimestamp(w['week'], timezone.utc).date() for w in h['weeks']), default=None)
               for h in star_history.get('records', []) if h.get('status') == 'complete'}
    end = date.fromisoformat(star_end)
    for r in records:
        attention = r.get('attention') or {}
        growth = {}
        repo = repo_key(attention.get('githubRepo') or (r.get('links') or {}).get('code'))
        if repo in events and attention.get('githubScope') == 'benchmark_repo':
            # History starts at the first recorded week; a repository younger than a window has
            # all of its stars inside that window, so its creation does not hide the value.
            growth['githubStars'] = event_growth(events[repo], end, None)
            growth['githubStars']['current'] = attention.get('githubStars')
            growth['githubStars']['repositoryCreated'] = created[repo].isoformat() if created.get(repo) else None
        for signal in ('hfPaperUpvotes', 'hfDatasetDownloads', 'hfDatasetLikes'):
            value = snapshot_growth(history.get(r['id'], {}).get(signal, []), as_of)
            if value:
                growth[signal] = value
        if growth:
            r['growth'] = {'asOf': as_of, 'starsThrough': star_end, **growth}
        else:
            r.pop('growth', None)


def star_window_end(as_of: str) -> str:
    """Same cut-off as Trends: star windows end at the last complete source week."""
    day = date.fromisoformat(as_of)
    return (day - timedelta(days=(day.weekday() + 1) % 7)).isoformat()


def apply_growth(records: list[dict], as_of: str) -> None:
    """Read-only: annotate growth from stored history (used by generate_library_index)."""
    history = json.loads(HISTORY_PATH.read_text()).get('records', {}) if HISTORY_PATH.exists() else {}
    stars_path = ROOT / 'data/github_star_history.json'
    stars = json.loads(stars_path.read_text()) if stars_path.exists() else {'records': []}
    annotate_growth(records, history, stars, as_of, star_window_end(as_of))


def seed(history: dict) -> int:
    """Import past daily Radar metric snapshots (data/metrics/YYYY-MM-DD.json)."""
    total = 0
    for path in sorted((ROOT / 'data/metrics').glob('*.json')):
        snapshot = json.loads(path.read_text())
        rows = [{'id': r['benchmarkId'], 'attention': r} for r in snapshot.get('records', [])]
        total += record_values(history, rows, snapshot.get('date') or path.stem)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--seed', action='store_true')
    args = parser.parse_args()
    library_path = ROOT / 'data/library_index.json'
    library = json.loads(library_path.read_text())
    history = json.loads(HISTORY_PATH.read_text()).get('records', {}) if HISTORY_PATH.exists() else {}
    seeded = seed(history) if args.seed else 0
    as_of = library['manifest'].get('dataAsOf') or date.today().isoformat()
    changed = record_values(history, [r for r in library['records'] if visible(r)], as_of)
    HISTORY_PATH.write_text(json.dumps({'schemaVersion': '1.0', 'note': 'Sparse: a value is stored only when it changes.',
                                        'records': dict(sorted(history.items()))}, separators=(',', ':')) + '\n')
    apply_growth(library['records'], as_of)
    library_path.write_text(json.dumps(library, ensure_ascii=False, separators=(',', ':')) + '\n')
    with_growth = sum('growth' in r for r in library['records'] if visible(r))
    print(f'signal_history seeded={seeded} changed={changed} records_with_growth={with_growth}')


if __name__ == '__main__':
    main()

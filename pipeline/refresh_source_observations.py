#!/usr/bin/env python3
"""Revisit known sources independently of their original publication date."""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import discover_benchmarks as discovery
import index_benchmarks as index
from source_identity import source_key, evidence_hash, merge_observation, newer_than_public
from source_coverage import save

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / 'data/source_refresh_state.json'
SUPPORTED = {'arxiv', 'github', 'huggingface', 'openreview'}


def fetch_observation(record: dict) -> dict:
    observation = copy.deepcopy(record)
    source = record['source']; kind, identifier = source['type'], source['id']
    if kind == 'arxiv':
        url = index.ATOM_API_URL + '?' + urlencode({'id_list': identifier, 'max_results': 1})
        with urlopen(Request(url, headers={'User-Agent': discovery.USER_AGENT}), timeout=20) as response:
            root = ET.fromstring(response.read())
        papers = [p for entry in root.findall('atom:entry', index.ATOM_NS) if (p := index.parse_atom_paper(entry)) is not None]
        paper = next((p for p in papers if p.arxiv_id == identifier), None)
        if paper is None:
            raise RuntimeError('Source did not return the requested paper')
        score, relation, reasons = index.recognition(paper)
        observation = index.to_record(paper, record.get('firstSeenAt', paper.released_at), score, relation, reasons)
        observation['reviewContext'] = {'abstract': paper.abstract, 'comments': paper.comments}
    elif kind == 'github':
        full_name = identifier.removeprefix('github:')
        headers = {'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']} if os.environ.get('GITHUB_TOKEN') else {}
        metadata = discovery.fetch_json('https://api.github.com/repos/' + full_name, headers)
        excerpt = discovery.fetch_text('https://api.github.com/repos/' + full_name + '/readme',
                                       {**headers, 'Accept': 'application/vnd.github.raw+json'})
        observation['sourceUpdatedAt'] = metadata.get('pushed_at') or metadata.get('updated_at')
        observation['reviewContext'] = {'abstract': discovery.clean(excerpt), 'comments': ''}
    elif kind == 'huggingface':
        full_name = identifier.removeprefix('huggingface:')
        metadata = discovery.fetch_json('https://huggingface.co/api/datasets/' + quote(full_name, safe='/'))
        excerpt = discovery.fetch_text('https://huggingface.co/datasets/' + quote(full_name, safe='/') + '/raw/main/README.md')
        observation['sourceUpdatedAt'] = metadata.get('lastModified')
        observation['reviewContext'] = {'abstract': discovery.clean(excerpt), 'comments': ''}
    elif kind == 'openreview':
        note_id = identifier.removeprefix('openreview:')
        headers = {'Authorization': 'Bearer ' + os.environ['OPENREVIEW_TOKEN']} if os.environ.get('OPENREVIEW_TOKEN') else {}
        result = discovery.fetch_json('https://api2.openreview.net/notes?' + urlencode({'id': note_id}), headers)
        note = next((n for n in result.get('notes', []) if n.get('id') == note_id), None)
        if note is None:
            raise RuntimeError('Source did not return the requested note')
        content = note.get('content', {})
        observation['sourceUpdatedAt'] = datetime.fromtimestamp(int(note.get('mdate') or note.get('cdate'))/1000, timezone.utc).isoformat()
        observation['reviewContext'] = {'abstract': discovery.clean(discovery.openreview_value(content, 'abstract')), 'comments': ''}
    else:
        raise ValueError('Unsupported source type')
    return merge_observation(record, observation)


def refresh(records: list[dict], state: dict, fetch, persist, *, now: str, limit: int = 60, max_seconds: int = 180) -> dict:
    started = time.monotonic()
    by_source = state.setdefault('bySource', {})
    eligible = [r for r in records if (r.get('source') or {}).get('type') in SUPPORTED
                and r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe'
                and by_source.get(source_key(r), {}).get('checkedAt', '')[:10] != now[:10]]
    eligible.sort(key=lambda r: (by_source.get(source_key(r), {}).get('checkedAt', ''), r.get('releasedAt', ''), source_key(r)))
    stats = {'checked': 0, 'changed': 0, 'failed': 0}
    for record in eligible[:limit]:
        if time.monotonic() - started >= max_seconds:
            break
        key = source_key(record)
        old = by_source.get(key, {})
        try:
            observation = fetch(record)
            digest = evidence_hash(observation)
            changed = digest != old['evidenceHash'] if old.get('evidenceHash') else newer_than_public(observation, record)
            if changed:
                observation['reviewReason'] = 'source-changed'
                persist(observation)  # queue first; a crash must not mark an update handled
                stats['changed'] += 1
            by_source[key] = {'checkedAt': now, 'status': 'changed' if changed else 'unchanged' if old.get('evidenceHash') else 'baseline-observed',
                              'evidenceHash': digest, 'sourceUpdatedAt': observation.get('sourceUpdatedAt')}
        except (HTTPError, URLError, TimeoutError, RuntimeError, ET.ParseError, ValueError, TypeError, KeyError) as error:
            # Preserve the last valid evidence hash; a failed read is not a source change.
            by_source[key] = {**old, 'checkedAt': now, 'status': 'source-unavailable', 'error': type(error).__name__}
            stats['failed'] += 1
        stats['checked'] += 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=60)
    parser.add_argument('--max-seconds', type=int, default=180)
    args = parser.parse_args()
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {'schemaVersion': 1, 'bySource': {}}
    records = json.loads(index.DATA_PATH.read_text()).get('records', [])
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    queue_payload = discovery.read_json(discovery.REVIEW_PATH, {'candidates': []})
    target = queue_payload.get('sourceDate') or now[:10]
    def persist(observation):
        # Force a source observation into review even when an old catalog lacks
        # revision timestamps; IDs and original release dates remain unchanged.
        payload = discovery.read_json(discovery.REVIEW_PATH, {'candidates': []})
        existing = next((r for r in payload['candidates'] if source_key(r) == source_key(observation)), None)
        if existing:
            discovery.merge_candidate(existing, observation)
            existing['reviewReason'] = 'source-changed'
        else:
            payload['candidates'].append(observation)
        payload['candidateCount'] = len(payload['candidates'])
        payload.setdefault('sourceDate', target)
        save(discovery.REVIEW_PATH, payload)
    stats = refresh(records, state, fetch_observation, persist, now=now, limit=args.limit, max_seconds=args.max_seconds)
    save(STATE_PATH, state)
    print(json.dumps(stats))


if __name__ == '__main__':
    main()

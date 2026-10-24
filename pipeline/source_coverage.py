"""Durable, scoped discovery receipts. Completion follows candidate persistence."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from backfill_index import atomic_write_json

CONTRACT_VERSION = 1


def load(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {'schemaVersion': 1, 'windows': {}}


def key(source: str, scope: str, start: str, end: str) -> str:
    return '|'.join((source, scope, start, end))


def enqueue(payload: dict, source: str, scope: str, start: str, end: str) -> str:
    identifier = key(source, scope, start, end)
    payload.setdefault('windows', {}).setdefault(identifier, {
        'source': source, 'scope': scope, 'from': start, 'to': end,
        'contractVersion': CONTRACT_VERSION, 'status': 'pending', 'attempts': [],
    })
    return identifier


def pending(payload: dict, now: str) -> list[tuple[str, dict]]:
    return sorted(((k, v) for k, v in payload.get('windows', {}).items()
                   if v.get('status') != 'complete' and v.get('retryAfter', '') <= now),
                  key=lambda pair: (pair[1].get('lastAttemptAt', ''), pair[1]['from'], pair[0]))


def attempt(payload: dict, identifier: str, *, now: str, status: str, count: int = 0,
            candidate_hash: str = '', error: str = '') -> None:
    if status not in {'complete', 'failed'}:
        raise ValueError('Only a persisted collection can be completed; failures remain retryable')
    if status == 'complete' and not candidate_hash:
        raise ValueError('Completion requires persisted candidate receipt')
    row = payload['windows'][identifier]
    row.update(status=status, lastAttemptAt=now)
    row['attempts'] = [*row.get('attempts', []), {'at': now, 'status': status,
        'count': count, 'candidateSha256': candidate_hash, 'error': error[:500]}][-20:]
    row['attemptCount'] = row.get('attemptCount', 0) + 1
    if status == 'failed':
        next_attempt = datetime.fromisoformat(now.replace('Z', '+00:00')) + timedelta(hours=2)
        row['retryAfter'] = next_attempt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    else:
        row.pop('retryAfter', None)


def receipt(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, payload: dict) -> None:
    atomic_write_json(path, payload)

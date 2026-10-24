"""A source observation identifies a source, never an inferred benchmark family."""
from __future__ import annotations
import copy
import hashlib
import json

SOURCE_FIELDS = ('source', 'paperTitle', 'sourceUpdatedAt', 'evidence', 'reviewContext',
                 'recognitionConfidence', 'relation', 'candidatePriority')
STABLE_FIELDS = ('id', 'releasedAt', 'firstSeenAt', 'familyId')


def source_key(record: dict) -> str:
    source = record.get('source') or {}
    identifier = str(source.get('id') or '')
    if not identifier:
        return ''
    kind = str(source.get('type') or 'unknown')
    if kind == 'unknown' and ':' in identifier:
        kind = identifier.split(':', 1)[0]
    # Case sensitivity belongs to the provider. arXiv/OpenReview IDs are not names.
    if kind in {'github', 'huggingface'}:
        identifier = identifier.casefold()
    return identifier if identifier.startswith(kind + ':') else kind + ':' + identifier


def updated_at(record: dict) -> str:
    return str(record.get('sourceUpdatedAt') or (record.get('source') or {}).get('updatedAt') or '')


def evidence_hash(record: dict) -> str:
    # Ignore popularity, observations times and editorial/card copy.
    content = {'sourceKey': source_key(record), 'title': record.get('paperTitle') or (record.get('source') or {}).get('title'),
               'evidence': record.get('evidence'), 'reviewContext': record.get('reviewContext'), 'links': record.get('links')}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def merge_observation(previous: dict, incoming: dict) -> dict:
    if not source_key(previous) or source_key(previous) != source_key(incoming):
        raise ValueError('Cannot merge different source observations')
    result = copy.deepcopy(previous)
    old, new = updated_at(previous), updated_at(incoming)
    if old and (not new or new < old):
        return result
    for field in SOURCE_FIELDS:
        if field in incoming:
            result[field] = copy.deepcopy(incoming[field])
    result['links'] = {**previous.get('links', {}), **{k:v for k,v in incoming.get('links', {}).items() if v}}
    result['sourceEvidenceHash'] = evidence_hash(result)
    for field in STABLE_FIELDS:
        if field in previous:
            result[field] = previous[field]
    return result


def newer_than_public(incoming: dict, public: dict) -> bool:
    old, new = updated_at(public), updated_at(incoming)
    return bool(new and (not old or new > old))


def editorial_decision(payload: dict, record: dict) -> dict:
    """Prefer namespaced decisions; accept only unambiguous legacy provider IDs."""
    key = source_key(record)
    namespaced = payload.get('bySourceKey', {}).get(key)
    if namespaced is not None:
        return namespaced
    source = record.get('source') or {}
    kind, identifier = source.get('type') or 'unknown', str(source.get('id') or '')
    if kind not in {'arxiv', 'unknown'} and not identifier.startswith(kind + ':'):
        return {}
    return payload.get('bySourceId', {}).get(identifier, {})

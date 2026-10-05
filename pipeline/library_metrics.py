"""Project Library observations onto records using the same attention fields as Radar."""
from __future__ import annotations
import copy


def apply_library_metrics(records, payload):
    """Overlay Library observations on existing attention.

    Observations may cover only some signals (the GitHub star refresher writes
    stars alone). Fields an observation does not mention keep the value the
    record already had, e.g. Hugging Face upvotes measured by the Radar
    pipeline; fields it sets explicitly, including None for not-applicable
    shared resources, replace the old value.
    """
    observations = {r['benchmarkId']: r for r in payload.get('records', [])}
    for record in records:
        raw = observations.get(record['id'])
        if raw is None:
            continue
        observed = copy.deepcopy(raw)
        observed.pop('benchmarkId', None)
        attention = copy.deepcopy(record.get('attention') or {})
        status = {**(attention.get('signalStatus') or {}), **(observed.pop('signalStatus', None) or {})}
        for key, value in observed.items():
            # A failed fetch is not evidence; only a not-applicable status clears a value.
            if value is None and key in attention and (status.get(key) or {}).get('state') != 'not_applicable':
                continue
            attention[key] = value
        if status:
            attention['signalStatus'] = status
        record['attention'] = attention
        if raw.get('hfPaperUrl'):
            record.setdefault('links', {})['hfPaper'] = raw['hfPaperUrl']

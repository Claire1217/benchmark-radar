"""Project opt-in Library observations using the same attention fields as Radar."""
import copy


def apply_library_metrics(records, payload):
    observations = {r['benchmarkId']: r for r in payload.get('records', [])}
    for record in records:
        raw = observations.get(record['id'])
        if raw is None:
            continue
        attention = copy.deepcopy(raw)
        attention.pop('benchmarkId', None)
        record['attention'] = attention
        if raw.get('hfPaperUrl'):
            record.setdefault('links', {})['hfPaper'] = raw['hfPaperUrl']

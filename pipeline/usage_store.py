"""Read and align source-qualified benchmark usage evidence (standard library only)."""
from __future__ import annotations
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

def norm(text):
    return re.sub(r'[^\w]+', '', str(text).casefold())

def url_key(value):
    p = urlsplit(value or '')
    host = p.netloc.lower().removeprefix('www.')
    path = p.path.rstrip('/').removesuffix('.git')
    if host in {'arxiv.org', 'export.arxiv.org'}:
        path = re.sub(r'^/(abs|pdf)/', '/', path)
        path = re.sub(r'(v\d+)?(\.pdf)?$', '', path)
        host = 'arxiv.org'
    if host == 'github.com':
        path = path.lower()
    return host + path if host else ''

def align(records, library):
    """Exact primary name AND common URL; aliases and shared papers never suffice."""
    by_name = {}
    for r in library:
        by_name.setdefault(norm(r['name']), []).append(r)
    result = {}
    for r in records:
        urls = {url_key(u) for u in r.get('identityUrls', [])} - {''}
        candidates = []
        for local in by_name.get(norm(r['name']), []):
            local_urls = {url_key(u) for u in (local.get('links') or {}).values() if isinstance(u, str)} - {''}
            if urls & local_urls:
                candidates.append(local['id'])
        result[r['id']] = {'localId': candidates[0] if len(candidates) == 1 else None,
                           'status': 'exact_name_and_url' if len(candidates) == 1 else 'ambiguous' if candidates else 'unmapped',
                           'candidates': sorted(candidates)}
    return result

class UsageStore:
    def __init__(self, data_dir=None, library=None):
        self.data_dir = Path(data_dir or ROOT / 'data')
        self.library = library if library is not None else json.loads((self.data_dir / 'library_index.json').read_text())['records']
        usage = self.data_dir / 'usage'
        self.manifest = json.loads((usage / 'manifest.json').read_text())
        self.records = json.loads((usage / 'benchmarks.json').read_text())
        self.documents = {r['id']: r for r in json.loads((usage / 'documents.json').read_text())}
        self.mentions = [json.loads(l) for l in (usage / 'mentions.jsonl').read_text().splitlines() if l.strip()]
        self.observations = [json.loads(l) for l in (usage / 'observations.jsonl').read_text().splitlines() if l.strip()]
        self.alignment = align(self.records, self.library)
        self.entities = {r['id']: dict(r, usageSourceIds=[]) for r in self.library}
        self.edges = {}
        self.scores = {}
        for r in self.records:
            lid = self.alignment[r['id']]['localId']
            if lid:
                self.entities[lid]['usageSourceIds'].append(r['id'])
                self.entities[lid]['aliases'] = sorted(set(self.entities[lid].get('aliases', [])) | set(r.get('aliases', [])))
            else:
                self.entities[r['id']] = dict(r, usageSourceIds=[r['id']], recordType='imported-evidence')
        for row in self.mentions:
            self.edges.setdefault(row['benchmarkId'], []).append(row)
        for row in self.observations:
            self.scores.setdefault(row['benchmarkId'], []).append(row)

    def summary(self, source_ids):
        mentions = {r['id']: r for k in source_ids for r in self.edges.get(k, [])}
        observations = {r['id']: r for k in source_ids for r in self.scores.get(k, [])}
        official = [r for r in mentions.values() if r['kind'] == 'upstream_report_mention']
        labs = sorted({self.documents[r['documentId']]['organization'] for r in official if self.documents[r['documentId']].get('organization')})
        dates = [str(self.documents[r['documentId']].get('revised') or self.documents[r['documentId']].get('published')) for r in official if self.documents[r['documentId']].get('revised') or self.documents[r['documentId']].get('published')]
        kinds = {}
        for row in observations.values():
            kinds[row['kind']] = kinds.get(row['kind'], 0) + 1
        return dict(reportedLabCount=len(labs), reportedLabs=labs,
                    reportCount=len({r['documentId'] for r in official}),
                    scoreObservationCount=len(observations), observationsByKind=kinds,
                    firstReported=min(dates, default=None), lastReported=max(dates, default=None),
                    instruments=sorted({str(r['instrument']) for r in observations.values() if r.get('instrument')}),
                    actualRunCount=None, lifecycle='unknown', saturation='unknown', influenceScore=None,
                    evidenceStatus='upstream_curated_not_independently_verified',
                    coverage='Imported snapshot only; zero means no matching evidence in this snapshot.')

    def show(self, entity):
        keys = entity.get('usageSourceIds', [])
        mentions = sorted({r['id']: r for k in keys for r in self.edges.get(k, [])}.values(), key=lambda x: x['id'])
        observations = sorted({r['id']: r for k in keys for r in self.scores.get(k, [])}.values(), key=lambda x: x['id'])
        docs = sorted({r['documentId'] for r in mentions} | {r['documentId'] for r in observations if r.get('documentId')})
        return {'benchmark': {'id': entity['id'], 'name': entity['name'], 'sourceIds': keys},
                'usage': self.summary(keys), 'mentions': mentions, 'observations': observations,
                'documents': [self.documents[k] for k in docs if k in self.documents],
                'unknowns': ['Internal evaluation runs are not observable.', 'Report mentions are not independently verified adoption.',
                             'Missing reports do not prove retirement.', 'Scores are not pooled across sources, versions or protocols.']}

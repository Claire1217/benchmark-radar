"""Trimmed record files for the website.

data/library_index.json and data/benchmarks_index.json are public downloads
(llms.txt, schema.org DataDownload), so they stay complete. The pages load
*_view.json copies contain only presentation and search fields. Nested evidence
and operational histories remain available in the complete public downloads.
"""
from __future__ import annotations
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VIEWS = {'library_index.json': 'library_view.json', 'benchmarks_index.json': 'radar_view.json'}

FIELDS = set('id name oneLine description releasedAt releaseDatePrecision readiness links '
             'attention source ranking publication attentionForecast watch dataStatus '
             'displayEligible evaluationMode evaluationRole applicationDomains capabilityGroups '
             'topics aliases domainScope researchDirections researchTopics libraryCategories '
             'benchmarkTaxonomy publishers growth detail modelReportReferences catalogModelCount '
             'releaseEvidence firstRelease identityReviewNote descriptionProvenance'.split())
NESTED = {
    'attention': 'hfPaperUpvotes githubStars hfDatasetDownloads githubScope githubRepo',
    'links': 'report paper project code data hfPaper',
    'publication': 'status venue', 'source': 'type', 'watch': 'status horizon',
    'attentionForecast': 'score', 'descriptionProvenance': 'basis',
    'releaseEvidence': 'note sourceUrl dateScope basis', 'firstRelease': 'sourceUrl',
    'benchmarkTaxonomy': 'tasks capabilities environments modalities protocols',
}


def pick(value, keys):
    return {k: v for k, v in value.items() if k in keys.split()}


def presentation(payload):
    result = slim(payload, FIELDS)
    for record in result['records']:
        for field, keys in NESTED.items():
            if isinstance(record.get(field), dict):
                record[field] = pick(record[field], keys)
        if isinstance(record.get('ranking'), dict):
            record['ranking'] = {k: pick(v, 'rank score') for k, v in record['ranking'].items() if isinstance(v, dict)}
        if isinstance(record.get('growth'), dict):
            g = record['growth']
            record['growth'] = {k: pick(v, '1m 3m stages') if k == 'githubStars' else pick(v, '1m') if isinstance(v, dict) else v
                                for k, v in g.items() if k in {'githubStars', 'hfPaperUpvotes', 'hfDatasetDownloads', 'starsThrough'}}
        if isinstance(record.get('detail'), dict):
            detail = pick(record['detail'], 'description task adoption leaderboard')
            for key, fields in [('adoption', 'independentOrganizations'), ('leaderboard', 'resultCount bestScore')]:
                if isinstance(detail.get(key), dict):
                    detail[key] = pick(detail[key], fields)
            record['detail'] = detail
        for field, keys in [('publishers', 'name role'), ('modelReportReferences', 'provider sourceId')]:
            if isinstance(record.get(field), list):
                record[field] = [pick(v, keys) for v in record[field]]
    return result


def bootstrap(radar, library):
    manifest = radar['manifest']
    latest = manifest.get('latestBatch', {}).get('to') or manifest.get('latestSourceDate') or manifest['dataAsOf']
    records = [r for r in radar['records'] if r.get('displayEligible') is not False
               and r.get('evaluationMode') != 'viewpoint_probe' and r.get('releasedAt', '') <= latest]
    records.sort(key=lambda r: r['releasedAt'], reverse=True)
    first_day = records[min(9, len(records) - 1)]['releasedAt'] if records else latest
    initial = [r for r in records if r['releasedAt'] >= first_day]
    earlier = [r['releasedAt'] for r in records if r['releasedAt'] < first_day]
    return {'records': initial, 'manifest': pick(manifest, 'dataAsOf latestSourceDate latestBatch updateStatus'),
            'libraryManifest': pick(library['manifest'], 'libraryTaxonomy identityRedirects'),
            'previousDate': max(earlier, default=None)}


def referenced_names(web: Path = ROOT / 'web') -> set[str]:
    names = set()
    for path in web.rglob('*.js'):
        text = path.read_text(encoding='utf-8')
        names.update(re.findall(r'[A-Za-z_$][\w$]*', text))
    return names


def slim(payload: dict, names: set[str]) -> dict:
    keep = lambda record: {k: v for k, v in record.items() if k in names}
    return {**payload, 'records': [keep(r) for r in payload['records']]}


def write_views(data_dir: Path, names: set[str] | None = None) -> dict:
    sizes = {}
    for source, target in VIEWS.items():
        payload = json.loads((data_dir / source).read_text(encoding='utf-8'))
        text = json.dumps(presentation(payload) if names is None else slim(payload, names), ensure_ascii=False, separators=(',', ':'))
        (data_dir / target).write_text(text + '\n', encoding='utf-8')
        sizes[target] = len(text)
    return sizes

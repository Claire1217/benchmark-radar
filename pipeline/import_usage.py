"""Import facts from a pinned Benchmark Radar release; never import editorial prose."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from usage_store import ROOT

def is_vendor_report(document):
    return (document.get('source') == 'model_reports'
            and bool(document.get('organization'))
            and document.get('document_type') in {'model_card', 'system_card', 'technical_report', 'release_post'})

def identifier(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()[:24]

def build(zip_path, output):
    archive = Path(zip_path)
    z = zipfile.ZipFile(archive)
    index = json.loads(z.read('benchmark-index.json'))
    records, docs, mentions, scores = [], {}, {}, {}
    for entry in sorted(index['benchmarks'], key=lambda r: r['key']):
        shard = json.loads(z.read('benchmarks/' + entry['slug'] + '.json'))
        r = shard['record']; rid = 'usage:' + r['key']
        urls = [entry.get('source_url')] + [x.get('url') for x in r.get('artifacts', [])]
        urls += [(r.get('provenance') or {}).get('source_url')]
        records.append({'id': rid, 'key': r['key'], 'name': r['name'], 'aliases': r.get('aliases', []),
                        'source': r['source'], 'categories': r.get('categories', []),
                        'identityUrls': sorted({u for u in urls if u}), 'released': r.get('released')})
        for d in r.get('documents', []):
            did = d['id']
            clean = {k: d.get(k) for k in ('id', 'source', 'source_id', 'source_url', 'document_type', 'organization', 'model_name', 'published', 'revised', 'retrieved_at')}
            if did in docs and docs[did] != clean:
                raise ValueError('Conflicting document identity: ' + did)
            docs[did] = clean
            kind = 'upstream_report_mention' if is_vendor_report(d) else 'external_document_reference'
            mid = identifier(rid, did, kind)
            mentions[mid] = {'id': mid, 'benchmarkId': rid, 'documentId': did, 'kind': kind}
        for source, group in shard.get('scores_by_source', {}).items():
            for raw in group.get('rows', []):
                oid = raw.get('observation_id') or raw.get('obs_id')
                if not oid:
                    raise ValueError('Missing observation ID')
                sid = identifier(source, oid)
                kind = raw.get('measurement_kind') if source == 'model_reports' else 'external_evaluation'
                kind = kind or 'unknown'
                score = {'id': sid, 'upstreamId': oid, 'benchmarkId': rid, 'source': source,
                         'documentId': raw.get('document_id'), 'kind': kind}
                score.update({k: raw.get(k) for k in ('model_id', 'model_name', 'organization', 'instrument', 'protocol', 'value', 'raw_value', 'value_kind', 'series_id', 'reported_at', 'reported_date', 'date_precision', 'source_url', 'read_from', 'measured_by', 'reported_by')})
                score['unit'] = entry.get('unit'); score['direction'] = entry.get('score_direction')
                if sid in scores and scores[sid] != score:
                    raise ValueError('Conflicting observation ID')
                scores[sid] = score
    for row in [*mentions.values(), *scores.values()]:
        if row.get('documentId') and row['documentId'] not in docs:
            raise ValueError('Unresolved document: ' + row['documentId'])
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in [('benchmarks', records), ('documents', sorted(docs.values(), key=lambda x: x['id']))]:
        (output / (name + '.json')).write_text(json.dumps(rows, ensure_ascii=False, separators=(',', ':'))+'\n')
    for name, rows in [('mentions', mentions), ('observations', scores)]:
        (output / (name+'.jsonl')).write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':'))+'\n' for _, r in sorted(rows.items())))
    dates = [str(d.get('revised') or d['published']) for d in docs.values() if is_vendor_report(d) and d.get('published')]
    manifest = {'schemaVersion': '1.0', 'datasetVersion': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'sourceRepository': 'https://github.com/ktwu01/benchmark-radar',
                'sourceArchive': 'https://github.com/ktwu01/benchmark-radar/releases/download/cli-data/benchmark-radar-data.zip',
                'counts': {'benchmarks': len(records), 'documents': len(docs), 'mentions': len(mentions), 'observations': len(scores)},
                'latestRegisteredReportDate': max(dates, default=None),
                'attribution': 'Benchmark Radar, Koutian Wu and contributors; underlying report and evaluation sources retained per row.',
                'contentScope': 'Source identifiers, bibliographic facts, reported metrics and references only. Upstream editorial descriptions and judgments are omitted.',
                'verification': 'Imported source assertions; not independently verified. No inferred retirement or saturation.'}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('archive', type=Path); p.add_argument('--output', type=Path, default=ROOT/'data/usage')
    args=p.parse_args(); print(json.dumps(build(args.archive, args.output)))

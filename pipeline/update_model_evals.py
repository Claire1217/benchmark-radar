#!/usr/bin/env python3
"""Apply reviewed provider evidence to the existing Model Evals snapshot.

The embedded historical dataset is retained. New evidence is a durable JSON
overlay, so this update is reproducible without scraping or replacing history.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA_PATTERN = re.compile(r'(<script id="preview-data" type="application/json">)(.*?)(</script>)', re.S)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_score(value, benchmark):
    if not finite(value):
        return False
    if benchmark['unit'] in {'signed_percent', 'signed_score'}:
        return -100 <= value <= 100
    if benchmark['unit'] in {'%', 'score'}:
        return 0 <= value <= 100
    if benchmark['unit'] == 'rating':
        return 1 <= value <= 10
    return True


def preferred(rows):
    """Latest report first; within that report retain its headline row order."""
    return sorted(rows, key=lambda row: row.get('reported_at', ''), reverse=True)[0]


def apply_updates(data, updates):
    sources = updates['sources']
    model_ids = {model['id'] for model in updates['models']}
    if len(model_ids) != len(updates['models']):
        raise ValueError('Duplicate reviewed model identity')
    for model in updates['models']:
        data['models'][model['id']] = dict(model)
    data['benchmarks'].update(updates['benchmarks'])
    # Replace only evidence owned by this overlay. Reruns cannot duplicate rows.
    data['observations'] = [row for row in data['observations'] if row.get('reviewOverlay') != 'provider-updates']
    for raw in updates['observations']:
        row = dict(raw)
        model = data['models'][row['model_id']]
        benchmark = data['benchmarks'][row['benchmark_id']]
        source = sources[row['sourceId']]
        if source['url'] != row['source_url']:
            raise ValueError('Source URL mismatch')
        if source['provider'] != model['organization']:
            raise ValueError('A competitor table is not a self-reported score')
        if source['publishedAt'] != row['reported_at']:
            raise ValueError('Report date mismatch')
        if not row.get('coverage_only'):
            value = row['display_value']
            if not valid_score(value, benchmark):
                raise ValueError('Invalid reviewed score')
        elif row['display_value'] is not None or row['scale_verified']:
            raise ValueError('Coverage must not imply a numeric result')
        if row['reported_at'] < model['date']:
            raise ValueError('Evidence predates model release')
        row['reviewOverlay'] = 'provider-updates'
        row['id'] = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:24]
        data['observations'].append(row)
    if len({row['id'] for row in data['observations']}) != len(data['observations']):
        raise ValueError('Duplicate observation identity')
    for mid in {row['model_id'] for row in updates['observations']}:
        rows = [row for row in data['observations'] if row['model_id'] == mid]
        data['models'][mid].update(
            score_count=sum(finite(row['display_value']) for row in rows),
            benchmark_count=len({row['benchmark_id'] for row in rows}),
        )
    for org in {model['organization'] for model in updates['models']}:
        ids = set(data['flagship_models'].get(org, [])) | {
            model['id'] for model in updates['models'] if model['organization'] == org
        }
        data['flagship_models'][org] = sorted(ids, key=lambda mid: (
            data['models'][mid].get('date', ''), data['models'][mid]['name']), reverse=True)
        # Imported averages do not incorporate this review. Do not extend them
        # across changed protocols, missing values, or Elo/percentage scales.
        data['company_trends'].pop(org, None)
    for bid in updates['benchmarks']:
        benchmark = data['benchmarks'][bid]
        rows_by_model = {}
        for row in data['observations']:
            if row['benchmark_id'] == bid and finite(row['display_value']):
                rows_by_model.setdefault(row['model_id'], []).append(row)
        rows = [preferred(group) for group in rows_by_model.values()]
        closest = benchmark['direction'] == 'closer_to_zero_is_better'
        if benchmark['direction'] in {'higher_is_better', 'lower_is_better', 'closer_to_zero_is_better'}:
            rows.sort(key=lambda row: abs(row['display_value']) if closest else row['display_value'],
                      reverse=not closest and benchmark['direction'] != 'lower_is_better')
        # Exact version/subset/tool rows only. No cross-version family pooling.
        data['charts'][bid] = dict(
            scale_label=benchmark['scale_label'], unit='%' if benchmark['unit'] in {'%', 'signed_percent'} else '',
            direction=benchmark['direction'], rows=rows, eligible=len(rows),
            scale_max=100 if benchmark['unit'] in {'%', 'score'} else 10 if benchmark['unit'] == 'rating' else None,
        )
    data['reviewed_sources'] = sources
    # Core rankings require explicit benchmark-level eligibility and row provenance.
    # An official provider URL or a verified scale alone never establishes this.
    audits = updates.get('benchmarkAudits', {})
    snapshots = updates.get('leaderboardSnapshots', {})
    for bid, snapshot in snapshots.items():
        if not audits.get(bid, {}).get('coreEligible'):
            raise ValueError('Official ranking requires a compatible benchmark audit')
        if not snapshot.get('source_url', '').startswith('https://') or not snapshot.get('retrievedAt'):
            raise ValueError('Official ranking requires a dated source')
        for row in snapshot['rows']:
            if row.get('provenance') != 'benchmark_evaluation' or not finite(row.get('display_value')) or not row.get('setting'):
                raise ValueError('Unverified or unspecified run cannot enter core ranking')
            if not valid_score(row['display_value'], data['benchmarks'][bid]):
                raise ValueError('Invalid official score')
    data['leaderboard_snapshots'] = snapshots
    data['benchmark_audits'] = audits
    model_audits = updates.get('modelBenchmarkAudits', {})
    for mid, metrics in model_audits.items():
        if mid not in data['models']:
            raise ValueError('Unknown model in benchmark audit')
        for bid, audit in metrics.items():
            if bid not in data['benchmarks'] or not audit.get('checkedAt') or not audit.get('note'):
                raise ValueError('Model benchmark audit requires a known metric and dated rationale')
            if audit.get('coreEligible') and audit.get('snapshotId', bid) not in snapshots:
                raise ValueError('Model benchmark audit requires an existing official snapshot')
    data['model_benchmark_audits'] = model_audits
    data['report_audits'] = updates.get('reportAudits', {})
    comparisons = updates.get('reportComparisons', {})
    for mid, metrics in comparisons.items():
        for bid, comparison in metrics.items():
            source = sources[comparison['sourceId']]
            if (comparison['selected_model_id'] != mid or source['url'] != comparison['source_url']
                    or source['provider'] != comparison['publisher']
                    or data['models'][mid]['organization'] != comparison['publisher']
                    or source['publishedAt'] != comparison['publishedAt']):
                raise ValueError('Comparison must belong to the selected model publisher and one source')
            for row in comparison['rows']:
                value = row['display_value']
                if row['provenance'] != 'publisher_comparison' or (value is not None and not finite(value)):
                    raise ValueError('Invalid publisher comparison value or provenance')
                if row['plot_eligible'] and (value is None or row['exception']):
                    raise ValueError('Missing or incompatible comparison cannot enter plot')
                if value is not None and not valid_score(value, data['benchmarks'][bid]):
                    raise ValueError('Invalid comparison score')
            own = [r for r in comparison['rows'] if r.get('model_id') == mid]
            if len(own) != 1 or own[0]['display_value'] != data['report_audits'][bid][mid]['value']:
                raise ValueError('Selected comparison result must match its report receipt')
    data['report_comparisons'] = comparisons
    from build_model_eval_review import build_review
    queue, report_html = build_review(data, updates)
    data['manifest']['batchReview'] = queue['summary']
    data['observations'].sort(key=lambda row: row.get('reported_at', ''), reverse=True)
    data['manifest']['reviewedUpdates'] = dict(
        reviewedAt=updates['reviewedAt'], latestModelDate=max(model['date'] for model in updates['models']),
        models=len(model_ids), benchmarks=len(updates['benchmarks']),
        numericObservations=sum(not row.get('coverage_only') for row in updates['observations']),
        coverageOnlyObservations=sum(bool(row.get('coverage_only')) for row in updates['observations']),
        policy=updates['policy'],
    )
    # Preserve the imported manifest's original dates/counts and authority.
    return data


def update_references(references, updates, data, library):
    known = {record['id'] for record in library['records']}
    refs = references['references']
    for bid, benchmark in updates['benchmarks'].items():
        lid = benchmark.get('libraryId')
        if not lid:
            continue
        if lid not in known:
            raise ValueError(f'Unknown reviewed Library ID: {lid}')
        for row in updates['observations']:
            if row['benchmark_id'] != bid:
                continue
            model = data['models'][row['model_id']]
            incoming = dict(sourceId=row['sourceId'], url=row['source_url'],
                            provider=model['organization'], model=model['name'],
                            modelDate=model['date'], evidence='reviewed-provider-model-card')
            target = refs.setdefault(lid, [])
            if not any((r['provider'], r['model'], r['url']) == (
                    incoming['provider'], incoming['model'], incoming['url']) for r in target):
                target.append(incoming)
    references['manifest'].update(
        generatedAt=updates['reviewedAt'], latestModelDate=max(model['date'] for model in updates['models']),
        libraryBenchmarkCount=len(refs), reportReferenceCount=sum(map(len, refs.values())),
    )
    return references


def main():
    updates = json.loads((ROOT / 'data/model_eval_updates.json').read_text())
    page = ROOT / 'web/model-evals/index.html'
    html = page.read_text()
    match = DATA_PATTERN.search(html)
    if not match:
        raise ValueError('Missing Model Evals dataset')
    data = apply_updates(json.loads(match[2]), updates)
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    path = ROOT / 'data/model_eval_references.json'
    refs = update_references(json.loads(path.read_text()), updates, data,
                             json.loads((ROOT / 'data/library_index.json').read_text()))
    page.write_text(html[:match.start(2)] + encoded + html[match.end(2):])
    path.write_text(json.dumps(refs, ensure_ascii=False, indent=2) + '\n')
    from build_model_eval_review import build_review
    queue, report_html = build_review(data, updates)
    (ROOT / 'data/model_eval_review_queue.json').write_text(json.dumps(queue, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'web/model-evals/review.html').write_text(report_html)
    print(json.dumps(data['manifest']['reviewedUpdates'], ensure_ascii=False))


if __name__ == '__main__':
    main()

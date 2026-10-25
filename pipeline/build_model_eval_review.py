"""Build a resumable review inventory and a public evidence page from receipts."""
from collections import defaultdict
from html import escape


def build_review(data, updates):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in data['observations']:
        grouped[row['model_id']][row['benchmark_id']].append(row)
    models = []
    for mid in sorted(grouped, key=lambda k: (data['models'][k].get('date', ''), k), reverse=True):
        model = data['models'][mid]
        pairs = []
        for bid, rows in grouped[mid].items():
            comparison = data.get('report_comparisons', {}).get(mid, {}).get(bid)
            receipt = data.get('report_audits', {}).get(bid, {}).get(mid)
            audit = data.get('model_benchmark_audits', {}).get(mid, {}).get(bid)
            if comparison:
                report_status = {
                    'not_reported': 'source_not_reported',
                    'unlabeled_figure': 'source_without_exact_value',
                    'no_single_score': 'source_without_exact_value',
                }.get(comparison.get('valueStatus'), 'comparison_verified')
            else:
                report_status = 'value_verified' if receipt else 'pending'
            board_status = audit.get('status', 'pending') if audit else 'pending'
            reviewed = bool(comparison and audit and board_status != 'pending')
            pairs.append(dict(
                benchmarkId=bid, benchmark=data['benchmarks'][bid]['name'],
                reportStatus=report_status, leaderboardStatus=board_status,
                status='reviewed' if reviewed else 'in_progress' if comparison or receipt or audit else 'pending',
                reportUrl=(comparison or {}).get('source_url') or (receipt or {}).get('source_url') or model.get('model_card_url'),
                leaderboardUrl=(audit or {}).get('benchmark_url'),
                note=(audit or {}).get('note', ''),
                sourceRecordIds=[r['id'] for r in rows],
            ))
        done = sum(p['status'] == 'reviewed' for p in pairs)
        coverage = updates.get('modelAudits', {}).get(mid, {}).get('sourceCoverageStatus', 'pending')
        models.append(dict(modelId=mid, name=model['name'], provider=model['organization'],
                           releasedAt=model.get('date'), modelCardUrl=model.get('model_card_url'),
                           sourceCoverageStatus=coverage,
                           status='reviewed' if done == len(pairs) and coverage == 'complete' else 'in_progress' if done else 'pending',
                           discoveredMetrics=updates.get('modelAudits', {}).get(mid, {}).get('discoveredMetrics', []),
                           reviewedPairs=done, totalPairs=len(pairs), pairs=pairs))
    summary = dict(modelsWithRecords=len(models), totalPairs=sum(m['totalPairs'] for m in models),
                   reviewedPairs=sum(m['reviewedPairs'] for m in models),
                   reviewedModels=sum(m['status'] == 'reviewed' for m in models),
                   catalogModelsWithoutRecords=len(data['models']) - len(models))
    queue = dict(schemaVersion=1, scope='All currently collected model–benchmark pairs, including non-numeric disclosures. New source discoveries must be added to the inventory. Catalog-only identities are not counted as reviewed.',
                 order='Newest release first; preserve variants and source-qualified identities.', summary=summary, models=models)
    e = lambda v: escape('' if v is None else str(v))
    def link(url, text):
        return '<a href="'+escape(url, quote=True)+'">'+e(text)+'</a>' if url and url.startswith(('https://', 'http://')) else e(text)
    labels = {'pending':'Not yet reviewed', 'value_verified':'Value verified; comparison pending',
              'source_without_exact_value':'Source reviewed; no exact value',
              'source_not_reported':'Not in this model’s report; references retained',
              'comparison_verified':'Source comparison verified', 'not_listed':'Model absent from captured board',
              'matched':'Matched official board', 'historical_board':'Historical board only',
              'protocol_mismatch':'Evaluation setup differs', 'internal':'Internal benchmark',
              'protocol_unverified':'Matching evaluation setup not verified',
              'no_verified_board':'No matching official board verified', 'republished_report':'Publisher result republished',
              'ambiguous_metric':'Metric unresolved', 'source_unavailable':'Source unavailable',
              'not_found':'No matching board found', 'unresolved_identity':'Benchmark identity unresolved'}
    html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Model Evals · Review progress</title><style>body{max-width:1100px;margin:32px auto;padding:0 20px;font:14px/1.6 system-ui;color:#17211c;background:#fafaf8}a{color:#285b90}details{margin:16px 0;border:1px solid #d7ded8;border-radius:5px;padding:12px}summary{cursor:pointer;font-weight:600}.table{overflow:auto}table{width:100%;border-collapse:collapse}td,th{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #d7ded8}th{background:#eaf0eb}small,.muted{color:#68736c}h1{font-size:28px}h3{margin-bottom:4px}.evidence{margin:20px 0}code{overflow-wrap:anywhere}</style></head><body><a href="./">← Model Evals</a><h1>Review progress</h1>'''
    html += '<p>'+str(summary['reviewedPairs'])+' / '+str(summary['totalPairs'])+' model–benchmark pairs reviewed across '+str(summary['modelsWithRecords'])+' models.</p>'
    html += '<p>Each comparison belongs to one publisher report. Benchmark-maintainer evaluations are reviewed separately for the exact version, subset and metric. “Not yet reviewed” does not mean a result is unavailable. Source verification checks transcription and evaluation scope; it does not reproduce the experiment.</p>'
    html += '<p>Reviewed includes documented unresolved sources and incompatible setups; these never enter the official ranking. Models are complete only after source coverage and every collected metric have been reviewed. '+str(summary['catalogModelsWithoutRecords'])+' catalog-only identities have no collected results and are not counted as reviewed.</p><p><a href="audit-2026-10-24.html">October 24 Kimi audit and complete official snapshots ↗</a></p>'
    for model in models:
        mid=model['modelId']
        html += '<details id="'+e(mid)+'"><summary>'+e(model['name'])+' · '+str(model['reviewedPairs'])+' / '+str(model['totalPairs'])+' metrics reviewed</summary>'
        html += '<p>'+link(model['modelCardUrl'],'Model card / release report')+' · Source coverage: '+e(model['sourceCoverageStatus'])+'</p><div class="table"><table><thead><tr><th>Benchmark</th><th>Model report</th><th>Benchmark leaderboard</th></tr></thead><tbody>'
        for pair in model['pairs']:
            html += '<tr><td>'+e(pair['benchmark'])+'</td><td>'+link(pair['reportUrl'],labels.get(pair['reportStatus'],pair['reportStatus']))+'</td><td>'+link(pair['leaderboardUrl'],labels.get(pair['leaderboardStatus'],pair['leaderboardStatus']))+(('<br><small>'+e(pair['note'])+'</small>') if pair['note'] else '')+'</td></tr>'
        html += '</tbody></table></div>'
        if model['discoveredMetrics']:
            html += '<p>Additional source metrics awaiting ingestion: '+e(', '.join(d['name'] for d in model['discoveredMetrics']))+'.</p>'
        for bid,c in data.get('report_comparisons',{}).get(mid,{}).items():
            html += '<details class="evidence"><summary>'+e(data['benchmarks'][bid]['name'])+' · original comparison values</summary><p>'+link(c['source_url'],c['title'])+' · published '+e(c['publishedAt'])+' · checked '+e(c['checkedAt'])+'</p><p>'+e(c['setting'])+'</p><p>'+e(c.get('note'))+'</p>'
            for source in c.get('supportingSources', []):
                html += '<p>'+link(source['url'],source['locator'])+'</p>'
            if c.get('source_table_sha256'):
                hash_label = 'Transcription SHA-256' if c.get('source_table_hash_basis') else 'Source snapshot SHA-256'
                html+='<p class="muted">'+hash_label+': <code>'+e(c['source_table_sha256'])+'</code></p>'
            html += '<div class="table"><table><thead><tr><th>Original model column</th><th>Original value</th><th>Displayed value</th><th>Setting / exception</th></tr></thead><tbody>'
            for row in c['rows']:
                html += '<tr><td>'+e(row['source_column'])+'</td><td>'+e(row.get('source_value') if row.get('source_value') is not None else '—')+'</td><td>'+e(row['display_text'])+'</td><td>'+e(row.get('exception') or row.get('setting'))+'</td></tr>'
            html += '</tbody></table></div>'
            for supplement in c.get('supplementaryComparisons', []):
                html += '<details><summary>'+e(supplement['title'])+' · supplementary report evidence</summary><p>'+link(supplement['source_url'],supplement['source_table_label'])+' · published '+e(supplement['publishedAt'])+' · checked '+e(supplement['checkedAt'])+'</p><p>'+e(supplement['setting'])+'</p><p>'+e(supplement.get('note'))+'</p>'
                html += '<p class="muted">These settings are kept separately from the headline comparison and official ranking. Transcription SHA-256: <code>'+e(supplement['source_table_sha256'])+'</code></p>'
                html += '<div class="table"><table><thead><tr><th>Model</th><th>Condition</th><th>Original value</th><th>Displayed value / limitation</th></tr></thead><tbody>'
                for row in supplement['rows']:
                    html += '<tr><td>'+e(row['name'])+'</td><td>'+e(row['setting'])+'</td><td>'+e(row['source_value'])+'</td><td>'+e(row['display_text'])+(('<br><small>'+e(row['exception'])+'</small>') if row.get('exception') else '')+'</td></tr>'
                html += '</tbody></table></div></details>'
            html += '</details>'
        html += '</details>'
    html += '<h2 id="official-snapshots">Captured official runs</h2>'
    for bid,s in data.get('leaderboard_snapshots',{}).items():
        html += '<details><summary>'+e(s['title'])+' · '+str(len(s['rows']))+' runs</summary><p>'+link(s['source_url'],'Official source')+' · captured '+e(s['retrievedAt'])+'</p><p>'+e(s.get('displayNote') or s.get('note'))+'</p><div class="table"><table><thead><tr><th>Model</th><th>Score</th><th>Evaluation settings</th></tr></thead><tbody>'
        for row in s['rows']:
            html += '<tr><td>'+e(row['name'])+'</td><td>'+e(row['display_text'])+'</td><td>'+e(row['setting'])+'</td></tr>'
        html += '</tbody></table></div></details>'
    html += '</body></html>'
    return queue, html

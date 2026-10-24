#!/usr/bin/env python3
"""Plan or apply a replay-safe historical reconciliation, never publish records."""
from __future__ import annotations
import argparse
import copy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError
import xml.etree.ElementTree as ET

import discover_benchmarks as discovery
import index_benchmarks as index
from evidence_facets import retain_sources
from source_identity import source_key, merge_observation, newer_than_public
import source_coverage

ROOT=Path(__file__).resolve().parents[1]
VERSION='historical-workflow-v1'

def load(path,default):
    return json.loads(path.read_text()) if path.exists() else copy.deepcopy(default)

def counts(root):
    records=load(root/'data/library_index.json',{'records':[]})['records']
    return {'stored':len(records),'visible':sum(r.get('displayEligible') is not False and r.get('evaluationMode')!='viewpoint_probe' for r in records),
            'queue':len(load(root/'data/review_queue.json',{'candidates':[]})['candidates'])}

def stable_snapshot(root):
    records=load(root/'data/library_index.json',{'records':[]})['records']
    return {r['id']:{k:r.get(k) for k in ('releasedAt','firstSeenAt','familyId','displayEligible','evaluationMode')} for r in records}

def fetch_case(case,config,now):
    identifier=case['sourceId']
    url=index.ATOM_API_URL+'?'+urlencode({'id_list':identifier,'max_results':1})
    with urlopen(Request(url,headers={'User-Agent':discovery.USER_AGENT}),timeout=20) as response:
        root=ET.fromstring(response.read())
    papers=[index.parse_atom_paper(e) for e in root.findall('atom:entry',index.ATOM_NS)]
    paper=next((p for p in papers if p and p.arxiv_id==identifier),None)
    if paper is None:
        raise RuntimeError('Requested source ID absent from response')
    record=discovery.paper_candidate(paper,config,now)
    if record is None:
        raise RuntimeError('Source below candidate threshold; source review still required')
    return record

def upsert_reassessment(queue,record):
    key=source_key(record)
    if not key: return False
    old=next((r for r in queue['candidates'] if source_key(r)==key),None)
    if old:
        if old != record:
            merged=merge_observation(old,record)
            old.clear();old.update(merged)
        target=old
    else:
        target=copy.deepcopy(record);queue['candidates'].append(target)
    target['reviewReason']='historical-reassessment'
    target['reassessmentVersion']=VERSION
    return True

def run(root,start,end,*,apply=False,max_cases=0,max_seconds=120,fetch=fetch_case):
    if date.fromisoformat(end)<date.fromisoformat(start):raise ValueError('Invalid range')
    if max_cases<0 or max_seconds<0:raise ValueError('Budgets must be non-negative')
    started=time.monotonic();now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    config=load(root/'pipeline/config.json',{})
    library=load(root/'data/library_index.json',{'records':[]})['records']
    canonical=load(root/'data/benchmarks.json',{'records':[]})['records']
    queue=load(root/'data/review_queue.json',{'candidates':[]})
    queue_by_source={source_key(r):r for r in queue['candidates'] if source_key(r)}
    cases=load(root/'data/workflow_audit_cases.json',{'discoveryCases':[]})['discoveryCases']
    state_path=root/'data/historical_reconciliation.json'
    prior_report=load(state_path,{})
    previous=prior_report.get('cases',{})
    report={'schemaVersion':1,'migrationVersion':VERSION,'window':{'from':start,'to':end},'dryRun':not apply,
            'baseline':prior_report.get('baseline') or prior_report.get('before') or counts(root),
            'before':counts(root),'modelReviewAvailable':bool(os.environ.get('DEEPSEEK_API_KEY')),'cases':copy.deepcopy(previous),'hidden':[],
            'limitations':['No admission, unhide or entity merge is performed by this migration.','Queued means durable review work, not a published benchmark.']}
    stable=stable_snapshot(root)
    ledger=source_coverage.load(root/'data/source_coverage.json')
    day=date.fromisoformat(start);last=date.fromisoformat(end)
    while day<=last:
        stop=min(day+timedelta(days=6),last)
        for category in config['arxiv']['categories']:
            source_coverage.enqueue(ledger,'arxiv',category,day.isoformat(),stop.isoformat())
        day=stop+timedelta(days=1)
    for offset in range((last-date.fromisoformat(start)).days+1):
        day=(date.fromisoformat(start)+timedelta(days=offset)).isoformat()
        for provider in ('github','huggingface','openreview'):
            source_coverage.enqueue(ledger,provider,'created-benchmark-v2',day,day)
    report['coverageWindows']={'total':len(ledger['windows']),'complete':sum(w['status']=='complete' for w in ledger['windows'].values())}
    if apply:source_coverage.save(root/'data/source_coverage.json',ledger)
    # Rehydrate hidden primary-source work from canonical/queue evidence, never
    # use stale positive curation fields as permission to restore visibility.
    by_source={source_key(r):r for r in canonical if source_key(r)}
    for candidate in queue['candidates']:
        public=by_source.get(source_key(candidate))
        if public and newer_than_public(candidate,public) and candidate.get('reviewReason')!='historical-reassessment':
            candidate['reviewReason']='source-changed'
    for row in sorted(library,key=lambda r:r['id']):
        if row.get('displayEligible') is not False and row.get('evaluationMode')!='viewpoint_probe':continue
        key=source_key(row);base=queue_by_source.get(key) or by_source.get(key)
        supported=(row.get('source') or {}).get('type') in {'arxiv','github','huggingface','openreview'}
        reason='source-backed-reassessment-required' if supported and base else 'missing-supported-primary-source'
        outcome='queued' if supported and base else 'unresolved'
        report['hidden'].append({'id':row['id'],'sourceKey':key,'outcome':outcome,'reason':reason})
        if apply and outcome=='queued':upsert_reassessment(queue,base)
    if apply:
        queue['candidateCount']=len(queue['candidates']);source_coverage.save(root/'data/review_queue.json',queue)
    attempts=0
    for case in cases:
        key='arxiv:'+case['sourceId'];prior=previous.get(case['id'],{})
        if prior.get('outcome')=='queued' and key in {source_key(r) for r in queue['candidates']}:continue
        item={'sourceUrl':case['sourceUrl'],'sourceKey':key,'outcome':'unresolved','reason':'not-attempted-budget'}
        if apply and attempts<max_cases and time.monotonic()-started<max_seconds:
            attempts+=1
            try:
                observed=fetch(case,config,now)
                base=by_source.get(key)
                record=merge_observation(base,observed) if base else observed
                retain_sources([record],root/'data/source_evidence.json')
                upsert_reassessment(queue,record)
                queue['candidateCount']=len(queue['candidates'])
                source_coverage.save(root/'data/review_queue.json',queue)
                item.update(outcome='queued',reason='source-fetched-admission-review-required',recordId=record['id'],
                            releasedAt=record.get('releasedAt'),sourceUpdatedAt=record.get('sourceUpdatedAt'),
                            releaseWindowMembership=start<=str(record.get('releasedAt',''))<=end,
                            sourceEvidenceSha256=hashlib.sha256(json.dumps(observed,sort_keys=True).encode()).hexdigest())
            except (URLError,TimeoutError,RuntimeError,ValueError,ET.ParseError) as error:
                item.update(reason='source-unavailable-or-unrecognized',error=type(error).__name__)
            report['cases'][case['id']]=item
            source_coverage.save(state_path,report) # after queue/evidence persistence
            if attempts<max_cases:time.sleep(3)
        elif case['id'] not in report['cases']:
            report['cases'][case['id']]=item
    bindings=load(root/'data/catalog_identity_bindings.json',{'bindings':{}})['bindings']
    report['identityReview']=[{'id':k,**v,'outcome':'unresolved','reason':'legacy-binding-needs-primary-source-review'} for k,v in sorted(bindings.items()) if v.get('reviewState')=='needs-source-review']
    report['after']=counts(root)
    report['stablePublicFieldsUnchanged']=stable_snapshot(root)==stable
    if not report['stablePublicFieldsUnchanged']:raise RuntimeError('Migration changed stable public fields')
    if apply:source_coverage.save(state_path,report)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start',required=True);p.add_argument('--end',required=True)
    p.add_argument('--apply',action='store_true');p.add_argument('--max-cases',type=int,default=0)
    p.add_argument('--max-seconds',type=int,default=120);p.add_argument('--output')
    a=p.parse_args()
    if a.output:
        target=Path(a.output).resolve()
        if any(target.is_relative_to(ROOT/area) for area in ('data','web','pipeline','.github')):
            p.error('Report output cannot overwrite product data or code; use outputs/.')
    report=run(ROOT,a.start,a.end,apply=a.apply,max_cases=a.max_cases,max_seconds=a.max_seconds)
    if a.output:source_coverage.save(Path(a.output),report)
    print(json.dumps({k:v for k,v in report.items() if k not in {'hidden','identityReview'}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

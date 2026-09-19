"""Validate shared taxonomy and emit an exhaustive record disposition report."""
import json,collections
from pathlib import Path
from research_topics import VERSION,topic_manifest
ROOT=Path(__file__).resolve().parents[1]
def audit():
 load=lambda n:json.loads((ROOT/'data'/n).read_text())
 library=load('library_index.json');public=load('benchmarks_index.json');trends=load('trends_topics.json');rows=library['records'];byid={r['id']:r for r in rows};manifest=topic_manifest(rows)
 assert library['manifest']['topicTaxonomy']==manifest,'Library manifest drift'
 ids=[t['id'] for t in manifest['directions']];assert len(ids)==20 and len(set(ids))==20
 categories=library['manifest']['libraryTaxonomy']
 assert trends['taxonomyVersion']==categories['version'] and [t['id'] for t in trends['topics']]==[d['id'] for d in categories['directions']],'Trends taxonomy drift'
 for r in public['records']:
  if r['id'] in byid:
   if byid[r['id']].get('repositoryScopeReview'):assert r.get('attention',{}).get('githubScope')==byid[r['id']]['repositoryScopeReview']['scope'],(r['id'],'scope drift')
   for key in ('researchTopics','benchmarkTaxonomy','topicClassification'):assert r[key]==byid[r['id']][key],(r['id'],key)
 for t in trends['topics']:
  assert t['library']==next(d['count'] for d in categories['directions'] if d['id']==t['id']),(t['id'],'count drift')
  for w in t['windows'].values():
   repos=w['repos'];assert len({r['url'].lower() for r in repos})==len(repos)
   assert w['stars']==sum(r['stars'] for r in repos) if repos else w['stars'] is None
   if w['growthRate'] is not None:assert abs(w['growthRate']-100*w['stars']/w['baseline'])<1e-9
 readme=(ROOT/'README.md').read_text();awesome=(ROOT/'AWESOME_BENCHMARKS.md').read_text()
 for t in manifest['directions']:
  assert 'direction='+t['id'] in readme,('README missing topic',t['id'])
  if any(t['id'] in r.get('researchTopics',[]) for r in public['records'] if r.get('displayEligible') is not False and r.get('evaluationMode')!='viewpoint_probe'):assert '## '+t['name'] in awesome
 result={'version':VERSION,'recordCount':len(rows),'featuredTopicCount':20,'topics':[{k:t[k] for k in ('id','name','count')} for t in manifest['directions']],'dispositions':dict(collections.Counter(r['topicClassification']['status'] for r in rows)),'sourceAccess':dict(collections.Counter(r.get('sourceAudit',{}).get('status','not-in-source-refresh') for r in rows)),'sourceVerificationPending':sum(r.get('dataStatus')=='catalog-listed-unverified' for r in rows),'notes':['Every record has a classification disposition; outside featured topics is separate from insufficient evidence.','Source retrieval is not semantic/full-paper verification. Unknown evidence is retained rather than invented.','README, Library, Radar and Trends topic versions, membership and counts are checked together.'],'records':[{'id':r['id'],'name':r['name'],'topics':r['researchTopics'],'status':r['topicClassification']['status'],'reviewFlags':r['topicClassification']['reviewFlags'],'sourceStatus':r.get('sourceAudit',{}).get('status'),'evaluationRole':r.get('evaluationRole'),'hasDate':r.get('releasedAt') not in (None,'','0001-01-01') and r.get('releaseDatePrecision') not in ('unknown','year'),'hasRepository':bool((r.get('links') or {}).get('code'))} for r in rows]}
 (ROOT/'data/research_topic_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Cross-surface audit passed:',result['dispositions']);return result
if __name__=='__main__':audit()

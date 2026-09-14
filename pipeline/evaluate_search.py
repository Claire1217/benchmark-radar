"""Compare old AND-substring search to BM25 on a developer-authored pilot set."""
import json
from pathlib import Path
from benchmark_reader import labels
from cli_discovery import keyword_match
from search_index import SearchIndex, relevance_order
from usage_store import UsageStore, ROOT


def evaluate():
    store=UsageStore()
    store.source_records={r['id']:r for r in store.records}
    records=[r for r in store.entities.values() if r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe']
    suite=json.loads((ROOT/'data/search_eval/queries.json').read_text())
    index=SearchIndex(records,lambda r:labels(r,store))
    results=[]
    for case in suite['cases']:
        query=case['query']; expected=set(case['expectedNames'])
        old=[r for r in records if keyword_match(query,r,labels(r,store))]
        old.sort(key=lambda r:(-store.summary(r.get('usageSourceIds',[]))['reportedLabCount'],r['name'].casefold(),r['id']))
        hits,_=index.search(query)
        new=sorted([dict(index.records[rid],relevance=h) for rid,h in hits.items()],key=relevance_order)
        def metrics(rows):
            names=[r['name'] for r in rows]
            return {'hitAt10':bool(expected&set(names[:10])) if expected else not rows,
                    'top1Exact':names[0] in expected if names and expected else not rows if not expected else False,
                    'candidateCount':len(rows),'top10':names[:10]}
        results.append(dict(case,old=metrics(old),new=metrics(new)))
    index.close()
    summary={}
    for kind in ['identity','intent','no-answer']:
        group=[r for r in results if r['type']==kind]
        metric='top1Exact' if kind=='identity' else 'hitAt10'
        summary[kind]={'queries':len(group),'metric':metric,**{method:sum(r[method][metric] for r in group) for method in ['old','new']}}
    return {'limitations':suite['note']+' Hit@10 checks for one expected example, not recall@10 or precision. No latency claim or full multilingual support is established.', 'summary':summary,'results':results}

if __name__=='__main__':
    print(json.dumps(evaluate(),ensure_ascii=False,indent=2))

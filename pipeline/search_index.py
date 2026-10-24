"""Python adapter for the same deterministic search engine used by both web views."""
import difflib
import json
from pathlib import Path
import shutil
import subprocess

class SearchIndex:
    def __init__(self, records, get_labels):
        self.records = {r['id']: r for r in records}
        node=shutil.which('node')
        if not node:
            raise ValueError('Library search requires Node.js 18+ (shared browser/CLI search runtime).')
        self.process=subprocess.Popen([node,str(Path(__file__).with_name('search_runtime.cjs'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8')
        fields=('id','name','aliases','description','oneLine','searchDocument','evidence','displayEligible','evaluationMode')
        try:
            self._request({'records':[{**{k:r[k] for k in fields if k in r},'_labels':get_labels(r)} for r in records]})
        except Exception:
            self.close()
            raise

    def _request(self, payload):
        self.process.stdin.write(json.dumps(payload,ensure_ascii=False)+'\n')
        self.process.stdin.flush()
        line=self.process.stdout.readline()
        if not line:
            raise ValueError('Shared search runtime exited before returning a result.')
        result=json.loads(line)
        if result.get('error'):
            raise ValueError(result['error'])
        return result

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdout.close()

    def search(self, query, alternatives=()):
        result=self._request({'query':query,'alternatives':list(alternatives)})
        hits,meta=result['hits'],result['meta']
        names=sorted({r['name'] for r in self.records.values()})
        meta['suggestions']=difflib.get_close_matches(query,names,n=5,cutoff=.65) if query and not hits else []
        return hits,meta

def relevance_order(row):
    match=row['relevance']
    return ({'id':0,'name':1,'alias':2}.get(match['exactMatch'],3),-match['score'],row['name'].casefold(),row['id'])

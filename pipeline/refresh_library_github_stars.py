"""Refresh deduplicated canonical Library GitHub counters without overwriting other signals."""
import concurrent.futures
from datetime import datetime, timezone
import json, os, subprocess, urllib.request, urllib.error
from pathlib import Path
try:
    from .generate_trends_comparison import repo_key
except ImportError:
    from generate_trends_comparison import repo_key
ROOT=Path(__file__).resolve().parents[1]

def token_value():
    token=os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:return token
    try:
        r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,timeout=10,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
        return dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line).get('password') if r.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired):return None

def scope_for(row):
    explicit=(row.get('repositoryScopeReview') or {}).get('scope')
    idx=row.get('githubIndex') or {}
    key=repo_key((row.get('links') or {}).get('code'))
    associated=next((r.get('scope') for r in idx.get('repositories',[]) if repo_key(r['url'])==key),None)
    scope=explicit or idx.get('selectedScope') or associated or (row.get('attention') or {}).get('githubScope')
    return 'benchmark_repo' if scope=='benchmark_repo' else 'hosting_repo'

def main():
    now=datetime.now(timezone.utc).isoformat();token=token_value()
    rows=json.loads((ROOT/'data/library_index.json').read_text())['records']
    keys={repo_key((r.get('links') or {}).get('code')) for r in rows}-{''}
    cache=ROOT/'data/repository_audit/counters';cache.mkdir(parents=True,exist_ok=True)
    def fetch(key):
        file=cache/(key.replace('/','__')+'.json')
        if file.exists():
            old=json.loads(file.read_text())
            if old.get('observedAt','')[:10]==now[:10] and old.get('status')=='ok':return key,old
        url='https://api.github.com/repos/'+key;headers={'User-Agent':'BenchmarkRadar','Accept':'application/vnd.github+json'}
        if token:headers['Authorization']='Bearer '+token
        result={'url':url,'observedAt':now}
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=25) as response:d=json.load(response)
            stars=d.get('stargazers_count')
            if not isinstance(stars,int) or stars<0:raise ValueError('Missing star count')
            result.update(status='ok',stars=stars,canonicalUrl=d['html_url'])
        except urllib.error.HTTPError as e:result['status']='http-'+str(e.code)
        except Exception as e:result['status']=type(e).__name__
        file.write_text(json.dumps(result));return key,result
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:observations=dict(pool.map(fetch,sorted(keys)))
    (ROOT/'data/github_repository_availability.json').write_text(json.dumps({k:{'status':v['status'],'observedAt':v['observedAt'],'sourceUrl':v['url']} for k,v in observations.items()},indent=2)+'\n')
    alias_path=ROOT/'data/github_repository_aliases.json'
    aliases=json.loads(alias_path.read_text()) if alias_path.exists() else {}
    for key,obs in observations.items():
        if obs['status']=='ok':
            canonical=obs['canonicalUrl'].removeprefix('https://github.com/').strip('/').lower()
            if key!=canonical:aliases[key]=canonical
    alias_path.write_text(json.dumps(aliases,indent=2)+'\n')
    out=ROOT/'data/library_metrics.json';payload=json.loads(out.read_text()) if out.exists() else {'records':[]}
    metrics={r['benchmarkId']:r for r in payload['records']}
    for r in rows:
        key=repo_key((r.get('links') or {}).get('code'))
        if not key:continue
        obs=observations[key];raw=metrics.setdefault(r['id'],{'benchmarkId':r['id']})
        raw.update(githubRepo='https://github.com/'+key,githubScope=scope_for(r))
        statuses=raw.setdefault('signalStatus',{})
        if obs['status']=='ok':
            raw.update(githubStars=obs['stars'],githubSource='github-rest',githubObservedAt=now)
            statuses['githubStars']={'state':'fresh','observedAt':now,'sourceUrl':obs['url']}
        else:
            statuses['githubStars']={'state':'stale' if raw.get('githubStars') is not None else 'unavailable','attemptedAt':now,'reason':obs['status'],'sourceUrl':obs['url']}
    payload.update(date=now[:10],records=sorted(metrics.values(),key=lambda r:r['benchmarkId']))
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print('GitHub counters:',len(keys),'repositories;',sum(x['status']=='ok' for x in observations.values()),'fresh',flush=True)
if __name__=='__main__':main()

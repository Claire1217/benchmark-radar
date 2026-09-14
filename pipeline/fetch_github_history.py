"""Refresh source-linked benchmark repository star histories; resume same-day downloads."""
import json,pathlib,urllib.request,urllib.error,concurrent.futures,os,subprocess,threading,datetime
P=pathlib.Path(__file__).resolve().parents[1];D=P/'data';out=D/'repository_audit/history';out.mkdir(parents=True,exist_ok=True)
lib={r['id']:r for r in json.load(open(D/'library_index.json'))['records']};snap=json.load(open(sorted((D/'metrics').glob('*.json'))[-1]));repos={}
metric_map={r['benchmarkId']:r for r in snap['records']}
for record in lib.values():
 r=metric_map.get(record['id'],{})
 idx=record.get('githubIndex') or {}
 code=(record.get('links') or {}).get('code')
 url=code or r.get('githubRepo') or ''
 scope=idx.get('selectedScope') if idx.get('addedCodeLink') else r.get('githubScope')
 if not scope:
  assoc=next((a for a in idx.get('repositories',[]) if a['url'].lower().rstrip('/')==url.lower().rstrip('/')),None)
  scope=assoc.get('scope') if assoc else None
 if scope!='benchmark_repo':continue
 import re
 match=re.match(r'https://github.com/([^/]+)/([^/#?]+)',url,re.I)
 if not match:continue
 url=('https://github.com/'+match.group(1)+'/'+match.group(2).removesuffix('.git')).lower()
 tags=record.get('researchDirections') or []
 if tags:repos.setdefault(url,set()).update(tags)
token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
if not token:
 try:
  x=subprocess.run(['gh','auth','token'],capture_output=True,text=True,timeout=10);token=x.stdout.strip() if x.returncode==0 else None
 except Exception:pass
if not token:
 try:
  credential=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,timeout=10,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
  if credential.returncode==0:
   fields=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
   token=fields.get('password')
 except Exception:pass
stop=threading.Event()
def fetch(pair):
 url,tags=pair;slug=url.replace('https://github.com/','');file=out/(slug.replace('/','__')+'.json')
 if file.exists():
  cached=json.load(open(file))
  if cached.get('status')=='complete' and cached.get('retrievedAt','')[:10]==datetime.datetime.now(datetime.timezone.utc).date().isoformat():
   cached['directions']=sorted(tags)
   return cached
 result={'url':url,'directions':sorted(tags),'weeks':[],'status':'pending','retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  for page in range(1,101):
   if stop.is_set():result['status']='rate-limit-not-attempted';break
   endpoint=f'https://api.github.com/repos/{slug}/stargazers/history?per_page=30&page={page}';headers={'Accept':'application/vnd.github+json','User-Agent':'BenchmarkRadar','X-GitHub-Api-Version':'2026-03-10'}
   if token:headers['Authorization']='Bearer '+token
   with urllib.request.urlopen(urllib.request.Request(endpoint,headers=headers),timeout=30) as r:
    rows=json.load(r);link=r.headers.get('Link','')
   if not isinstance(rows,list):raise ValueError('Unexpected history response')
   for row in rows:
    assert len(row['days'])==7 and sum(row['days'])==row['total']
   result['weeks'].extend(rows)
   if len(rows)<30 or not 'rel="next"' in link:
    result['status']='complete';break
  else:result['status']='pagination-limit'
 except urllib.error.HTTPError as e:
  result['status']='http-'+str(e.code)
  if e.code in [403,429] and (e.headers.get('X-RateLimit-Remaining')=='0' or e.code==429):stop.set()
 except Exception as e:result['status']=type(e).__name__
 file.write_text(json.dumps(result));return result
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for item in pool.map(fetch,sorted(repos.items())):
  results.append(item)
  if len(results)%25==0:print('Retrieved',len(results),'/',len(repos),flush=True)
receipt={'repositories':len(repos),'complete':sum(r['status']=='complete' for r in results),'statuses':{s:sum(r['status']==s for r in results) for s in set(r['status'] for r in results)}}
(D/'github_star_history.json').write_text(json.dumps({'records':results,'receipt':receipt},separators=(',',':'))+'\n');print(receipt,flush=True)

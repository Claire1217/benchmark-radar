"""Evidence-preserving batch discovery from public, record-linked sources."""
import pathlib,json,re,html,urllib.request,urllib.error,urllib.parse,ipaddress,socket,concurrent.futures,hashlib,datetime,threading,os,argparse
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'data/repository_audit';P.mkdir(parents=True,exist_ok=True);CACHE=P/'cache';CACHE.mkdir(exist_ok=True)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ids-file', help='JSON list of records or IDs to refresh; other index rows are retained')
args=parser.parse_args()
records=json.load(open(ROOT/'data/library_index.json'))['records']
selected_ids=None
if args.ids_file:
 selected_ids={x['id'] if isinstance(x,dict) else x for x in json.load(open(args.ids_file))}
 records=[r for r in records if r['id'] in selected_ids]
metric_files=sorted((ROOT/'data/metrics').glob('*.json'))
metrics={r['benchmarkId']:r for r in json.load(open(metric_files[-1]))['records']} if metric_files else {}
lock=threading.Lock();blocked=set();counts={}
UA='BenchmarkRadar/1.0 public benchmark repository indexing'
for f in CACHE.glob('*.json'):
 try:
  cached=json.load(open(f))
  if cached.get('status') in ['http-403','http-429']:blocked.add(urllib.parse.urlparse(cached['url']).hostname)
 except Exception:pass
def valid(u):
 try:
  x=urllib.parse.urlparse(u)
  if x.scheme not in ['http','https'] or not x.hostname or x.username or x.password:return False
  if x.hostname in ['localhost'] or x.hostname.endswith('.local'):return False
  try:return ipaddress.ip_address(x.hostname).is_global
  except ValueError:return True
 except Exception:return False
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  if not valid(newurl):raise ValueError('non-public redirect')
  return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(u):
 if not valid(u):return {'status':'invalid-url','body':''}
 key=hashlib.sha256(u.encode()).hexdigest();file=CACHE/(key+'.json')
 if file.exists():
  try:return json.load(open(file))
  except (json.JSONDecodeError,OSError):pass
 host=urllib.parse.urlparse(u).hostname
 if host in blocked:return {'status':'host-access-blocked','body':''}
 result={'url':u,'status':'error','body':''}
 try:
  # Refuse addresses resolving to local/private networks.
  if any(not ipaddress.ip_address(a[4][0]).is_global for a in socket.getaddrinfo(host,None)):raise ValueError('non-public address')
  with urllib.request.build_opener(SafeRedirect()).open(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=14) as resp:
   ctype=resp.headers.get('Content-Type','');data=resp.read(2_000_001)
   if len(data)>2_000_000:result['status']='too-large'
   elif any(t in ctype for t in ['html','json','text','xml']):result.update(status='ok',body=data.decode('utf-8','replace'),finalUrl=resp.url)
   else:result['status']='non-text'
 except urllib.error.HTTPError as e:
  result['status']='http-'+str(e.code)
  if e.code in (403,429):
   with lock:blocked.add(host)
 except Exception as e:result['status']=type(e).__name__
 temp=file.with_suffix('.'+str(threading.get_ident())+'.tmp');temp.write_text(json.dumps(result));os.replace(temp,file);return result
def repo(u):
 u=html.unescape(u).replace('\\/','/').rstrip('.,;:)')
 m=re.search(r'https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)',u,re.I)
 if not m or m.group(1).lower() in ['features','topics','collections','settings','login','orgs','sponsors','marketplace','about','site','pricing']:return None
 return 'https://github.com/'+m.group(1)+'/'+m.group(2).removesuffix('.git')
def norm(s):return re.sub('[^a-z0-9]','',s.lower())
def matches(name,url):
 n=norm(name);canonical=repo(url);slug=norm((canonical or url).split('/')[-1]);return len(slug)>=5 and len(n)>=5 and (n in slug or slug in n)
def one(r):
 cand={};checks=[]
 def add(u,source,basis,verified=False):
  canonical=repo(u)
  if not canonical:return
  k=canonical.lower();item=cand.setdefault(k,{'url':canonical,'evidence':[],'verified':False,'scope':'unresolved'})
  item['evidence'].append({'url':source,'basis':basis,'linkedUrl':u});item['verified']|=verified
  if verified:item['scope']='benchmark_repo' if matches(r['name'],canonical) else ('hosting_repo' if re.search(r'github.com/[^/]+/[^/]+/(tree|blob)/',u) else 'project_repo')
 links=r.get('links') or {};code=links.get('code');m=metrics.get(r['id'],{})
 if code:add(code,code,'existing-code-link',True)
 if m.get('githubRepo'):add(m['githubRepo'],m.get('hfPaperUrl') or links.get('report') or m['githubRepo'],'existing-metric-association',bool(code))
 urls=[]
 for key in ['project','report','data']:
  u=links.get(key)
  if not u or not valid(u):continue
  if repo(u):add(u,u,'record-resource-link',matches(r['name'],u));continue
  # Report pages can contain many benchmarks: candidates need identity matching.
  if not u.lower().endswith('.pdf'):urls.append((u,key))
 # Reviewed release evidence may point to the original paper absent from old catalog links.
 evidence_urls=[(r.get('releaseEvidence') or {}).get('sourceUrl'),*(r.get('taskReview') or {}).get('sources',[])]
 for u in evidence_urls:
  if not u or not valid(u):continue
  if repo(u):add(u,u,'reviewed-source-link',matches(r['name'],u))
  elif not u.lower().endswith('.pdf'):urls.append((u,'reviewed-source'))
 for u in [links.get('report'),*evidence_urls]:
  match=re.search(r'arxiv.org/(?:abs|pdf)/(\d{4}\.\d{4,5})',u or '')
  if match:urls.append(('https://huggingface.co/api/papers/'+match.group(1),'paper-association'))
 arxiv=re.search(r'arxiv.org/(?:abs|pdf)/(\d{4}\.\d{4,5})',links.get('report') or '')
 if arxiv:urls.insert(0,('https://huggingface.co/api/papers/'+arxiv.group(1),'paper-association'))
 for u,role in dict.fromkeys(urls):
  result=fetch(u);checks.append({'url':u,'status':result['status']})
  if result['status']!='ok':continue
  body=html.unescape(result['body']).replace('\\/','/')
  if role=='paper-association':
   try:
    obj=json.loads(body);g=obj.get('githubRepo');
    if g:add(g,u,'huggingface-paper-association',matches(r['name'],g))
   except Exception:pass
  for url in set(re.findall(r'https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+',body)):
   if role=='paper-association':continue
   add(url,u,'linked-from-'+role,matches(r['name'],url) and (role in ['project','data','reviewed-source'] or bool(arxiv) or (role=='report' and matches(r['name'],repo(url)) and norm(repo(url).split('/')[-1]) in norm(urllib.parse.urlparse(u).path))))
  if u.startswith('https://hub.harborframework.com/datasets/'):
   for target,label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',body,re.S):
    canonical=repo(target)
    if canonical and norm(canonical.split('/')[-1])==norm(r['name']) and re.search(r'tasks|github|code',re.sub('<[^>]+>',' ',label),re.I):
     add(target,u,'dataset-page-explicit-task-link',True)
 candidates=sorted(cand.values(),key=lambda c:(not c['verified'],c['url'].lower()))
 return {'id':r['id'],'name':r['name'],'researchDirections':r.get('researchDirections',[]),'status':'linked' if any(c['verified'] for c in candidates) else 'candidates' if candidates else 'not-found','candidates':candidates,'checks':checks}
def safe_one(r):
 try:return one(r)
 except Exception as e:return {'id':r['id'],'name':r['name'],'status':'error','candidates':[],'checks':[{'status':type(e).__name__}]}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for result in pool.map(safe_one,records):
  results.append(result)
  if len(results)%100==0:print('Indexed',len(results),'/',len(records),flush=True);(P/'progress.json').write_text(json.dumps({'completed':len(results),'total':len(records)}))
if selected_ids is not None and (ROOT/'data/github_repository_index.json').exists():
 old=json.load(open(ROOT/'data/github_repository_index.json'))['records']
 results=[r for r in old if r['id'] not in selected_ids]+results
status={s:sum(r['status']==s for r in results) for s in set(r['status'] for r in results)};payload={'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'recordCount':len(records),'statusCounts':status,'blockedHosts':sorted(blocked),'records':results};(ROOT/'data/github_repository_index.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2));print(status,'blocked hosts',sorted(blocked),flush=True)

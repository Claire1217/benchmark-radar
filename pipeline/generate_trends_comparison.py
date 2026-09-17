"""Build a comparable release and GitHub-history payload for the Trends page."""
from pathlib import Path
import json
from datetime import datetime,timezone,timedelta,date
ROOT=Path(__file__).resolve().parents[1]
ALIASES=json.loads((ROOT/'data/github_repository_aliases.json').read_text()) if (ROOT/'data/github_repository_aliases.json').exists() else {}
def repo_key(url):
 from urllib.parse import urlparse
 path=urlparse(url or "").path.strip("/").removesuffix(".git").lower()
 key="/".join(path.split("/")[:2]) if urlparse(url or "").hostname in {"github.com", "www.github.com"} else ""
 seen=set()
 while key in ALIASES and key not in seen:
  seen.add(key);key=ALIASES[key]
 return key

def current_repo_directions(records):
 result={}
 for r in records:
  if r.get("displayEligible") is False or r.get("evaluationMode")=="viewpoint_probe":continue
  url=(r.get("links") or {}).get("code")
  key=repo_key(url)
  # Main tool repository stars cannot be isolated to the benchmark it hosts.
  if not key or key in {"aider-ai/aider","allenai/olmocr"} or (r.get("attention") or {}).get("githubScope")=="hosting_repo":continue
  result.setdefault(key,set()).update(r.get("researchTopics",r.get("researchDirections",[])))
 return result

def main():
 library=json.loads((ROOT/'data/library_index.json').read_text());recent=json.loads((ROOT/'data/benchmarks_index.json').read_text());history=json.loads((ROOT/'data/github_star_history.json').read_text());lookup={r['id']:r for r in library['records']};families={}
 for r in sorted(recent['records'],key=lambda r:r.get('releasedAt','')):
  if r.get('displayEligible') is False or not r.get('releasedAt'):continue
  key=r.get('familyId') or r['id'];tags=lookup.get(r['id'],r).get('researchTopics',lookup.get(r['id'],r).get('researchDirections',[]))
  if key not in families:families[key]={'date':r['releasedAt'],'directions':set(tags)}
  else:families[key]['directions'].update(tags)
 releases=[{'date':v['date'],'directions':sorted(v['directions'])} for v in families.values()]
 mapping=current_repo_directions(library['records'])
 repos=[{'url':r['url'],'directions':sorted(mapping[repo_key(r['url'])]),'weeks':[{'date':datetime.fromtimestamp(w['week'],timezone.utc).date().isoformat(),'count':w['total']} for w in r['weeks']]} for r in history['records'] if r['status']=='complete' and mapping.get(repo_key(r['url']))]
 repos=list({repo_key(r['url']):r for r in repos}.values())
 # End is exclusive and falls on Sunday, dropping the unfinished current week.
 asof=date.fromisoformat(recent['manifest'].get('latestSourceDate') or max(r['date'] for r in releases));end=asof-timedelta(days=(asof.weekday()+1)%7)
 data={'directions':library['manifest'].get('topicTaxonomy',library['manifest']['researchTaxonomy'])['directions'],'releases':releases,'repos':repos,'releaseStart':min(r['date'] for r in releases),'historyStart':min(w['date'] for r in repos for w in r['weeks']),'end':end.isoformat(),'requestedRepos':history['receipt']['repositories']}
 (ROOT/'data/trends_comparison.json').write_text(json.dumps(data,separators=(',',':'))+'\n');(ROOT/'data/github_history_coverage.json').write_text(json.dumps(history['receipt'],indent=2)+'\n');print('trend_histories',len(repos),'release_families',len(releases),'end',end)
if __name__=='__main__':main()

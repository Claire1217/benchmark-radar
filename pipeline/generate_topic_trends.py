"""Build topic-first Trends from canonical Library membership and recorded events."""
import calendar,json
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
from generate_trends_comparison import repo_key,current_repo_directions
ROOT=Path(__file__).resolve().parents[1]
def shift(d,months):
 n=d.year*12+d.month-1+months;y,m=divmod(n,12);return date(y,m+1,min(d.day,calendar.monthrange(y,m+1)[1]))
def visible(r):return r.get('displayEligible') is not False and r.get('evaluationMode')!='viewpoint_probe'
def build(library,recent,history):
 records=[r for r in library['records'] if visible(r)];byid={r['id']:r for r in records};mapping=current_repo_directions(records)
 asof=date.fromisoformat(recent['manifest'].get('latestSourceDate') or recent['manifest']['dataAsOf']);end=asof-timedelta(days=(asof.weekday()+1)%7)
 # Drop the current partial API week. Repository history uses source calendar boundaries.
 earliest=min(r['releasedAt'] for r in recent['records'] if visible(r) and r.get('releasedAt') and r['releasedAt']!='0001-01-01');family={}
 for r in records:
  d=r.get('releasedAt');f=r.get('familyId') or r['id']
  if not d or d=='0001-01-01' or r.get('releaseDatePrecision') in ('year','unknown'):continue
  if f not in family:family[f]={'date':d,'members':[],'topics':set()}
  family[f]['date']=min(family[f]['date'],d);family[f]['members'].append(r);family[f]['topics'].update(r.get('researchTopics',[]))
 # Historical Library records identify existing families; only recent-index families form the monitored release cohort.
 recentfamilies={byid[r['id']].get('familyId') or r['id'] for r in recent['records'] if r['id'] in byid}
 releases=[{'id':f,'date':v['date'],'directions':sorted(v['topics']),'name':v['members'][0]['name'],'description':v['members'][0].get('description',''),'url':(v['members'][0].get('links') or {}).get('report')} for f,v in family.items() if f in recentfamilies and earliest<=v['date']<end.isoformat()]
 names={};repoentries={}
 for r in records:
  k=repo_key((r.get('links') or {}).get('code'));names.setdefault(k,set()).add(r['name']);repoentries.setdefault(k,[]).append(r)
 repos=[]
 for h in history['records']:
  k=repo_key(h['url'])
  if h['status']!='complete' or not mapping.get(k):continue
  weeks=sorted(h['weeks'],key=lambda w:w['week']);dates=[w['week'] for w in weeks]
  if not weeks or len(set(dates))!=len(dates) or any(b-a!=604800 for a,b in zip(dates,dates[1:])):continue
  if datetime.fromtimestamp(dates[-1],timezone.utc).date()+timedelta(days=7)<end:continue
  days=[(datetime.fromtimestamp(w['week'],timezone.utc).date()+timedelta(days=i),n) for w in weeks for i,n in enumerate(w['days'])]
  repos.append({'url':h['url'],'name':k,'names':sorted(names.get(k,[])),'directions':sorted(mapping[k]),'days':days,'firstDay':days[0][0]})
 topics=[]
 for t in library['manifest']['topicTaxonomy']['directions']:
  members=[r for r in records if t['id'] in r.get('researchTopics',[])];rr=[r for r in repos if t['id'] in r['directions']];ff=[f for f in releases if t['id'] in f['directions']];windows={}
  for months in (1,3,6):
   start=shift(end,-months);prev=shift(start,-months);full=start.isoformat()>=earliest;prevfull=prev.isoformat()>=earliest
   current=[f for f in ff if start.isoformat()<=f['date']<end.isoformat()];prior=[f for f in ff if prev.isoformat()<=f['date']<start.isoformat()]
   stars=[]
   for r in rr:
    n=sum(n for d,n in r['days'] if start<=d<end);baseline=sum(n for d,n in r['days'] if d<start);priorstars=sum(n for d,n in r['days'] if prev<=d<start)
    weekly=[sum(n for d,n in r['days'] if end-timedelta(days=(13-i)*7)<=d<end-timedelta(days=(12-i)*7)) for i in range(13)]
    stars.append({k:r[k] for k in ('url','name','names')}|{'stars':n,'baseline':baseline,'previous':priorstars,'weekly':weekly,'newRepository':r['firstDay']>=start})
   stars.sort(key=lambda r:(-r['stars'],r['name']));total=sum(r['stars'] for r in stars);base=sum(r['baseline'] for r in stars);top=stars[0]['stars'] if stars else 0
   bins=[]
   for i in range(8):
    a=end-timedelta(days=(8-i)*14);b=a+timedelta(days=14);bins.append(sum(a.isoformat()<=f['date']<b.isoformat() for f in ff) if a.isoformat()>=earliest else None)
   windows[str(months)]={'start':start.isoformat(),'previousStart':prev.isoformat(),'count':len(current) if full else None,'observedCount':len(current),'previous':len(prior) if prevfull else None,'delta':len(current)-len(prior) if full and prevfull else None,'bars':bins,'releases':sorted(current,key=lambda x:x['date'],reverse=True),'repos':stars,'stars':total if stars else None,'baseline':base if stars else None,'growthRate':100*total/base if base else None,'active':sum(r['stars']>0 for r in stars),'share':top/total if total else None,'otherStars':total-top,'newRepoStars':sum(r['stars'] for r in stars if r['newRepository'])}
  used=[]
  for r in members:
   refs=[x for x in r.get('modelReportReferences',[]) if x.get('provider') and (x.get('url') or x.get('sourceUrl'))]
   if refs:used.append({'id':r['id'],'name':r['name'],'reports':refs})
  topics.append({'id':t['id'],'name':t['name'],'description':t['description'],'library':len(members),'windows':windows,'trackedUse':used,'linkedRepos':len({repo_key((r.get('links') or {}).get('code')) for r in members if repo_key((r.get('links') or {}).get('code'))})})
 return {'taxonomyVersion':library['manifest']['topicTaxonomy']['version'],'asOf':(end-timedelta(days=1)).isoformat(),'endExclusive':end.isoformat(),'releaseCoverageStart':earliest,'defaultReleaseMonths':1,'defaultStarMonths':3,'topics':topics,'coverage':{'completeHistories':len(repos),'requestedHistories':history['receipt']['repositories']},'methodology':{'stars':'Recorded star creation events, not net stars or current stargazer totals. Growth rate = period events / all recorded events before the period.','time':'Calendar-month windows end at the last complete source week. Source day boundaries may differ from UTC.','release':'Monitored recent-index families, first dated across the canonical Library; unknown/year-only dates excluded. Incomplete windows return null, not zero.','scope':'Deduplicated repositories within each topic. Topics overlap. Shared hosting/toolkit repositories excluded. New-repository share is a lower-bound estimate using complete creation weeks; it is not benchmark release age.','classification':'Same current topic mapping applied retrospectively to every window.'}}
def main():
 load=lambda n:json.loads((ROOT/'data'/n).read_text())
 result=build(load('library_index.json'),load('benchmarks_index.json'),load('github_star_history.json'));(ROOT/'data/trends_topics.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n');print('Topic Trends:',len(result['topics']),result['coverage'])
if __name__=='__main__':main()

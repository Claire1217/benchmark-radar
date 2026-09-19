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
 records=[r for r in library['records'] if visible(r)]
 taxonomy=library['manifest'].get('libraryTaxonomy',library['manifest']['topicTaxonomy'])
 membership=lambda r:r.get('libraryCategories',r.get('researchTopics',[]))
 mapping=current_repo_directions([{**r,'researchTopics':membership(r)} for r in records])
 asof=date.fromisoformat(recent['manifest'].get('latestSourceDate') or recent['manifest']['dataAsOf']);end=asof-timedelta(days=(asof.weekday()+1)%7)
 release_end=date.fromisoformat(recent['manifest'].get('dataAsOf') or asof.isoformat())+timedelta(days=1)
 # Stars require complete weeks; releases include the latest indexed day.
 family={}
 for r in records:
  # An index/leaderboard launch is useful metadata, not a dataset release.
  if r.get('evaluationRole')=='aggregate-index':continue
  d=r.get('releasedAt');f=r.get('familyId') or r['id']
  if f not in family:family[f]={'date':None,'members':[],'topics':set()}
  family[f]['members'].append(r);family[f]['topics'].update(membership(r))
  if d and d!='0001-01-01' and r.get('releaseDatePrecision') not in ('year','month','unknown') and (r.get('releaseEvidence') or {}).get('dateScope') not in ('underlying-dataset','public-disclosure'):
   family[f]['date']=min(family[f]['date'] or d,d)
 # Count every dated Library family, including entries absent from the recent feed.
 # These are known releases in the catalog, not a claim of exhaustive discovery.
 releases=[]
 for f,v in family.items():
  if not v['date'] or v['date']>=release_end.isoformat():continue
  r=next(r for r in v['members'] if r.get('releasedAt')==v['date'] and r.get('releaseDatePrecision') not in ('year','month','unknown'))
  evidence=r.get('releaseEvidence') or {}
  releases.append({'id':f,'date':v['date'],'directions':sorted(v['topics']),'name':r['name'],'description':r.get('description',''),'url':evidence.get('sourceUrl') or (r.get('links') or {}).get('report'),'dateBasis':evidence.get('basis','released')})
 earliest=min((f['date'] for f in releases),default=None)
 names={};repoentries={}
 for r in records:
  k=repo_key((r.get('links') or {}).get('code'));names.setdefault(k,set()).add(r['name']);repoentries.setdefault(k,[]).append(r)
 repos=[];seen_repos=set()
 for h in history['records']:
  k=repo_key(h['url'])
  if h['status']!='complete' or not mapping.get(k) or k in seen_repos:continue
  weeks=sorted(h['weeks'],key=lambda w:w['week']);dates=[w['week'] for w in weeks]
  if not weeks or len(set(dates))!=len(dates) or any(b-a!=604800 for a,b in zip(dates,dates[1:])):continue
  if datetime.fromtimestamp(dates[-1],timezone.utc).date()+timedelta(days=7)<end:continue
  seen_repos.add(k)
  days=[(datetime.fromtimestamp(w['week'],timezone.utc).date()+timedelta(days=i),n) for w in weeks for i,n in enumerate(w['days'])]
  repos.append({'url':h['url'],'name':k,'names':sorted(names.get(k,[])),'directions':sorted(mapping[k]),'days':days,'firstDay':days[0][0]})
 systematic_dates=[r.get('releasedAt') for r in recent.get('records',[]) if r.get('releasedAt') and r.get('releasedAt')!='0001-01-01']
 coverage_start=min(systematic_dates,default=None)
 topics=[]
 for t in taxonomy['directions']:
  members=[r for r in records if t['id'] in membership(r)];rr=[r for r in repos if t['id'] in r['directions']];ff=[f for f in releases if t['id'] in f['directions']];windows={}
  for months in (1,3,6,12):
   start=shift(end,-months);prev=shift(start,-months)
   release_start=shift(release_end,-months);release_prev=shift(release_start,-months)
   current=[f for f in ff if release_start.isoformat()<=f['date']<release_end.isoformat()];prior=[f for f in ff if release_prev.isoformat()<=f['date']<release_start.isoformat()]
   stars=[]
   for r in rr:
    n=sum(n for d,n in r['days'] if start<=d<end);baseline=sum(n for d,n in r['days'] if d<start);priorstars=sum(n for d,n in r['days'] if prev<=d<start)
    weekly=[sum(n for d,n in r['days'] if end-timedelta(days=(13-i)*7)<=d<end-timedelta(days=(12-i)*7)) for i in range(13)]
    week_count=52 if months==12 else 26
    longweeks=[sum(n for d,n in r['days'] if end-timedelta(days=(week_count+3-i)*7)<=d<end-timedelta(days=(week_count+2-i)*7)) for i in range(week_count+3)]
    stars.append({k:r[k] for k in ('url','name','names')}|{'stars':n,'baseline':baseline,'previous':priorstars,'weekly':weekly,'weekly26':longweeks[3:],'average26':[sum(longweeks[i:i+4])/4 for i in range(week_count)],'newRepository':r['firstDay']>=start})
   stars.sort(key=lambda r:(-r['stars'],r['name']));total=sum(r['stars'] for r in stars);base=sum(r['baseline'] for r in stars);top=stars[0]['stars'] if stars else 0
   # Calendar-month bins follow the selected period, including leap-year boundaries.
   bounds=[shift(release_end,-months+i) for i in range(months+1)]
   bins=[sum(a.isoformat()<=f['date']<b.isoformat() for f in ff) for a,b in zip(bounds,bounds[1:])]
   comparable=not coverage_start or release_prev.isoformat()>=coverage_start
   windows[str(months)]={'start':release_start.isoformat(),'previousStart':release_prev.isoformat(),'starStart':start.isoformat(),'starPreviousStart':prev.isoformat(),'count':len(current),'observedCount':len(current),'previous':len(prior),'delta':len(current)-len(prior),'comparisonBasis':'indexed-releases','comparisonComplete':comparable,'bars':bins,'barDates':[d.isoformat() for d in bounds],'releases':sorted(current,key=lambda x:x['date'],reverse=True),'repos':stars,'stars':total if stars else None,'baseline':base if stars else None,'growthRate':100*total/base if base else None,'active':sum(r['stars']>0 for r in stars),'share':top/total if total else None,'otherStars':total-top,'newRepoStars':sum(r['stars'] for r in stars if r['newRepository'])}
  used=[]
  for r in members:
   refs=[x for x in r.get('modelReportReferences',[]) if x.get('provider') and (x.get('url') or x.get('sourceUrl'))]
   if refs:used.append({'id':r['id'],'name':r['name'],'reports':refs})
  topics.append({'id':t['id'],'name':t['name'],'description':t['description'],'library':len(members),'windows':windows,'trackedUse':used,'linkedRepos':len({repo_key((r.get('links') or {}).get('code')) for r in members if repo_key((r.get('links') or {}).get('code'))})})
 scoped_out=sum(
  not v['date'] and any(
   r.get('releasedAt') and r.get('releasedAt')!='0001-01-01'
   and r.get('releaseDatePrecision') not in ('year','month','unknown')
   and (r.get('releaseEvidence') or {}).get('dateScope') in ('underlying-dataset','public-disclosure')
   for r in v['members']
  ) for v in family.values()
 )
 missing_exact=sum(not v['date'] for v in family.values())-scoped_out
 return {
  'taxonomyVersion':taxonomy['version'],
  'asOf':(release_end-timedelta(days=1)).isoformat(),'endExclusive':release_end.isoformat(),'starAsOf':(end-timedelta(days=1)).isoformat(),'starEndExclusive':end.isoformat(),
  'earliestKnownRelease':earliest,'systematicReleaseCoverageStart':coverage_start,
  'releaseTotals':{str(m):sum(shift(release_end,-m).isoformat()<=f['date']<release_end.isoformat() for f in releases) for m in (1,3,6,12)},
  'defaultReleaseMonths':3,'defaultStarMonths':3,'topics':topics,
  'coverage':{
   'libraryRecords':len(records),'storedLibraryRecords':len(library['records']),'displayEligibleRecords':len(records),
   'datedFamilies':len(releases),'undatedFamilies':missing_exact+scoped_out,
   'familiesMissingExactDate':missing_exact,'familiesExcludedAsVariantsOrDisclosures':scoped_out,
   'releaseScope':'all-library-dated-families','completeHistories':len(repos),'includedHistories':len(repos),'fetchedCompleteHistories':sum(h['status']=='complete' for h in history['records']),'requestedHistories':history['receipt']['repositories']
  },
  'methodology':{
   'stars':'Recorded star creation events, not net stars or current stargazer totals. Growth rate = period events / all recorded events before the period.',
   'time':'Release windows include the latest indexed day; star windows end at the last complete source week. Source day boundaries may differ from UTC.',
   'release':'All dated canonical Library families, counted at their earliest supported day-level publication date. Unknown/year-only dates excluded. Counts describe indexed releases, not exhaustive historical coverage; backfills can change past counts.',
   'scope':'Deduplicated repositories within each topic. Topics overlap. Shared hosting/toolkit repositories excluded. New-repository share is a lower-bound estimate using complete creation weeks; it is not benchmark release age.',
   'classification':'Same current topic mapping applied retrospectively to every window.'
  }
 }
def main():
 load=lambda n:json.loads((ROOT/'data'/n).read_text())
 result=build(load('library_index.json'),load('benchmarks_index.json'),load('github_star_history.json'));(ROOT/'data/trends_topics.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n');print('Topic Trends:',len(result['topics']),result['coverage'])
if __name__=='__main__':main()

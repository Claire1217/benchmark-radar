import unittest,json,sys,copy
from pathlib import Path
from datetime import date,datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'pipeline'))
from generate_topic_trends import shift,build
from research_topics import annotate_topics
class TopicTrendsTests(unittest.TestCase):
 def test_calendar_months(self):
  self.assertEqual(shift(date(2026,3,31),-1),date(2026,2,28));self.assertEqual(shift(date(2024,3,31),-1),date(2024,2,29))
 def test_target_boundaries_and_word_forms(self):
  rows=[{'description':'Evaluates self-improving agents through retained experience.'},{'description':'Benchmarks video world models predicting future physical states.'},{'description':'Evaluates healthcare tasks in a terminal environment.'}];annotate_topics(rows)
  self.assertIn('self-improving-agents',rows[0]['researchTopics']);self.assertIn('world-models',rows[1]['researchTopics']);self.assertNotIn('coding-agents',rows[2]['researchTopics'])
 def test_zero_missing_and_baseline(self):
  def record(id):return {'id':id,'familyId':id,'name':id,'releasedAt':'2026-05-21','researchTopics':['coding-agents'],'links':{'code':'https://github.com/test/repo'}}
  rows=[record('a'),record('b')];library={'records':rows,'manifest':{'topicTaxonomy':{'version':'test','directions':[{'id':'coding-agents','name':'Coding Agents','description':''},{'id':'tool-use','name':'Tool Use','description':''}]}}};recent={'records':rows,'manifest':{'latestSourceDate':'2026-09-13'}}
  weeks=[]
  for i in range(35):
   d=date(2026,1,11)+timedelta(days=7*i);days=[1,0,0,0,0,0,0];weeks.append({'week':int(datetime.combine(d,datetime.min.time(),timezone.utc).timestamp()),'days':days,'total':1})
  hist={'receipt':{'repositories':1},'records':[{'url':'https://github.com/test/repo','status':'complete','weeks':weeks}]};j=build(library,recent,hist);w=j['topics'][0]['windows']['3'];self.assertEqual(len(w['repos']),1);self.assertIsNone(w['delta']);self.assertFalse(w['comparisonComplete']);self.assertAlmostEqual(w['growthRate'],100*w['stars']/w['baseline']);self.assertIsNone(j['topics'][1]['windows']['3']['stars']);self.assertEqual(j['topics'][0]['windows']['6']['count'],2)
 def test_real_data_membership_and_counts(self):
  l=json.loads((ROOT/'data/library_index.json').read_text());j=json.loads((ROOT/'data/trends_topics.json').read_text());self.assertEqual(l['manifest']['topicTaxonomy']['version'],j['taxonomyVersion']);self.assertEqual([t['id'] for t in j['topics']],[t['id'] for t in l['manifest']['topicTaxonomy']['directions']]);self.assertEqual([t['library'] for t in j['topics']],[t['count'] for t in l['manifest']['topicTaxonomy']['directions']])
  visible=sum(r.get('displayEligible') is not False and r.get('evaluationMode')!='viewpoint_probe' for r in l['records'])
  self.assertEqual(j['coverage']['storedLibraryRecords'],len(l['records']))
  self.assertEqual(j['coverage']['displayEligibleRecords'],visible)

 def test_all_library_year_and_missing_dates(self):
  def record(identity,release,**kw):
   return {'id':identity,'familyId':identity,'name':identity,'releasedAt':release,'researchTopics':['coding-agents'],'links':{},**kw}
  rows=[record('old','2025-10-01'),record('prior','2024-10-01'),record('recent','2026-06-01'),record('unknown','0001-01-01'),record('year','2026-01-01',releaseDatePrecision='year'),record('duplicate','2025-11-01',familyId='old'),record('undated-alias',None,familyId='old',researchTopics=['tool-use'])]
  rows += [record('month','2026-04-01',releaseDatePrecision='month'),record('score-slice','2026-04-01',releaseEvidence={'dateScope':'underlying-dataset'})]
  rows += [record('disclosure','2026-06-12',releaseEvidence={'dateScope':'public-disclosure'}),record('disclosure-alias','2023-01-01',familyId='old',releaseEvidence={'dateScope':'public-disclosure'})]
  rows += [record('index','2026-08-13',evaluationRole='aggregate-index'),record('old-index','2020-01-01',evaluationRole='aggregate-index'),record('index-alias','2024-01-01',familyId='old',evaluationRole='aggregate-index')]
  library={'records':rows,'manifest':{'topicTaxonomy':{'version':'test','directions':[{'id':'coding-agents','name':'Coding','description':''},{'id':'tool-use','name':'Tool use','description':''}]}}}
  recent={'records':[rows[2]],'manifest':{'latestSourceDate':'2026-09-13'}}
  j=build(library,recent,{'records':[],'receipt':{'repositories':0}})
  w=j['topics'][0]['windows']['12']
  self.assertEqual((w['count'],w['previous'],w['delta']),(2,None,None))
  self.assertEqual(len(w['bars']),12)
  self.assertEqual(sum(w['bars']),w['count'])
  self.assertEqual(w['barDates'][0],'2025-09-13')
  self.assertEqual(w['barDates'][-1],'2026-09-13')
  self.assertEqual(j['defaultReleaseMonths'],3)
  self.assertEqual(j['systematicReleaseCoverageStart'],'2026-06-01')
  self.assertEqual(j['coverage']['familiesMissingExactDate'],3)
  self.assertEqual(j['coverage']['familiesExcludedAsVariantsOrDisclosures'],2)
  self.assertIsNone(w['previous'])
  self.assertIsNone(w['delta'])
  self.assertEqual(j['topics'][1]['windows']['12']['count'],1)
  self.assertEqual(j['coverage']['undatedFamilies'],5)
  self.assertEqual(j['releaseTotals']['12'],2)
  self.assertEqual(j['earliestKnownRelease'],'2024-10-01')

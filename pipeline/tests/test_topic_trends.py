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
  hist={'receipt':{'repositories':1},'records':[{'url':'https://github.com/test/repo','status':'complete','weeks':weeks}]};j=build(library,recent,hist);w=j['topics'][0]['windows']['3'];self.assertEqual(len(w['repos']),1);self.assertIsNone(w['delta']);self.assertAlmostEqual(w['growthRate'],100*w['stars']/w['baseline']);self.assertIsNone(j['topics'][1]['windows']['3']['stars']);self.assertIsNone(j['topics'][0]['windows']['6']['count'])
 def test_real_data_membership_and_counts(self):
  l=json.loads((ROOT/'data/library_index.json').read_text());j=json.loads((ROOT/'data/trends_topics.json').read_text());self.assertEqual(l['manifest']['topicTaxonomy']['version'],j['taxonomyVersion']);self.assertEqual([t['id'] for t in j['topics']],[t['id'] for t in l['manifest']['topicTaxonomy']['directions']]);self.assertEqual([t['library'] for t in j['topics']],[t['count'] for t in l['manifest']['topicTaxonomy']['directions']])

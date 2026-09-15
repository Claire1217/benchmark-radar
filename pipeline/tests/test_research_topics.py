import unittest,json,copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pipeline'))
from research_topics import annotate_topics,TOPICS
from generate_trends_comparison import current_repo_directions
class ResearchTopicsTests(unittest.TestCase):
 def test_target_not_construction(self):
  rows=[{'description':'A self-evolving benchmark for evaluating software security vulnerabilities.'},{'description':'Video evaluation built by a multi-agent pipeline.'},{'description':'We evaluate language world models that simulate agentic environments.'}]
  annotate_topics(rows)
  for r,t in zip(rows,['self-improving-agents','multi-agent','world-models']):self.assertNotIn(t,r['researchTopics'])
 def test_missing_and_legacy_preservation(self):
  r={'description':'','topics':['Original label'],'researchDirections':['mathematical-reasoning']};annotate_topics([r]);self.assertEqual(r['researchTopics'],[]);self.assertEqual(r['benchmarkTaxonomy']['sourceLabels']['topics'],['Original label']);self.assertEqual(r['researchDirections'],['mathematical-reasoning'])
 def test_production_parity_evidence_and_idempotence(self):
  library=json.loads((ROOT/'data/library_index.json').read_text());rows={r['id']:r for r in library['records']};ids={t['id'] for t in TOPICS};self.assertEqual(len(ids),20)
  for r in rows.values():
   self.assertTrue(set(r['researchTopics'])<=ids);self.assertEqual(set(r['researchTopics']),set(r['researchTopicEvidence']))
  for r in json.loads((ROOT/'data/benchmarks_index.json').read_text())['records']:
   if r['id'] in rows:self.assertEqual(r['researchTopics'],rows[r['id']]['researchTopics'])
  sample=copy.deepcopy(list(rows.values())[::29]);before=copy.deepcopy(sample);annotate_topics(sample);self.assertEqual(sample,before)
 def test_hosting_repo_not_benchmark_attention(self):
  self.assertEqual(current_repo_directions([{'links':{'code':'https://github.com/allenai/olmocr'},'researchTopics':['ocr-documents']}]),{})

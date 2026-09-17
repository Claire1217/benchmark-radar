import unittest
from pipeline.repository_index import apply_repository_index,safe_github
class RepositoryIndexTests(unittest.TestCase):
 def entry(self,verified=True,url='https://github.com/acme/bench',scope='benchmark_repo'):
  return {'url':url,'verified':verified,'scope':scope,'evidence':[{'url':'https://arxiv.org/abs/2601.01234','linkedUrl':url,'basis':'linked-from-report'}]}
 def apply(self,r,c):
  apply_repository_index([r],{'records':[{'id':'x','status':'linked','candidates':c}]});return r
 def test_single_link(self):
  r=self.apply({'id':'x','links':{}},[self.entry()]);self.assertEqual(r['links']['code'],'https://github.com/acme/bench')
 def test_existing_deep_link(self):
  r=self.apply({'id':'x','links':{'code':'https://github.com/acme/mono/tree/main/bench'}},[self.entry()]);self.assertIn('/tree/',r['links']['code'])
 def test_candidate(self):
  r=self.apply({'id':'x','links':{}},[self.entry(False)]);self.assertNotIn('code',r['links'])
 def test_ambiguous(self):
  r=self.apply({'id':'x','links':{}},[self.entry(),self.entry(url='https://github.com/acme/other')]);self.assertNotIn('code',r['links'])
 def test_subdirectory(self):
  c=self.entry(scope='hosting_repo');c['evidence'][0]['linkedUrl']='https://github.com/acme/bench/tree/main/task';r=self.apply({'id':'x','links':{}},[c]);self.assertTrue(r['links']['code'].endswith('/task'))
 def test_url_validation(self):
  for u in ['javascript:alert(1)','https://github.com.evil.test/a/b','https://github.com/a/b" onmouseover="x','http://github.com/a/b']:self.assertFalse(safe_github(u))
 def test_missing(self):
  r={'id':'y','links':{}};self.apply(r,[self.entry()]);self.assertEqual(r,{'id':'y','links':{}})

class RepositoryAvailabilityTests(unittest.TestCase):
 def test_history_404_does_not_remove_source_verified_code(self):
  from pipeline.repository_index import load_and_apply
  import tempfile,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);url='https://github.com/acme/bench'
   p.joinpath('github_repository_index.json').write_text(json.dumps({'records':[{'id':'x','status':'linked','candidates':[{'url':url,'verified':True,'scope':'benchmark_repo'}]}]}))
   p.joinpath('github_star_history.json').write_text(json.dumps({'records':[{'url':url,'status':'http-404'}]}))
   rows=[{'id':'x','links':{}}];load_and_apply(rows,p)
   self.assertEqual(rows[0]['links']['code'],url)
 def test_review_selects_upstream_among_forks(self):
  from pipeline.repository_index import load_and_apply
  import tempfile,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);url='https://github.com/acme/bench'
   candidates=[{'url':u,'verified':True,'scope':'benchmark_repo'} for u in [url,'https://github.com/fork/bench']]
   p.joinpath('github_repository_index.json').write_text(json.dumps({'records':[{'id':'x','status':'linked','candidates':candidates}]}))
   p.joinpath('repository_link_reviews.json').write_text(json.dumps({'reviews':[{'id':'x','url':url,'scope':'benchmark_repo'}]}))
   rows=[{'id':'x','links':{}}];load_and_apply(rows,p)
   self.assertEqual(rows[0]['links']['code'],url)

 def test_metadata_404_prevents_new_dead_code_link(self):
  from pipeline.repository_index import load_and_apply
  import tempfile,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);url='https://github.com/acme/bench'
   p.joinpath('github_repository_index.json').write_text(json.dumps({'records':[{'id':'x','status':'linked','candidates':[{'url':url,'verified':True,'scope':'benchmark_repo'}]}]}))
   p.joinpath('github_repository_availability.json').write_text(json.dumps({'acme/bench':{'status':'http-404'}}))
   rows=[{'id':'x','links':{}}];load_and_apply(rows,p)
   self.assertNotIn('code',rows[0]['links'])

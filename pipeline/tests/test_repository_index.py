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

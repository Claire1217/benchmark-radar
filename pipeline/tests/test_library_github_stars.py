import unittest
from pipeline.refresh_library_github_stars import scope_for
class StarScopeTests(unittest.TestCase):
 def test_tool_scope_overrides_name_match(self):
  r={'links':{'code':'https://github.com/acme/tool'},'githubIndex':{'selectedScope':'benchmark_repo'},'repositoryScopeReview':{'scope':'hosting_repo'}}
  self.assertEqual(scope_for(r),'hosting_repo')
 def test_unverified_scope_is_not_benchmark(self):
  self.assertEqual(scope_for({'links':{'code':'https://github.com/acme/tool'}}),'hosting_repo')
 def test_confirmed_association(self):
  r={'links':{'code':'https://github.com/acme/bench'},'githubIndex':{'repositories':[{'url':'https://github.com/acme/bench','scope':'benchmark_repo'}]}}
  self.assertEqual(scope_for(r),'benchmark_repo')

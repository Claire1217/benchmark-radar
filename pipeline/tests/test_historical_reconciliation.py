import copy,json,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import reconcile_workflow as migration
import source_coverage as coverage
import index_benchmarks as index
from auto_admit_candidates import automatically_publishable
from generate_editorial_copy import selection_fingerprint

class HistoricalTests(unittest.TestCase):
 def fixture(self,root):
  values={'pipeline/config.json':{'arxiv':{'categories':['cs.AR']},'thresholds':{'review':.4,'publish':.85}},
   'data/library_index.json':{'records':[{'id':'hidden','name':'Chip tests','releasedAt':'2026-07-12','firstSeenAt':'2026-07-13','displayEligible':False,'source':{'type':'arxiv','id':'old'}}]},
   'data/benchmarks.json':{'records':[{'id':'hidden','name':'Chip tests','releasedAt':'2026-07-12','firstSeenAt':'2026-07-13','source':{'type':'arxiv','id':'old'}}]},
   'data/review_queue.json':{'candidates':[]},
   'data/workflow_audit_cases.json':{'discoveryCases':[{'id':'Known','sourceId':'new','sourceUrl':'https://arxiv.org/abs/new'}]}}
  for f,v in values.items():
   p=root/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v))
 def test_dry_run_is_read_only_and_apply_replay_preserves_identity(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.fixture(root);snapshot=lambda:{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   before=snapshot();plan=migration.run(root,'2026-07-24','2026-10-24');self.assertEqual(before,snapshot())
   record={'id':'new-id','name':'NewBench','releasedAt':'2026-08-01','source':{'type':'arxiv','id':'new','url':'https://arxiv.org/abs/new'},'reviewContext':{'abstract':'We introduce a benchmark for chip design.'}}
   fetch=lambda *args:copy.deepcopy(record)
   first=migration.run(root,'2026-07-24','2026-10-24',apply=True,max_cases=1,fetch=fetch)
   q=(root/'data/review_queue.json').read_bytes()
   with patch.object(migration,'fetch_case',side_effect=AssertionError('must reuse persisted queue')):
    second=migration.run(root,'2026-07-24','2026-10-24',apply=True,max_cases=1,fetch=lambda *a:(_ for _ in ()).throw(AssertionError('fetched twice')))
   self.assertEqual(q,(root/'data/review_queue.json').read_bytes());self.assertTrue(second['stablePublicFieldsUnchanged'])
   rows=json.loads(q)['candidates'];self.assertEqual(len(rows),2)
   hidden=next(r for r in rows if r['id']=='hidden');self.assertEqual(hidden['releasedAt'],'2026-07-12')
   self.assertFalse(automatically_publishable({**hidden,'recognitionConfidence':1,'relation':'introduces'},.85))
   original={k:v for k,v in hidden.items() if k!='reassessmentVersion'}
   self.assertNotEqual(selection_fingerprint(original),selection_fingerprint(hidden))
   self.assertEqual(first['cases']['Known']['outcome'],'queued')
 def test_source_failure_is_recoverable_and_never_completion(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.fixture(root)
   def fail(*args):raise TimeoutError('down')
   result=migration.run(root,'2026-07-24','2026-10-24',apply=True,max_cases=1,fetch=fail)
   self.assertEqual(result['cases']['Known']['outcome'],'unresolved');self.assertEqual(result['coverageWindows']['complete'],0)
 def test_first_release_path_uses_atom_and_does_not_fall_back_to_oai(self):
  with patch.object(index,'fetch_for_range_atom',return_value=['paper-with-later-metadata-update']) as atom,patch.object(index,'request_oai') as oai:
   self.assertEqual(index.fetch_for_range('2026-07-24','2026-07-31',{}),['paper-with-later-metadata-update'])
   atom.assert_called_once();oai.assert_not_called()
  with patch.object(index,'fetch_for_range_atom',side_effect=TimeoutError()),patch.object(index,'request_oai') as oai:
   with self.assertRaises(TimeoutError):index.fetch_for_range('2026-07-24','2026-07-31',{})
   oai.assert_not_called()
 def test_old_completion_is_invalidated_and_backlog_cannot_starve_today(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ledger.json';payload={'windows':{}}
   for day in ['2026-07-24','2026-07-25','2026-10-23','2026-10-24']:
    coverage.enqueue(payload,'arxiv','cs.AR',day,day)
   old=next(iter(payload['windows'].values()));old.update(contractVersion=1,status='complete')
   p.write_text(json.dumps(payload));loaded=coverage.load(p);self.assertEqual(next(iter(loaded['windows'].values()))['status'],'pending')
   work=coverage.scheduled(loaded,'2026-10-24T00:00:00Z','2026-10-17')
   self.assertEqual([w['from'] for _,w in work],['2026-10-23','2026-07-24','2026-10-24','2026-07-25'])

class OperationalAuditTests(unittest.TestCase):
 def test_legacy_and_failed_coverage_are_distinct(self):
  from audit_workflow import audit_operations
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'data').mkdir()
   payload={'windows':{'legacy':{'from':'2026-07-01','status':'complete','contractVersion':1},'failed':{'from':'2026-10-01','status':'failed','contractVersion':coverage.CONTRACT_VERSION}}}
   (root/'data/source_coverage.json').write_text(json.dumps(payload))
   result=audit_operations(root)['discovery']
   self.assertEqual(result['states'],{'failed':1,'legacy-unverified':1})
   self.assertEqual(result['oldestUnfinishedFrom'],'2026-07-01')

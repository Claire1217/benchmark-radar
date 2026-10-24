import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import discover_benchmarks as discovery
import index_benchmarks as index
from source_identity import source_key, merge_observation
import refresh_source_observations as refresh
from auto_admit_candidates import automatically_publishable
from sync_catalogs import merge_payloads, build_payload


class SourceIdentityTests(unittest.TestCase):
    def record(self, name='HWE-bench', kind='arxiv', identifier='1', updated='2026-10-01'):
        return {'id':'stable', 'name':name, 'releasedAt':'2026-08-01', 'firstSeenAt':'2026-08-02',
                'source':{'type':kind,'id':identifier}, 'sourceUpdatedAt':updated,
                'reviewContext':{'abstract':'Original tasks'}, 'links':{'report':'https://example.org/shared'}}

    def test_names_and_shared_reports_never_establish_source_identity(self):
        left=self.record();right=self.record(kind='github')
        self.assertNotEqual(source_key(left), source_key(right))
        self.assertFalse(discovery.same_identity(left,right))
        self.assertFalse(discovery.same_identity({},{}))
        right=self.record(identifier='2')
        self.assertFalse(discovery.same_identity(left,right))
        self.assertEqual(len(index.upsert([left],[self.record(kind='github')])),2)

    def test_new_observation_updates_evidence_without_rewriting_identity_or_dates(self):
        previous=self.record();new=self.record(updated='2026-10-23')
        new.update(id='changed-id',releasedAt='2026-10-23',firstSeenAt='2026-10-24',
                   reviewContext={'abstract':'Updated task and scoring protocol'})
        result=merge_observation(previous,new)
        self.assertEqual(result['reviewContext'],new['reviewContext'])
        for key in ('id','releasedAt','firstSeenAt'):
            self.assertEqual(result[key],previous[key])
        self.assertEqual(merge_observation(result,previous),result)
        self.assertEqual(merge_observation(result,new),result)
        self.assertEqual(previous['reviewContext']['abstract'],'Original tasks')

    def test_newer_public_source_is_requeued_but_never_rule_readmitted(self):
        public=self.record();incoming=self.record(updated='2026-10-23')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);canonical=root/'canonical.json';queue=root/'queue.json'
            canonical.write_text(json.dumps({'records':[public]}))
            with patch.object(index,'DATA_PATH',canonical),patch.object(index,'curated_records',return_value=[]), \
                    patch.object(discovery,'REVIEW_PATH',queue):
                discovery.merge_review_queue([incoming],'2026-10-24','2026-10-22',{})
            [candidate]=json.loads(queue.read_text())['candidates']
            self.assertEqual(candidate['id'],public['id'])
            self.assertEqual(candidate['releasedAt'],public['releasedAt'])
            self.assertEqual(candidate['reviewReason'],'source-changed')
            self.assertFalse(automatically_publishable(candidate,.85))

    def test_public_update_already_in_queue_still_requires_review(self):
        public=self.record();incoming=self.record(updated='2026-10-23')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);canonical=root/'canonical.json';queue=root/'queue.json'
            canonical.write_text(json.dumps({'records':[public]}));queue.write_text(json.dumps({'candidates':[public]}))
            with patch.object(index,'DATA_PATH',canonical),patch.object(index,'curated_records',return_value=[]), patch.object(discovery,'REVIEW_PATH',queue):
                discovery.merge_review_queue([incoming],'2026-10-24','2026-10-22',{})
            [candidate]=json.loads(queue.read_text())['candidates']
            self.assertEqual(candidate['reviewReason'],'source-changed')
            self.assertFalse(automatically_publishable(candidate,.85))
            self.assertEqual(candidate['releasedAt'],public['releasedAt'])

    def test_known_source_refresh_rotates_past_failure_and_preserves_last_evidence(self):
        rows=[self.record(identifier='1'),self.record(identifier='2')]
        state={};queued=[]
        def fetch(record):
            if record['source']['id']=='1':raise URLError('down')
            updated=copy.deepcopy(record);updated['sourceUpdatedAt']='2026-10-24'
            updated['reviewContext']['abstract']='New tasks'
            return updated
        stats=refresh.refresh(rows,state,fetch,queued.append,now='2026-10-24T00:00:00Z')
        self.assertEqual(stats,{'checked':2,'changed':1,'failed':1})
        self.assertEqual(len(queued),1)
        self.assertEqual(queued[0]['reviewReason'],'source-changed')
        fingerprint=state['bySource']['arxiv:2']['evidenceHash']
        refresh.refresh(rows,state,lambda r: (_ for _ in ()).throw(URLError('down')),queued.append,
                        now='2026-10-25T00:00:00Z')
        self.assertEqual(state['bySource']['arxiv:2']['evidenceHash'],fingerprint)

    def test_initial_unchanged_refresh_baselines_without_duplicate_review(self):
        record=self.record();state={};queued=[]
        def fetch(record):
            result=copy.deepcopy(record);result['reviewContext']['abstract']='Full source text absent from compact public copy'
            return result
        stats=refresh.refresh([record],state,fetch,queued.append,now='2026-10-24T00:00:00Z')
        self.assertEqual(stats['changed'],0)
        self.assertEqual(queued,[])
        self.assertEqual(state['bySource']['arxiv:1']['status'],'baseline-observed')

    def test_catalog_update_keeps_prior_id_and_release_but_homonym_stays_separate(self):
        old={'id':'legacy','name':'HWE-bench','releasedAt':'2026-01-01','sourceRecords':[{'catalog':'a','sourceId':'one','url':'https://example.org/one'}]}
        same={'id':'new-generation-id','name':'Renamed HWE','releasedAt':'2026-10-01','sourceRecords':old['sourceRecords']}
        other={'id':'different','name':'HWE-bench','sourceRecords':[{'catalog':'b','sourceId':'one','url':'https://example.org/other'}]}
        result=merge_payloads({'retrievedAt':'2026-10-24','records':[same,other]}, {'records':[old]}, {})
        self.assertEqual({r['id'] for r in result['records']},{'legacy','different'})
        self.assertEqual(next(r for r in result['records'] if r['id']=='legacy')['releasedAt'],'2026-01-01')
        self.assertEqual(merge_payloads({'retrievedAt':'2026-10-24','records':[same,other]}, result, {}), result)

    def test_fresh_catalogs_do_not_merge_same_named_rows_across_providers(self):
        with patch('sync_catalogs.MIN_EXPECTED_ROWS',{'benchlm':1,'llm-stats':1}):
            result=build_payload(json.dumps({'items':[{'benchmarkKey':'one','name':'HWE-bench'}]}).encode(),
                json.dumps([{'benchmark_id':'one','name':'HWE-bench'}]).encode(),'2026-10-24')
        self.assertEqual(len(result['records']),2)
        self.assertEqual(len({r['id'] for r in result['records']}),2)

    def test_editorial_decisions_do_not_share_cross_provider_raw_ids(self):
        from source_identity import editorial_decision
        payload={'bySourceId':{'1':{'decision':'exclude'}},
                 'bySourceKey':{'github:1':{'decision':'defer'}}}
        self.assertEqual(editorial_decision(payload,self.record())['decision'],'exclude')
        self.assertEqual(editorial_decision(payload,self.record(kind='github'))['decision'],'defer')
        self.assertEqual(editorial_decision(payload,self.record(kind='huggingface')), {})

    def test_admission_persists_two_namespaced_decisions_with_same_raw_id(self):
        import os,sys
        import generate_editorial_copy as review
        records=[self.record(kind='arxiv'),self.record(kind='github')]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);queue=root/'queue.json';output=root/'copy.json'
            queue.write_text(json.dumps({'candidates':records}))
            def responses(batch,model,key,failures):
                return [{'sourceId':r['sourceId'],'decision':'defer','canonicalName':'',
                    'canonicalNameSource':'abstract','canonicalNameEvidence':'','benchmarkMode':'unclear',
                    'stableScoringContract':False,'publicReusePath':False,'description':'Needs evidence.',
                    'whyItMatters':'Protocol unresolved.','decisionReason':'Needs evidence.',
                    'attentionForecast':{'score':0,'confidence':'Low','horizon':'7d','reason':'Unknown.'}}
                    for r in batch]
            with patch.multiple(review,REVIEW_PATH=queue,OUTPUT_PATH=output,CURATED_PATH=root/'curated.json',STATE_PATH=root/'state.json'), \
                    patch.object(review,'review_batch',side_effect=responses), \
                    patch.dict(os.environ,{'DEEPSEEK_API_KEY':'test-not-a-real-key'}), \
                    patch.object(sys,'argv',['review','--review-queue','--limit','0']):
                review.main()
            self.assertEqual(set(json.loads(output.read_text())['bySourceKey']),{'arxiv:1','github:1'})


if __name__=='__main__':unittest.main()

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from enrich_library_metrics import metric_input, scope_observation, finish_observations
from library_metrics import apply_library_metrics
from generate_library_index import public_classic


class LibraryMetricsTests(unittest.TestCase):
    def seed(self):
        return {'id':'lib_demo','familyId':'family_demo','name':'Demo','recordType':'family',
                'area':'Code & Software','primaryDomain':'General AI',
                'firstRelease':{'year':2025,'date':'2025-05-22'},'firstSeenAt':'2026-09-16',
                'construction':'Transform Existing','annotation':'Mixed',
                'links':{'paper':'https://arxiv.org/abs/2505.12345','pdf':'https://arxiv.org/pdf/2505.12345',
                         'hfPaper':'https://huggingface.co/papers/2505.12345',
                         'data':'https://huggingface.co/datasets/example/demo'}}

    def test_public_generation_preserves_metadata_and_observations(self):
        row=public_classic(self.seed(), {'reviewedAt':'2020-01-01'})
        self.assertEqual(row['firstSeenAt'],'2026-09-16')
        self.assertEqual(row['links']['pdf'],self.seed()['links']['pdf'])
        self.assertEqual(row['links']['hfPaper'],self.seed()['links']['hfPaper'])
        self.assertEqual(row['construction'],'Transform Existing')
        payload={'records':[{'benchmarkId':'lib_demo','githubStars':12,'asOf':'2026-09-16'}]}
        apply_library_metrics([row],payload)
        self.assertEqual(row['attention']['githubStars'],12)
        row['attention']['githubStars']=100
        self.assertEqual(payload['records'][0]['githubStars'],12)

    def test_library_paper_is_used_without_changing_seed_identity(self):
        seed=self.seed();record=metric_input(seed)
        self.assertEqual(record['source'],{'type':'arxiv','id':'2505.12345'})
        self.assertNotIn('source',seed)

    def test_shared_subset_counters_are_not_independent_popularity(self):
        raw={'githubStars':100,'hfPaperUpvotes':20,'hfDatasetDownloads':300,'hfDatasetLikes':5,'signalStatus':{}}
        seed={'metricScopes':{'github':'hosting_repo','hfPaper':'parent-paper','hfDataset':'parent-dataset'}}
        scoped=scope_observation(raw,seed)
        self.assertEqual(scoped['githubScope'],'hosting_repo')
        self.assertIsNone(scoped['hfDatasetDownloads'])
        self.assertIsNone(scoped['hfPaperUpvotes'])
        self.assertEqual(scoped['sharedResourceSignals']['hfDataset']['hfDatasetDownloads'],300)

    def test_provider_failure_keeps_dated_value_not_zero(self):
        previous={'date':'2026-09-15','records':[{'benchmarkId':'lib_demo','githubStars':42,'observedAt':'2026-09-15T12:00:00Z'}]}
        raw={'benchmarkId':'lib_demo','githubStars':None,'signalStatus':{'githubStars':{'state':'unavailable'}}}
        result=finish_observations([raw],[self.seed()],previous,'2026-09-16T12:00:00Z')[0]
        self.assertEqual(result['githubStars'],42)
        self.assertEqual(result['signalStatus']['githubStars']['state'],'stale')
        self.assertEqual(result['observedAt'],'2026-09-15T12:00:00Z')


if __name__=='__main__':unittest.main()


class PartialObservationTests(unittest.TestCase):
    def test_github_only_observation_keeps_radar_hf_signals(self):
        row = {'id': 'x', 'attention': {'hfPaperUpvotes': 95, 'githubStars': 1,
                                        'signalStatus': {'hfPaperUpvotes': {'state': 'fresh'}}}}
        apply_library_metrics([row], {'records': [{'benchmarkId': 'x', 'githubStars': 4,
                                                   'signalStatus': {'githubStars': {'state': 'fresh'}}}]})
        self.assertEqual(row['attention']['hfPaperUpvotes'], 95)
        self.assertEqual(row['attention']['githubStars'], 4)
        self.assertEqual(set(row['attention']['signalStatus']), {'hfPaperUpvotes', 'githubStars'})

    def test_explicit_not_applicable_still_wins(self):
        row = {'id': 'x', 'attention': {'hfDatasetDownloads': 10}}
        apply_library_metrics([row], {'records': [{'benchmarkId': 'x', 'hfDatasetDownloads': None,
                                                   'signalStatus': {'hfDatasetDownloads': {'state': 'not_applicable'}}}]})
        self.assertIsNone(row['attention']['hfDatasetDownloads'])


class FailedFetchTests(unittest.TestCase):
    def test_failed_fetch_does_not_erase_known_value(self):
        row = {'id': 'x', 'attention': {'hfPaperUpvotes': 7}}
        apply_library_metrics([row], {'records': [{'benchmarkId': 'x', 'hfPaperUpvotes': None,
                                                   'signalStatus': {'hfPaperUpvotes': {'state': 'unavailable'}}}]})
        self.assertEqual(row['attention']['hfPaperUpvotes'], 7)


class AllVisibleSelectionTests(unittest.TestCase):
    def test_stalest_first_skips_today_and_hidden(self):
        from enrich_library_metrics import library_input, stalest
        records = [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}, {'id': 'h', 'displayEligible': False}]
        previous = {'records': [{'benchmarkId': 'a', 'attemptedAt': '2026-10-01T00:00:00'},
                                {'benchmarkId': 'b', 'attemptedAt': '2026-10-05T01:00:00'}]}
        self.assertEqual([r['id'] for r in stalest(records, previous, 0, '2026-10-05')], ['c', 'a'])
        self.assertEqual([r['id'] for r in stalest(records, previous, 1, '2026-10-05')], ['c'])
        seed = library_input({'id': 'z', 'links': {'pdf': 'https://arxiv.org/pdf/2501.00001'},
                              'attention': {'githubRepo': 'https://github.com/o/z', 'hfPaperUpvotes': 3}})
        self.assertEqual(seed['source'], {'type': 'arxiv', 'id': '2501.00001'})
        self.assertEqual(seed['links']['code'], 'https://github.com/o/z')
        self.assertEqual(seed['attention']['hfPaperUpvotes'], 3)

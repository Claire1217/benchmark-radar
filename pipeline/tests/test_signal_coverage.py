import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_signal_coverage import arxiv_id, coverage, github_repo


class SignalCoverageTests(unittest.TestCase):
    def test_source_detection(self):
        self.assertEqual(github_repo({'links': {'code': 'https://github.com/Org/Repo.git'}}), 'org/repo')
        self.assertEqual(github_repo({'attention': {'githubRepo': 'https://github.com/a/b'}, 'links': {'code': 'https://github.com/x/y'}}), 'a/b')
        self.assertIsNone(github_repo({'links': {'code': 'https://gitlab.com/a/b'}}))
        self.assertEqual(arxiv_id({'links': {'pdf': 'https://arxiv.org/pdf/2501.01234v2'}}), '2501.01234')
        self.assertEqual(arxiv_id({'links': {'hfPaper': 'https://huggingface.co/papers/2502.00001'}}), '2502.00001')

    def test_shares_use_the_right_denominator(self):
        records = [
            {'id': 'a', 'links': {'code': 'https://github.com/o/a', 'report': 'https://arxiv.org/abs/2501.00001'},
             'attention': {'githubStars': 3, 'hfPaperUpvotes': 1}, 'releaseDatePrecision': 'day'},
            {'id': 'b', 'links': {'code': 'https://github.com/o/b'}, 'attention': {}},
            {'id': 'c', 'links': {'data': 'https://huggingface.co/datasets/o/c'}, 'attention': {'hfDatasetDownloads': 0}},
            {'id': 'd', 'links': {}},
            {'id': 'hidden', 'displayEligible': False, 'links': {'code': 'https://github.com/o/h'}},
        ]
        history = {'records': [{'url': 'https://github.com/o/a', 'status': 'complete'},
                               {'url': 'https://github.com/o/b', 'status': 'http-404'}]}
        got = coverage(records, history)
        self.assertEqual(got['records'], 4)
        self.assertEqual(got['githubRepo'], {'count': 2, 'of': 4, 'share': 0.5})
        self.assertEqual(got['githubStars'], {'count': 1, 'of': 2, 'share': 0.5})
        self.assertEqual(got['githubStarHistory']['count'], 1)
        self.assertEqual(got['hfPaperUpvotes'], {'count': 1, 'of': 1, 'share': 1.0})
        self.assertEqual(got['hfDatasetDownloads'], {'count': 1, 'of': 1, 'share': 1.0})  # zero is a real value
        self.assertEqual(got['noSignal']['count'], 2)


if __name__ == '__main__':
    unittest.main()

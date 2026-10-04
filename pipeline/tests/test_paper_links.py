import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paper_links import link_reviewed_papers


class PaperLinkTests(unittest.TestCase):
    def test_reviewed_sources_fill_missing_paper_only(self):
        rows = [
            {'id': 'ev', 'links': {'report': 'https://llm-stats.com/benchmarks/x'},
             'releaseEvidence': {'basis': 'paper-v1', 'sourceUrl': 'https://arxiv.org/abs/2510.25726v2'}},
            {'id': 'cat', 'links': {}, 'catalogSources': [{'paperUrl': 'https://arxiv.org/pdf/1809.08887'}]},
            {'id': 'conflict', 'links': {}, 'catalogSources': [{'paperUrl': 'https://arxiv.org/abs/1111.11111'},
                                                                {'paperUrl': 'https://arxiv.org/abs/2222.22222'}]},
            {'id': 'announce', 'links': {}, 'releaseEvidence': {'basis': 'official-announcement', 'sourceUrl': 'https://arxiv.org/abs/2501.00001'}},
            {'id': 'has', 'links': {'pdf': 'https://arxiv.org/pdf/2401.00001'},
             'releaseEvidence': {'basis': 'paper-v1', 'sourceUrl': 'https://arxiv.org/abs/2501.99999'}},
        ]
        self.assertEqual(link_reviewed_papers(rows), 2)
        self.assertEqual(rows[0]['links']['paper'], 'https://arxiv.org/abs/2510.25726')
        self.assertEqual(rows[0]['paperLinkBasis'], 'release-evidence')
        self.assertEqual(rows[1]['links']['paper'], 'https://arxiv.org/abs/1809.08887')
        for row in rows[2:]:
            self.assertNotIn('paper', row['links'], row['id'])


class ForkTests(unittest.TestCase):
    def test_hf_linked_fork_counts_upstream_stars(self):
        import enrich_metrics as em
        responses = {
            'https://huggingface.co/api/papers/1809.08887': {'upvotes': 2, 'githubRepo': 'https://github.com/ygan/spider'},
            'https://api.github.com/repos/ygan/spider': {'stargazers_count': 0, 'fork': True, 'parent': {'full_name': 'taoyds/spider'}},
            'https://api.github.com/repos/taoyds/spider': {'stargazers_count': 1101, 'fork': False},
        }
        original = em.get_json
        em.get_json = lambda url, headers=None: responses.get(url)
        try:
            out = em.enrich_one({'id': 'spider', 'links': {}, 'source': {'type': 'arxiv', 'id': '1809.08887'}}, None, True)
        finally:
            em.get_json = original
        self.assertEqual(out['githubRepo'], 'https://github.com/taoyds/spider')
        self.assertEqual(out['githubStars'], 1101)
        self.assertEqual(out['hfPaperUpvotes'], 2)


if __name__ == '__main__':
    unittest.main()


class AlignmentTests(unittest.TestCase):
    def test_alignment_fills_only_missing_links(self):
        rows = [{'id': 'a', 'links': {'report': 'https://llm-stats.com/x', 'code': 'https://github.com/keep/me'}},
                {'id': 'b', 'links': {'pdf': 'https://arxiv.org/pdf/2401.00001'}}]
        alignments = {'a': {'paper': 'https://arxiv.org/abs/2103.03874', 'code': 'https://github.com/other/repo',
                            'dataset': 'https://huggingface.co/datasets/o/d'},
                      'b': {'paper': 'https://arxiv.org/abs/2501.00002'}, 'gone': {'paper': 'https://arxiv.org/abs/1'}}
        link_reviewed_papers(rows, alignments)
        self.assertEqual(rows[0]['links']['paper'], 'https://arxiv.org/abs/2103.03874')
        self.assertEqual(rows[0]['links']['code'], 'https://github.com/keep/me')
        self.assertEqual(rows[0]['links']['data'], 'https://huggingface.co/datasets/o/d')
        self.assertEqual(rows[0]['paperLinkBasis'], 'source-alignment')
        self.assertNotIn('paper', rows[1]['links'])

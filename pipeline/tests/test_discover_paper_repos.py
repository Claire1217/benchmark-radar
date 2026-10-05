from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from discover_paper_repos import arxiv_entries, candidate_links, pick, resolve
from paper_links import link_reviewed_papers

FEED = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
<entry><id>http://arxiv.org/abs/2510.25726v2</id><summary>We release Toolathlon.</summary>
<arxiv:comment>Code: https://github.com/hkust-nlp/Toolathlon.</arxiv:comment></entry></feed>"""


class LinkExtractionTests(unittest.TestCase):
    def test_candidates(self):
        text = ('Data at https://github.com/Org/MyBench. Built on github.com/huggingface/transformers '
                'and github.com/Org/MyBench again; see https://github.com/big/mono/tree/main/bench_x, '
                'https://github.com/topics/llm and github.com/a/b.git')
        got = [(c['owner'], c['repo'], c['subpath']) for c in candidate_links(text)]
        self.assertEqual(got, [('Org', 'MyBench', False), ('huggingface', 'transformers', False),
                               ('big', 'mono', True), ('a', 'b', False)])

    def test_pick_prefers_name_match_and_refuses_ambiguity(self):
        two = candidate_links('github.com/x/library-tool and github.com/lab/my-bench')
        self.assertEqual(pick(two, 'MyBench')['repo'], 'my-bench')
        self.assertIsNone(pick(two, 'Unrelated'))
        self.assertEqual(pick(candidate_links('github.com/lab/code'), 'Anything')['repo'], 'code')
        self.assertIsNone(pick([], 'X'))

    def test_arxiv_feed_parsing(self):
        texts = arxiv_entries(['2510.25726'], fetch=lambda url: FEED)
        self.assertIn('github.com/hkust-nlp/Toolathlon', texts['2510.25726'])


class ResolveTests(unittest.TestCase):
    def test_fork_resolves_upstream_and_subpath_is_shared(self):
        repos = {'ygan/spider': {'full_name': 'ygan/spider', 'fork': True, 'parent': {'full_name': 'taoyds/spider'}},
                 'taoyds/spider': {'full_name': 'taoyds/spider', 'fork': False},
                 'big/mono': {'full_name': 'big/mono'}}
        get = lambda path: repos.get(path)
        r = resolve({'name': 'Spider', 'arxiv': '1809.08887'}, 'code: github.com/ygan/spider', None, get)
        self.assertEqual(r['code'], 'https://github.com/taoyds/spider')
        self.assertEqual(r['scope'], 'benchmark_repo')
        r = resolve({'name': 'X', 'arxiv': '1'}, 'github.com/big/mono/tree/main/x', None, get)
        self.assertEqual(r['scope'], 'hosting_repo')
        self.assertIsNone(resolve({'name': 'X', 'arxiv': '1'}, 'github.com/gone/repo', None, get))

    def test_applied_only_where_code_is_missing(self):
        rows = [{'id': 'a', 'links': {}}, {'id': 'b', 'links': {'code': 'https://github.com/keep/me'}}, {'id': 'c', 'links': {}}]
        link_reviewed_papers(rows, {}, {'a': {'code': 'https://github.com/o/a', 'source': 'arxiv-abstract-or-comment', 'scope': 'benchmark_repo'},
                                         'b': {'code': 'https://github.com/o/b', 'source': 's', 'scope': 'benchmark_repo'},
                                         'c': {'code': 'https://github.com/big/mono', 'source': 's', 'scope': 'hosting_repo'}})
        self.assertEqual(rows[0]['links']['code'], 'https://github.com/o/a')
        self.assertEqual(rows[1]['links']['code'], 'https://github.com/keep/me')
        self.assertEqual(rows[2]['metricScopes']['github'], 'hosting_repo')


if __name__ == '__main__':
    unittest.main()


class BackoffTests(unittest.TestCase):
    def test_rate_limit_waits_then_succeeds(self):
        from urllib.error import HTTPError
        calls, waits = [], []
        def fetch(url):
            calls.append(url)
            if len(calls) < 3:
                raise HTTPError(url, 429, 'Too Many', None, None)
            return FEED
        texts = arxiv_entries(['2510.25726'], fetch=fetch, sleep=waits.append)
        self.assertIn('2510.25726', texts)
        self.assertEqual(waits, [30, 60])
        self.assertTrue(calls[0].startswith('https://export.arxiv.org/'))


ABS_HTML = '''<html><blockquote class="abstract mathjax"><span class="descriptor">Abstract:</span>We present X.
Code at <a href="https://github.com/lab/xbench" class="link-external">this https URL</a>.</blockquote>
<table><tr><td class="tablecell comments mathjax">ICLR 2026, project <a href="https://xbench.ai/">this https URL</a></td></tr></table>
<div>Related: <a href="https://github.com/unrelated/sidebar">x</a></div></html>'''


class AbsPageTests(unittest.TestCase):
    def test_reads_hrefs_from_abstract_and_comments_only(self):
        from discover_paper_repos import abs_page_text, abs_pages
        text = abs_page_text(ABS_HTML)
        self.assertIn('github.com/lab/xbench', text)
        self.assertIn('xbench.ai', text)
        self.assertNotIn('unrelated/sidebar', text)
        self.assertEqual([c['repo'] for c in candidate_links(text)], ['xbench'])
        waits = []
        out = abs_pages(['2501.00001'], fetch=lambda url: ABS_HTML, sleep=waits.append)
        self.assertIn('github.com/lab/xbench', out['2501.00001'])
        self.assertEqual(waits, [3])

"""Static benchmark/category pages: stable slugs, escaped data, valid discovery files."""
import html
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
import build_github_pages
from static_pages import (assign_slugs, library_attention, attention_maxima, name_text, record_lastmod, release,
                          slugify, trim, write_static_pages, LLMS_MARKER, NOSCRIPT_MARKER)
from submit_indexnow import batches
from validate_static_site import validate_static_pages

HEADER = ('<header class="topbar"><a class="brand" href="#radar"><img src="./benchmark-radar-mark.png" alt=""></a>'
          '<nav><a href="#radar" data-route="radar">Radar</a><a href="#library" data-route="library">Library</a>'
          '<a href="./trends/" data-route="trends">Trends</a><a href="#saved" data-route="saved">Saved <span id="saved-count">0</span></a></nav></header>')


def record(identity, name, **fields):
    return {'id': identity, 'name': name, 'firstSeenAt': '2026-09-01', 'releasedAt': '2026-08-01',
            'releaseDatePrecision': 'day', 'libraryCategories': ['math'], 'links': {}, 'attention': {}, **fields}


def library(records):
    return {'manifest': {'dataAsOf': '2026-10-10', 'libraryTaxonomy': {
        'groups': [{'id': 'reasoning-knowledge', 'name': 'Reasoning & Knowledge'}],
        'directions': [{'id': 'math', 'name': 'Math Reasoning', 'group': 'reasoning-knowledge',
                        'section': 'Reasoning & Knowledge', 'description': 'Competition mathematics.'},
                       {'id': 'abstract-reasoning', 'name': 'Abstract Reasoning & Planning', 'group': 'reasoning-knowledge',
                        'section': 'Reasoning & Knowledge', 'description': 'Novel problems.'}]}},
        'records': records}


def site(root: Path):
    (root / 'trends').mkdir()
    (root / 'model-evals').mkdir()
    (root / 'index.html').write_text(f'<noscript>{NOSCRIPT_MARKER}</noscript>{HEADER}<a href="./benchmarks/">x</a><a href="./categories/">y</a>')
    for name in ('site-header.css', 'github-repositories.css', 'static-pages.css', 'github-repositories.js'):
        (root / name).write_text('/* asset */')
    (root / 'llms.txt').write_text(f'# Benchmark Radar\n\n/benchmarks/ /categories/\n\n{LLMS_MARKER}\n')
    (root / 'about').mkdir()
    (root / 'about/index.html').write_text('<a href="../categories/">Categories</a>')
    for name in ('trends/index.html', 'model-evals/index.html'):
        (root / name).write_text('<main></main>')


class SlugTests(unittest.TestCase):
    def test_slugs_are_readable_ascii(self):
        self.assertEqual(slugify('τ²-bench'), 'tau2-bench')
        self.assertEqual(slugify('M$^3$ISR'), 'm3isr')
        self.assertEqual(slugify('V\\={a}kQA'), 'vakqa')
        self.assertEqual(slugify('Translation en→Set1 COMET22'), 'translation-en-set1-comet22')
        self.assertEqual(slugify('SWE-bench Verified'), 'swe-bench-verified')
        long = slugify('An Environment for End-To-End, Realistic Agent Construction and Very Long Titles Indeed')
        self.assertLessEqual(len(long), 60)
        self.assertFalse(long.endswith('-'))
        self.assertTrue('an-environment-for-end-to-end'.startswith(long[:10]))

    def test_collisions_keep_existing_urls(self):
        old = record('bm_simple_a', 'SIMPLE', firstSeenAt='2026-08-19')
        hidden = record('bm_other_b', 'Other', displayEligible=False)
        before = assign_slugs([old, hidden])
        newcomer = record('bm_simple_0', 'Simple', firstSeenAt='2026-10-09')
        after = assign_slugs([newcomer, old, hidden])
        self.assertEqual(before['bm_simple_a'], 'simple')
        self.assertEqual(after['bm_simple_a'], 'simple')
        self.assertRegex(after['bm_simple_0'], r'^simple-[0-9a-f]{6}$')
        self.assertEqual(after, assign_slugs([hidden, old, newcomer]), 'input order must not matter')
        # Hidden records reserve their slug, so hiding one never moves another page.
        clash = record('bm_other_c', 'OTHER', firstSeenAt='2026-10-01')
        self.assertNotEqual(assign_slugs([hidden, clash])['bm_other_c'], 'other')


class RecordFactTests(unittest.TestCase):
    def test_trim_cuts_on_a_word(self):
        self.assertEqual(trim('short  text', 155), 'short text')
        text = trim('word ' * 60, 40)
        self.assertLessEqual(len(text), 40)
        self.assertTrue(text.endswith('word…'))

    def test_unverified_release_dates_stay_unknown(self):
        self.assertIsNone(release(record('a', 'A', releasedAt='0001-01-01')))
        self.assertIsNone(release(record('a', 'A', releaseDatePrecision='unknown')))
        self.assertEqual(release(record('a', 'A', releaseDatePrecision='month'))['date'], '2026-08')
        paper = release(record('a', 'A', releaseEvidence={'basis': 'paper-v1', 'sourceUrl': 'https://arxiv.org/abs/1'}))
        self.assertEqual((paper['label'], paper['source']), ('Paper published', 'https://arxiv.org/abs/1'))

    def test_lastmod_ignores_attention_refreshes(self):
        base = record('a', 'A', curation={'reviewedAt': '2026-09-20T10:00:00Z'})
        refreshed = {**base, 'attention': {'githubStars': 99, 'observedAt': '2026-10-10T00:00:00Z'}}
        self.assertEqual(record_lastmod(base, '2026-10-10'), '2026-09-20')
        self.assertEqual(record_lastmod(refreshed, '2026-10-10'), '2026-09-20')
        self.assertEqual(record_lastmod(record('a', 'A', firstSeenAt='2026-10-11'), '2026-10-10'), '2026-10-10')

    def test_attention_matches_library_sort(self):
        rows = [record('a', 'A', attention={'githubStars': 100}), record('b', 'B', attention={'githubStars': 10}),
                record('c', 'C')]
        maxima = attention_maxima(rows)
        scores = [library_attention(r, maxima) for r in rows]
        self.assertGreater(scores[0], scores[1])
        self.assertIsNone(scores[2], 'no observed signal has no score, never zero')


class WriteStaticPagesTests(unittest.TestCase):
    def build(self, records):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        site(root)
        payload = library(records)
        (root / 'data').mkdir()
        (root / 'data/library_index.json').write_text(json.dumps(payload))
        counts = write_static_pages(root, payload, build_github_pages.visible, {'math'}, {'/': '2026-10-10', '/about/': None,
                                                                                    '/trends/': '2026-10-10', '/model-evals/': None})
        return root, counts

    def test_pages_escape_data_and_never_invent_facts(self):
        hostile = record('bm_x_1', 'X<script>alert(1)</script>', description='Uses <b>tags</b> & "quotes" ' + 'long ' * 40,
                         links={'report': 'https://arxiv.org/abs/2610.00001', 'code': 'javascript:alert(1)'},
                         attention={'githubStars': 5, 'githubScope': 'benchmark_repo', 'observedAt': '2026-10-09T01:00:00Z'})
        plain = record('bm_y_2', 'Y-Bench', releasedAt='0001-01-01', publishers=[{'name': 'Y Lab', 'role': 'benchmark-publisher'}])
        root, counts = self.build([hostile, plain, record('bm_z_3', 'Hidden', displayEligible=False)])
        self.assertEqual(counts['benchmarks'], 2)
        page = (root / 'benchmarks/x-script-alert-1-script/index.html').read_text()
        self.assertNotIn('<script>alert', page)
        self.assertNotIn('<b>tags', page)
        self.assertNotIn('javascript:', page)
        self.assertIn('&lt;b&gt;tags&lt;/b&gt; &amp; &quot;quotes&quot;', page)
        self.assertIn('observed 2026-10-09', page)
        self.assertIn('Missing signals remain unknown rather than being converted to zero.', page)
        self.assertIn('href="/#library?q=X%3Cscript%3E', page)
        description = re.search(r'<meta name="description" content="([^"]*)"', page)[1]
        self.assertLessEqual(len(html.unescape(description)), 155)
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page)[1])['@graph']
        dataset = graph[0]
        self.assertEqual(dataset['@type'], 'Dataset')
        self.assertEqual(dataset['sameAs'], ['https://arxiv.org/abs/2610.00001'])
        self.assertEqual(dataset['isPartOf'], {'@id': 'https://benchmark-radar.com/#website'})
        self.assertNotIn('creator', dataset)
        other = (root / 'benchmarks/y-bench/index.html').read_text()
        other_data = json.loads(re.search(r'application/ld\+json">(.*?)</script>', other)[1])['@graph'][0]
        self.assertEqual(other_data['creator'], [{'@type': 'Organization', 'name': 'Y Lab'}])
        self.assertNotIn('datePublished', other_data)
        self.assertIn('Release date unverified', other)
        self.assertIn('No public attention signal has been observed', other)
        self.assertFalse((root / 'benchmarks/hidden').exists())

    def test_category_pages_indexes_and_discovery_files(self):
        rows = [record('bm_a', 'Alpha', attention={'githubStars': 1}), record('bm_b', 'Beta', attention={'githubStars': 50}),
                record('bm_c', 'Gamma', libraryCategories=['abstract-reasoning', 'math'])]
        root, _ = self.build(rows)
        category = (root / 'categories/math/index.html').read_text()
        order = [category.index(f'/benchmarks/{s}/') for s in ('beta', 'alpha', 'gamma')]
        self.assertEqual(order, sorted(order), 'sorted by Library attention')
        self.assertIn('href="/trends/#c=math"', category)
        self.assertNotIn('/trends/#c=abstract-reasoning', (root / 'categories/abstract-reasoning/index.html').read_text())
        self.assertIn('Math Reasoning benchmarks — 3 AI benchmarks | Benchmark Radar', category)
        items = json.loads(re.search(r'application/ld\+json">(.*?)</script>', category)[1])['@graph'][0]['mainEntity']
        self.assertEqual(items['numberOfItems'], 3)
        az = (root / 'benchmarks/index.html').read_text()
        self.assertIn('id="letter-a"', az)
        urls = [u.findtext('{http://www.sitemaps.org/schemas/sitemap/0.9}loc') for u in ET.parse(root / 'sitemap.xml').getroot()]
        self.assertIn('https://benchmark-radar.com/benchmarks/alpha/', urls)
        self.assertIn('https://benchmark-radar.com/categories/math/', urls)
        self.assertIn('https://benchmark-radar.com/trends/', urls)
        llms = (root / 'llms.txt').read_text()
        self.assertNotIn(LLMS_MARKER, llms)
        self.assertIn('[Math Reasoning](https://benchmark-radar.com/categories/math/)', llms)
        self.assertIn('- [Alpha](https://benchmark-radar.com/benchmarks/alpha/): Math Reasoning · 2026-08-01', (root / 'llms-full.txt').read_text())
        self.assertIn('href="./categories/math/"', (root / 'index.html').read_text())
        self.assertIn('href="/categories/"', (root / 'trends/index.html').read_text())

    def test_validator_accepts_build_and_rejects_broken_pages(self):
        root, _ = self.build([record('bm_a', 'Alpha')])
        build_github_pages.OUTPUT, saved = root, build_github_pages.OUTPUT
        try:
            build_github_pages.write_feed(build_github_pages.json.loads((root / 'data/library_index.json').read_text())['records'],
                                          '2026-10-10', {'bm_a': 'alpha'})
        finally:
            build_github_pages.OUTPUT = saved
        self.assertIn('<link>https://benchmark-radar.com/benchmarks/alpha/</link>', (root / 'feed.xml').read_text())
        self.assertIn('benchmark-radar:bm_a</guid>', (root / 'feed.xml').read_text())
        self.assertEqual(validate_static_pages(root), 5)
        page = root / 'benchmarks/alpha/index.html'
        page.write_text(page.read_text().replace('rel="canonical"', 'rel="alternate"'))
        with self.assertRaises(SystemExit):
            validate_static_pages(root)


class IndexNowTests(unittest.TestCase):
    def test_batches_respect_the_request_limit(self):
        self.assertEqual([len(b) for b in batches([str(i) for i in range(25001)])], [10000, 10000, 5001])
        self.assertEqual(batches([]), [])


class NameTests(unittest.TestCase):
    def test_tex_names_render_as_text(self):
        self.assertEqual(name_text('$\\tau^\\tau$-Bench'), 'τ^τ-Bench')
        self.assertEqual(name_text('M$^3$R-Bench'), 'M³R-Bench')


if __name__ == '__main__':
    unittest.main()

from pathlib import Path
import re
from urllib.parse import urlsplit
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_github_pages import version_trends_assets


class TrendsAssetVersionsTest(unittest.TestCase):
    def test_data_update_invalidates_script_and_page_references(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'trends').mkdir()
            (root / 'data').mkdir()
            (root / 'site-header.css').write_text('.topbar{height:60px}')
            (root / 'benchmark-name.js').write_text('function benchmarkNameHtml(value){return value}')
            def build(data):
                (root / 'data/trends_topics.json').write_text(data)
                (root / 'trends/trends.js').write_text("fetch('../data/trends_topics.json')")
                (root / 'trends/index.html').write_text('<link href="../site-header.css"><script src="../benchmark-name.js"></script><script src="./trends.js"></script>')
                version_trends_assets(root)
                page = (root / 'trends/index.html').read_text()
                script_name = re.search(r'src="./([^"]+)"', page)[1]
                script = (root / 'trends' / urlsplit(script_name).path).read_text()
                data_name = re.search(r"../data/([^']+)", script)[1]
                self.assertEqual((root / 'data' / urlsplit(data_name).path).read_text(), data)
                self.assertNotIn('href="../site-header.css"', page)
                self.assertRegex(page, r'benchmark-name\.js\?v=[0-9a-f]{12}')
                return script_name
            first = build('{"version":1}')
            self.assertEqual(first, build('{"version":1}'))
            self.assertNotEqual(first, build('{"version":2}'))
            self.assertTrue((root / 'trends' / urlsplit(first).path).exists())


class DirectionsScriptVersionTest(unittest.TestCase):
    def test_directions_script_and_search_index_are_versioned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'trends').mkdir()
            (root / 'data').mkdir()
            (root / 'site-header.css').write_text('x')
            (root / 'benchmark-name.js').write_text('x')
            (root / 'data/trends_topics.json').write_text('{}')
            (root / 'data/trends_search.json').write_text('{"version":1}')
            (root / 'trends/directions.js').write_text('const Directions={}')
            (root / 'trends/trends.js').write_text("fetch('../data/trends_topics.json');fetch('../data/trends_search.json')")
            (root / 'trends/index.html').write_text('<script src="./directions.js"></script><script src="./trends.js"></script>')
            version_trends_assets(root)
            page = (root / 'trends/index.html').read_text()
            script = (root / 'trends/trends.js').read_text()
            self.assertRegex(page, r'\./directions\.js\?v=[0-9a-f]{12}')
            self.assertRegex(script, r'\.\./data/trends_search\.json\?v=[0-9a-f]{12}')

"""README overview and AWESOME list follow the public v5 categories."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class GeneratedListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / 'data/library_index.json').read_text())['manifest']['libraryTaxonomy']
        cls.readme = (ROOT / 'README.md').read_text()
        cls.awesome = (ROOT / 'AWESOME_BENCHMARKS.md').read_text()
        cls.public = json.loads((ROOT / 'data/benchmarks_index.json').read_text())

    def test_readme_links_every_category_with_its_count(self):
        for d in self.manifest['directions']:
            self.assertIn(f"direction={d['id']}) · {d['count']:,}", self.readme, d['id'])
        for retired in ('vision-language-models', 'data-analysis-agents', 'coding-agents'):
            self.assertNotIn('direction=' + retired, self.readme)

    def test_readme_groups_follow_taxonomy_groups(self):
        overview = self.readme.split('### Explore the library')[1]
        for g in self.manifest['groups']:
            self.assertIn(f"**{g['name']}**", overview)

    def test_awesome_lists_each_release_once_under_its_primary(self):
        visible = [r for r in self.public['records'] if r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe']
        entries = re.findall(r'^- \*\*', self.awesome, flags=re.M)
        self.assertEqual(len(entries), len(visible))
        names = {d['id']: d['name'] for d in self.manifest['directions']}
        sections = re.split(r'^## ', self.awesome, flags=re.M)
        by_section = {s.split('\n', 1)[0]: s for s in sections}
        for r in visible[:200]:
            primary = (r.get('libraryCategories') or [None])[0]
            heading = names.get(primary, 'Other benchmark tasks')
            self.assertIn(f"- **{r['name']}** ({r['releasedAt']})", by_section[heading], r['name'])


if __name__ == '__main__':
    unittest.main()

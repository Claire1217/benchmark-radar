"""Reviewed anchor benchmarks and model-card aliases stay consistent with the Library."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from library_identity import apply_reviewed_aliases

load = lambda name: json.loads((ROOT / 'data' / name).read_text())
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.casefold())


class ReviewedAliasTests(unittest.TestCase):
    def test_aliases_follow_redirects_and_skip_duplicates(self):
        rows = [{'id': 'new', 'name': 'SWE-bench Verified', 'aliases': ['SWE Verified']}]
        missing = apply_reviewed_aliases(rows, {'aliases': {'old': ['SWE Verified', 'SWE-bench Verified', 'SWEV'],
                                                           'gone': ['X']}}, {'old': 'new'})
        self.assertEqual(rows[0]['aliases'], ['SWE Verified', 'SWEV'])
        self.assertEqual(missing, ['gone'])


class AnchorDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = load('library_index.json')['records']
        cls.by_id = {r['id']: r for r in cls.library}
        cls.anchors = [r for r in load('supplemental_catalog_records.json')['records']
                       if any(s['catalog'] == 'anchor-review' for s in r['sourceRecords'])]

    def test_every_anchor_has_verified_source_and_description(self):
        self.assertGreaterEqual(len(self.anchors), 40)
        for row in self.anchors:
            source = next(s for s in row['sourceRecords'] if s['catalog'] == 'anchor-review')
            self.assertTrue(source['url'].startswith('https://'), row['name'])
            self.assertGreater(len(row['description']), 30, row['name'])

    def test_every_anchor_reaches_the_library(self):
        names = {norm(n) for r in self.library for n in [r['name'], *(r.get('aliases') or [])]}
        for row in self.anchors:
            self.assertIn(norm(row['name']), names, row['name'])

    def test_aliases_target_live_records_and_are_unambiguous(self):
        aliases = load('library_aliases.json')['aliases']
        own = {}
        for record in self.library:
            own.setdefault(norm(record['name']), set()).add(record['id'])
        for target, labels in aliases.items():
            self.assertIn(target, self.by_id, target)
            for label in labels:
                self.assertIn(label, self.by_id[target]['aliases'], (target, label))
                # An alias must not be another record's canonical name.
                self.assertLessEqual(own.get(norm(label), set()), {target}, (target, label))

    def test_anchor_release_dates_are_reviewed_and_not_future(self):
        anchor_ids = {r['id'] for r in self.anchors}
        dates = [d for d in load('library_release_dates.json')['records'] if d['id'] in anchor_ids]
        self.assertGreater(len(dates), 20)
        for item in dates:
            self.assertTrue(item['sourceUrl'].startswith('https://'))
            self.assertLessEqual(item['date'], '2026-10-05')


if __name__ == '__main__':
    unittest.main()

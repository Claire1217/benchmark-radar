import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
import classify_categories as cc
import library_categories as lc

VALID = {c['id'] for c in json.loads((ROOT / 'data/taxonomy_v5.json').read_text())['categories']}


class ValidateTests(unittest.TestCase):
    batch = [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}, {'id': 'd'}]

    def test_only_well_formed_answers_for_asked_ids(self):
        answers = [
            {'id': 'a', 'primary': 'tool-use', 'secondary': ['tool-use', 'professional-work', 'bogus', 'math', 'science'], 'confidence': 'high'},
            {'id': 'a', 'primary': 'math'},                       # duplicate: first answer wins
            {'id': 'b', 'primary': 'vision-language-models'},     # retired id -> rejected
            {'id': 'c', 'primary': 'other', 'secondary': ['math'], 'confidence': 'sure'},
            {'id': 'zzz', 'primary': 'math'},                     # not asked
            'garbage',
        ]
        got = cc.validate(self.batch, answers, VALID)
        self.assertEqual(set(got), {'a', 'c'})
        self.assertEqual(got['a'], {'primary': 'tool-use', 'secondary': ['professional-work', 'math'], 'confidence': 'high'})
        self.assertEqual(got['c'], {'primary': 'other', 'secondary': [], 'confidence': 'low'})
        self.assertEqual(cc.validate(self.batch, {'records': []}, VALID), {})

    def test_brief_lists_every_category(self):
        text = cc.brief(json.loads((ROOT / 'data/taxonomy_v5.json').read_text()))
        for identity in VALID:
            self.assertIn(f'- {identity}:', text)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.saved = (cc.ASSIGNMENTS_PATH, cc.LIBRARY_PATH)
        cc.ASSIGNMENTS_PATH = root / 'assignments.json'
        cc.LIBRARY_PATH = root / 'library.json'
        cc.ASSIGNMENTS_PATH.write_text(json.dumps({'version': 'taxonomy-v5', 'records': {'old': {'primary': 'math', 'secondary': [], 'confidence': 'high', 'basis': 'model-review'}}}))
        rows = [{'id': f'new{i}', 'name': f'N{i}', 'description': 'Agents operate desktop apps.',
                 'categoryAssignment': {'basis': 'keyword-provisional'}} for i in range(30)]
        rows += [{'id': 'old', 'name': 'Old', 'categoryAssignment': {'basis': 'model-review'}},
                 {'id': 'hidden', 'name': 'H', 'displayEligible': False, 'categoryAssignment': {'basis': 'keyword-provisional'}}]
        cc.LIBRARY_PATH.write_text(json.dumps({'records': rows}))

    def tearDown(self):
        cc.ASSIGNMENTS_PATH, cc.LIBRARY_PATH = self.saved
        self.temp.cleanup()

    def test_new_records_are_reviewed_and_failed_batches_are_isolated(self):
        calls = []

        def post(system, batch):
            calls.append(len(batch))
            if len(calls) == 2:
                raise TimeoutError('provider down')
            return [{'id': r['id'], 'primary': 'computer-use', 'secondary': [], 'confidence': 'medium'} for r in batch]

        stats = cc.run(post, today='2026-10-05', model='m')
        self.assertEqual(calls, [25, 5])
        self.assertEqual(stats, {'pending': 30, 'accepted': 25, 'rejected': 5})
        records = json.loads(cc.ASSIGNMENTS_PATH.read_text())['records']
        self.assertEqual(records['old']['basis'], 'model-review')  # reviewed rows are never re-asked
        self.assertEqual(records['new0'], {'primary': 'computer-use', 'secondary': [], 'confidence': 'medium',
                                           'basis': 'model-review-daily', 'reviewedAt': '2026-10-05', 'model': 'm'})
        self.assertNotIn('new29', records)
        self.assertNotIn('hidden', records)

    def test_daily_review_replaces_keyword_placement(self):
        cc.run(lambda s, b: [{'id': r['id'], 'primary': 'speech-audio'} for r in b], today='2026-10-05')
        original = lc.assignments
        lc.assignments = lambda: json.loads(cc.ASSIGNMENTS_PATH.read_text())['records']
        try:
            row = [{'id': 'new3', 'name': 'N3', 'description': 'Agents operate desktop apps.'}]
            lc.annotate_categories(row)
        finally:
            lc.assignments = original
        self.assertEqual(row[0]['libraryCategories'], ['speech-audio'])
        self.assertEqual(row[0]['categoryAssignment']['basis'], 'model-review-daily')

    def test_nothing_pending_writes_nothing(self):
        cc.LIBRARY_PATH.write_text(json.dumps({'records': []}))
        before = cc.ASSIGNMENTS_PATH.read_text()
        self.assertEqual(cc.run(lambda s, b: [], today='2026-10-05')['pending'], 0)
        self.assertEqual(cc.ASSIGNMENTS_PATH.read_text(), before)


if __name__ == '__main__':
    unittest.main()

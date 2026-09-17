import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from library_source_reviews import apply_source_reviews
from research_directions import classify_directions
ROOT=Path(__file__).resolve().parents[2]

class ReviewedCoverageTests(unittest.TestCase):
    def test_pending_correction_does_not_claim_verification_or_date(self):
        rows = [{'id': 'a', 'name': 'Ambiguous', 'description': 'Unsupported identity',
                 'dataStatus': 'catalog-listed-unverified', 'releaseDatePrecision': 'unknown'}]
        apply_source_reviews(rows, {'reviewedAt': '2026-09-17', 'pending': [{
            'id': 'a', 'note': 'Original identity is unresolved',
            'description': 'Catalog label awaiting source verification',
            'sources': ['https://example.org/catalog'],
        }]})
        self.assertEqual(rows[0]['oneLine'], 'Catalog label awaiting source verification')
        self.assertEqual(rows[0]['previousDescription'], 'Unsupported identity')
        self.assertEqual(rows[0]['descriptionProvenance']['basis'], 'identity-unresolved')
        self.assertEqual(rows[0]['dataStatus'], 'catalog-listed-unverified')
        self.assertEqual(rows[0]['releaseDatePrecision'], 'unknown')
        self.assertNotIn('taskReview', rows[0])

    def test_corrected_catalog_names_preserve_identity_and_parent(self):
        rows = {r['id']: r for r in json.loads((ROOT/'data/library_index.json').read_text())['records']}
        for identity, old_name, parent in [
            ('catalog_c01c2eefae4457df', 'AI-Needle', 'catalog_c847be0a0dc9793c'),
            ('catalog_484ddc4711d4f077', 'MMAnswerBench', 'catalog_9f633d8c67b1c89b'),
            ('catalog_19876f7f9ed94bec', 'WideResearch', 'catalog_d91422f7df97f946'),
        ]:
            row = rows[identity]
            self.assertIn(old_name, row['aliases'])
            self.assertEqual(row['benchmarkParentId'], parent)
            self.assertEqual(row['name'], rows[parent]['name'] + ' (Qwen comparison)')
            self.assertEqual(row['releaseEvidence']['dateScope'], 'underlying-dataset')

    def test_review_wins_over_incidental_wording(self):
        record={'id':'a','name':'Example','description':'GUI grounding supports multi-step task completion'}
        review={'reviewedAt':'2026-09-15','reviews':[{'id':'a','directions':['computer-use'],'sources':['https://example.org/task'],'note':'Scored on full task completion','role':'observation-setting'}]}
        rows=[copy.deepcopy(record)];apply_source_reviews(rows,review)
        self.assertEqual(list(classify_directions(rows[0])),['computer-use'])
        self.assertNotIn('taskReview',record)

    def test_addition_collision_fails_instead_of_overwriting(self):
        with self.assertRaises(ValueError):
            apply_source_reviews([{'id':'a'}],{'additions':[{'id':'a'}]})

    def test_published_scope_and_homonym_boundaries(self):
        data=json.loads((ROOT/'data/library_index.json').read_text());rows={r['name']:r for r in data['records']}
        for name in ['OSWorld-G','GroundUI-1K','UI-Vision','ScreenSpot-v2','UI-I2E-Bench','VenusBench-GD']:
            self.assertIn('gui-grounding',rows[name]['researchDirections'])
        for name in ['MobileWorld','OSWorld Screenshot-only']:
            self.assertNotIn('gui-grounding',rows[name]['researchDirections'])
        self.assertIn('ai-for-science',rows['ScienceAgentBench']['researchDirections'])
        self.assertIn('deep-research',rows['BrowseComp']['researchDirections'])
        self.assertIn('coding-agents',rows['SWE-bench']['researchDirections'])
        self.assertNotEqual(rows['AIR-BENCH']['id'],rows['AIR-Bench (Audio)']['id'])
        self.assertNotIn('audio-speech',rows['AIR-BENCH']['researchDirections'])
        self.assertNotIn('MMMU (validation)',rows)
        self.assertIn('MMMU (validation)',rows['MMMU (val)']['aliases'])
        self.assertEqual(rows['ScreenSpot-v2']['benchmarkParentId'],rows['ScreenSpot']['id'])

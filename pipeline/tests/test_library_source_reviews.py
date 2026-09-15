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

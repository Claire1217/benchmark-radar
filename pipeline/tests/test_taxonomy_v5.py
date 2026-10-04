"""Taxonomy v5 registry, reviewed assignments, fallback and the merge rule."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from category_overlap import REVIEW_THRESHOLD, overlaps
from library_categories import keyword_assignment

TAXONOMY = json.loads((ROOT / 'data/taxonomy_v5.json').read_text())
IDS = {c['id'] for c in TAXONOMY['categories']}


class RegistryTests(unittest.TestCase):
    def test_registry_is_well_formed(self):
        groups = {g['id'] for g in TAXONOMY['groups']}
        self.assertEqual(len(IDS), len(TAXONOMY['categories']))
        for c in TAXONOMY['categories']:
            self.assertIn(c['group'], groups, c['id'])
            self.assertGreaterEqual(len(c['anchors']), 2, c['id'])
            self.assertEqual(len(c['anchors']), len(set(c['anchors'])), c['id'])
            self.assertGreater(len(c['description']), 30, c['id'])
            re.compile(c['keywords'], re.I)
        self.assertEqual({c['group'] for c in TAXONOMY['categories']}, groups, 'empty group')

    def test_retired_ids_redirect_to_live_categories(self):
        for old, item in TAXONOMY['retired'].items():
            self.assertNotIn(old, IDS)
            self.assertIn(item['redirect'], IDS, old)

    def test_vague_umbrellas_are_gone(self):
        names = {c['name'].casefold() for c in TAXONOMY['categories']}
        for vague in ('vision-language models', 'data analysis agents', 'content generation', 'coding'):
            self.assertNotIn(vague, names)


class AssignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assigned = json.loads((ROOT / 'data/taxonomy_v5_assignments.json').read_text())['records']
        cls.library = json.loads((ROOT / 'data/library_index.json').read_text())['records']

    def test_assignments_use_valid_ids(self):
        for rid, item in self.assigned.items():
            self.assertIn(item['primary'], IDS | {'other'}, rid)
            self.assertLessEqual(len(item['secondary']), 2, rid)
            self.assertNotIn(item['primary'], item['secondary'], rid)
            self.assertTrue(set(item['secondary']) <= IDS, rid)
            self.assertIn(item['confidence'], {'high', 'medium', 'low'}, rid)

    def test_assignments_point_at_live_records(self):
        live = {r['id'] for r in self.library}
        stale = [rid for rid in self.assigned if rid not in live]
        # Records can be merged away later; a large share would mean a broken id scheme.
        self.assertLess(len(stale) / len(self.assigned), 0.05, stale[:10])

    def test_lab_reported_benchmarks_are_reviewed(self):
        for r in self.library:
            if r.get('modelReportReferences') and r.get('displayEligible') is not False:
                self.assertNotEqual((r.get('categoryAssignment') or {}).get('basis'), 'keyword-provisional', r['name'])

    def test_no_category_pair_reaches_merge_review(self):
        _, pairs = overlaps(self.library)
        flagged = [p for p in pairs if p['overlap'] >= REVIEW_THRESHOLD]
        self.assertEqual(flagged, [], 'Top-10 overlap >= 50%: review these categories for a merge')


class FallbackTests(unittest.TestCase):
    CASES = {
        'agentic-coding': ('RepoFixBench', 'Agents resolve GitHub issues in real repositories and submit pull requests.'),
        'computer-use': ('DeskOps', 'Agents operate desktop applications on an operating system from screenshots.'),
        'speech-audio': ('VoxEval', 'Evaluates speech recognition and spoken dialogue in voice assistants.'),
        'image-video-generation': ('MotionGen', 'Text-to-video generation quality and temporal consistency.'),
        'agent-security': ('InjectBench', 'Measures prompt injection attacks that hijack tool-using agents.'),
        'embodied-robotics': ('GraspSuite', 'Robot manipulation tasks for vision-language-action policies.'),
        'health-medicine': ('ClinicQA', 'Clinical diagnosis questions written by doctors about patients.'),
        'forecasting': ('FutureQ', 'Forecasting future events against prediction markets.'),
        'video-understanding': ('LongVidQA', 'Video question answering over hour-long egocentric videos.'),
    }

    def test_typical_new_records_land_in_expected_category(self):
        for expected, (name, description) in self.CASES.items():
            got = keyword_assignment({'id': name, 'name': name, 'description': description})
            self.assertIsNotNone(got, name)
            self.assertEqual(got['primary'], expected, (name, got))
            self.assertEqual(got['basis'], 'keyword-provisional')

    def test_unmatched_record_stays_unclassified(self):
        self.assertIsNone(keyword_assignment({'id': 'x', 'name': 'Zyx', 'description': 'Quantum widgets.'}))


if __name__ == '__main__':
    unittest.main()


class LegacyFilterCoverageTests(unittest.TestCase):
    def test_every_legacy_label_in_data_has_a_v5_target(self):
        library = json.loads((ROOT / 'data/library_index.json').read_text())['records']
        legacy = TAXONOMY['legacyFilters']
        domains = {d for r in library for d in r.get('applicationDomains') or []}
        capabilities = {c for r in library for c in r.get('capabilityGroups') or []}
        self.assertEqual(domains - set(legacy['domain']), set())
        self.assertEqual(capabilities - set(legacy['capability']), set())
        for kind in legacy.values():
            self.assertTrue(set(kind.values()) <= IDS)

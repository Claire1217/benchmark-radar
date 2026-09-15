"""Source-reviewed sample and cross-surface aggregation regressions."""
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from research_directions import classify_directions, annotate_records
from generate_trends_comparison import current_repo_directions, repo_key

class TaxonomyAuditTests(unittest.TestCase):
    def test_frozen_sample_and_regeneration(self):
        rows = json.loads((ROOT/'data/taxonomy_review_20260915.json').read_text())
        library = {r['id']: r for r in json.loads((ROOT/'data/library_index.json').read_text())['records']}
        self.assertEqual(len(rows), 50)
        self.assertEqual(len({r['id'] for r in rows}), 50)
        for review in rows:
            record = library[review['id']]
            self.assertEqual(set(record['researchDirections']), set(review['after']), review['name'])
            annotate_records([record])
            self.assertEqual(set(record['researchDirections']), set(review['after']), review['name'])

    def test_public_library_parity(self):
        library = {r['id']: r for r in json.loads((ROOT/'data/library_index.json').read_text())['records']}
        for r in json.loads((ROOT/'data/benchmarks_index.json').read_text())['records']:
            if r['id'] in library:
                self.assertEqual(r['researchDirections'], library[r['id']]['researchDirections'], r['name'])

    def test_programming_and_natural_languages_are_distinct(self):
        for text in ['Multilingual code editing in Rust and Python.', 'Macro translation from C to Rust.']:
            self.assertNotIn('multilingual-nlp', classify_directions({'description': text}))
        self.assertIn('multilingual-nlp', classify_directions({'description': 'Cross-lingual software questions in English and Chinese.'}))

    def test_current_repo_mapping_and_exclusions(self):
        rows = [
            {'links': {'code': 'https://github.com/Org/Repo.git'}, 'researchDirections': ['software-engineering']},
            {'links': {'code': 'https://github.com/org/repo'}, 'researchDirections': ['coding-agents']},
            {'links': {'code': 'https://github.com/aider-ai/aider'}, 'researchDirections': ['multilingual-nlp']},
            {'links': {'code': 'https://github.com/org/hidden'}, 'researchDirections': ['video-understanding'], 'displayEligible': False},
        ]
        mapping=current_repo_directions(rows)
        self.assertEqual(mapping, {'org/repo': {'software-engineering', 'coding-agents'}})
        library=json.loads((ROOT/'data/library_index.json').read_text())['records']
        mapping=current_repo_directions(library)
        repos=json.loads((ROOT/'data/trends_comparison.json').read_text())['repos']
        self.assertEqual(len(repos),len({repo_key(r['url']) for r in repos}))
        for r in repos:
            self.assertEqual(set(r['directions']),mapping[repo_key(r['url'])])

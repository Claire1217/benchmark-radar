"""Failure paths and persisted outputs for scheduled admission and forecasts."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import apply_overrides
import forecast_attention
import generate_editorial_copy as review
import review_scheduler as scheduler


class ReviewSafetyTests(unittest.TestCase):
    def record(self, identifier='example', day='2026-01-01'):
        return {'id': 'bm_' + identifier, 'name': identifier, 'releasedAt': day,
                'source': {'type': 'arxiv', 'id': identifier}, 'displayEligible': True,
                'description': 'Existing validated description', 'whyItMatters': 'Existing rationale',
                'curation': {'state': 'ai-reviewed'}}

    def test_scheduler_reserves_capacity_for_old_and_new_and_rotates_retries(self):
        old = [self.record(f'old{i}') for i in range(5)]
        new = [self.record(f'new{i}', '2026-10-24') for i in range(5)]
        state = {}
        selected = scheduler.select(new + old, state, limit=4, now='2026-10-24T00:00:00Z')
        self.assertEqual(sum(r['name'].startswith('old') for r in selected), 2)
        self.assertEqual(sum(r['name'].startswith('new') for r in selected), 2)
        for r in selected:
            scheduler.record_attempt(state, r, 'source-unavailable', '2026-10-24T00:00:00Z', 'fp')
        retry = scheduler.select(new + old, state, limit=4, now='2026-10-24T12:00:00Z')
        self.assertFalse({r['id'] for r in selected} & {r['id'] for r in retry})
        forced = scheduler.select([selected[0]], state, limit=4, now='2026-10-24T12:00:00Z', force=True)
        self.assertEqual(forced, [selected[0]])

    def test_source_failure_preserves_actual_curated_and_copy_files(self):
        record = self.record()
        with tempfile.TemporaryDirectory() as directory:
            paths = {name: Path(directory) / name for name in ('data', 'curated', 'copy', 'state')}
            for name in ('data', 'curated'):
                paths[name].write_text(json.dumps({'records': [record]}))
            paths['copy'].write_text(json.dumps({'schemaVersion': '1.0', 'bySourceId': {}}))
            original = {name: paths[name].read_bytes() for name in ('curated', 'copy')}
            with patch.multiple(review, DATA_PATH=paths['data'], CURATED_PATH=paths['curated'],
                                OUTPUT_PATH=paths['copy'], STATE_PATH=paths['state']), \
                    patch.object(review, 'fetch_abstracts', return_value={}), \
                    patch.object(sys, 'argv', ['review', '--review-public']), \
                    patch.object(review, 'review_batch') as model:
                review.main()
            model.assert_not_called()
            for name in original:
                self.assertEqual(paths[name].read_bytes(), original[name])
            state = json.loads(paths['state'].read_text())['bySource']['arxiv:example']
            self.assertEqual(state['status'], 'source-unavailable')
            self.assertIn('preserved', state['history'][0]['reason'])

    def test_defer_and_unverified_exclusion_do_not_unpublish(self):
        record = self.record()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'curated.json'
            path.write_text(json.dumps({'records': [record]}))
            for decision in ('defer', 'exclude'):
                with patch.object(review, 'CURATED_PATH', path):
                    review.upsert_curated([record], [{'sourceId': 'example', 'decision': decision,
                        'decisionReason': 'Unverified'}], '2026-10-24', 'test', audit_existing=True, allow_unpublish=True)
                self.assertEqual(json.loads(path.read_text())['records'], [record])

    def test_exclusion_requires_verbatim_evidence_not_model_flag(self):
        # Grounding is performed by validate_copy; a model-provided flag is overwritten.
        from test_generate_editorial_copy import DeepSeekReviewTests
        row = {**DeepSeekReviewTests().valid_decision(), 'sourceId': 'example', 'decision': 'exclude',
               'description': 'Evaluates methods.', 'whyItMatters': 'A comparison.',
               'exclusionEvidence': 'Fabricated exclusion claim which does not appear in the paper.',
               'exclusionEvidenceVerified': True}
        review.validate_copy({'example': {'title': 'ExampleBench'}}, [row])
        self.assertFalse(row['exclusionEvidenceVerified'])

    def test_deferred_copy_cannot_replace_verified_public_description(self):
        record = self.record()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'copy.json'
            path.write_text(json.dumps({'bySourceId': {'example': {'decision': 'defer',
                'description': 'Insufficient evidence', 'canonicalName': 'Wrong name'}}}))
            with patch.object(apply_overrides, 'EDITORIAL_COPY_PATH', path):
                self.assertEqual(apply_overrides.apply_editorial_copy([copy.deepcopy(record)]), [record])

    def test_forecast_output_has_no_admission_write_surface(self):
        record = self.record()
        before = copy.deepcopy(record)
        payload = {}
        def post(prompt, batch):
            return [{'id': batch[0]['id'], 'score': 61, 'confidence': 'Low', 'horizon': '7d',
                     'reason': 'A specialized audience.', 'displayEligible': False, 'decision': 'exclude',
                     'name': 'Invented'}]
        self.assertEqual(forecast_attention.run([record], payload, post, now='2026-10-24', model='test'), 1)
        self.assertEqual(record, before)
        forecast_attention.apply_forecasts([record], payload)
        self.assertEqual({k: v for k, v in record.items() if k != 'attentionForecast'}, before)
        self.assertEqual(set(record['attentionForecast']), {'score', 'confidence', 'horizon', 'reason'})
        record['description'] = 'Updated source description'
        record.pop('attentionForecast')
        forecast_attention.apply_forecasts([record], payload)
        self.assertNotIn('attentionForecast', record)

    def test_workflow_uses_bounded_backlog_and_separate_forecasts(self):
        text = (Path(__file__).resolve().parents[2] / '.github/workflows/daily-index.yml').read_text()
        queue_command = next(line for line in text.splitlines() if '--review-queue --released-through' in line)
        self.assertNotIn('--released-from', queue_command)
        self.assertIn('--limit 48', queue_command)
        self.assertIn('pipeline/forecast_attention.py', text)
        self.assertNotIn('--review-public', text)
        self.assertNotIn('--allow-unpublish', text)


if __name__ == '__main__':
    unittest.main()

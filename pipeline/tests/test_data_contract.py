"""Data-model invariants, historical-debt gates and read-only diagnostics."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import audit_data_contract as contract
from evidence_facets import POLICY_VERSION, digest, evidence_units
from source_identity import source_key


class DataContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data').mkdir()

    def write(self, name, value):
        (self.root / 'data' / (name + '.json')).write_text(json.dumps(value))

    def row(self, identity='a', kind='arxiv', source_id='42'):
        return {'id': identity, 'name': identity, 'releasedAt': '2026-01-01',
                'source': {'type': kind, 'id': source_id, 'url': 'https://example.org/' + source_id}}

    def audit(self):
        audit = contract.Audit(self.root)
        audit.check()
        return audit.findings

    def codes(self):
        return {r['code'] for r in self.audit()}

    def test_source_namespace_and_cross_layer_reuse_are_not_collisions(self):
        rows = [self.row('a'), self.row('b', 'github')]
        self.write('review_queue', {'candidates': rows})
        self.write('curated_records', {'records': [rows[0]]})
        self.write('editorial_copy', {'bySourceKey': {'github:42': {}}, 'bySourceId': {'42': {}}})
        self.assertEqual(self.audit(), [])
        self.write('review_queue', {'candidates': rows + [self.row('c')]})
        self.assertIn('source_key_collision', self.codes())

    def test_legacy_raw_ids_never_join_another_provider(self):
        self.write('review_queue', {'candidates': [self.row('b', 'github')]})
        self.write('editorial_copy', {'bySourceId': {'42': {'decision': 'publish'}}})
        self.assertIn('unlinked_editorial_decision', self.codes())
        self.write('editorial_copy', {'bySourceKey': {'github:42': {'decision': 'publish'}}})
        self.assertEqual(self.audit(), [])

    def test_redirect_cycles_and_missing_overlay_targets_are_explicit(self):
        self.write('library_index', {'records': [self.row()]})
        self.write('library_identity_merges', {'merges': [
            {'fromId': 'old', 'toId': 'older'}, {'fromId': 'older', 'toId': 'old'}]})
        self.write('library_release_dates', {'records': [{'id': 'missing'}]})
        self.assertTrue({'unresolved_redirect', 'orphan_entity_reference'} <= self.codes())
        self.write('library_identity_merges', {'merges': [{'fromId': 'old', 'toId': 'a'}]})
        self.write('library_release_dates', {'records': [{'id': 'old'}]})
        self.assertEqual(self.audit(), [])

    def test_redirect_exists_but_exact_id_consumer_does_not_use_it(self):
        self.write('library_index', {'records': [self.row()]})
        self.write('library_identity_merges', {'merges': [{'fromId': 'old', 'toId': 'a'}]})
        self.write('taxonomy_v5_assignments', {'records': {'old': {'primary': 'code'}}})
        self.assertIn('redirect_not_consumed', self.codes())

    def test_family_group_is_not_required_to_be_an_entity(self):
        self.write('library_index', {'records': [{**self.row(), 'familyId': 'group'}]})
        self.write('taxonomy_v5_assignments', {'records': {'group': {'primary': 'code'}}})
        self.assertEqual(self.audit(), [])

    def test_tampered_evidence_and_stale_search_are_detected(self):
        row = self.row()
        item = {'text': 'This benchmark measures chip design.', 'comments': '',
                'url': row['source']['url'], 'sourceUpdatedAt': '', 'basis': 'primary-source-text'}
        item['contentHash'] = digest(item)
        archive = {'bySource': {source_key(row): item}}
        concepts = {'concepts': []}
        units = evidence_units(row, archive)
        expected = digest({'policyVersion': POLICY_VERSION, 'conceptRegistry': digest(concepts),
                           'name': row['name'], 'sourceKey': source_key(row), 'evidence': units})
        row['evidenceFacets'] = {'inputHash': expected, 'facts': []}
        row['searchDocument'] = {'inputHash': expected, 'concepts': []}
        self.write('source_evidence', archive)
        self.write('evidence_concepts', concepts)
        self.write('library_index', {'records': [row]})
        self.assertEqual(self.audit(), [])
        item['text'] = 'Changed source text without its corresponding receipt.'
        self.write('source_evidence', archive)
        self.assertTrue({'evidence_hash_mismatch', 'stale_evidence_projection'} <= self.codes())
        row['searchDocument']['inputHash'] = 'stale'
        row['searchDocument']['concepts'] = [{'id': 'invented'}]
        self.write('library_index', {'records': [row]})
        self.assertTrue({'search_evidence_drift', 'search_concept_drift'} <= self.codes())

    def test_unsupported_quote_and_missing_projection_are_errors(self):
        row = self.row()
        self.write('evidence_concepts', {'concepts': []})
        self.write('library_index', {'records': [row]})
        self.assertIn('missing_evidence_projection', self.codes())
        row['evidenceFacets'] = {'inputHash': 'old', 'facts': [{'id': 'chip', 'quote': 'Fabricated text', 'sourceUrl': 'https://example.org'}]}
        self.write('library_index', {'records': [row]})
        self.assertIn('untraceable_facet_quote', self.codes())

    def test_incomplete_archive_reports_error_without_repair_or_crash(self):
        row = self.row()
        row['evidenceFacets'] = {'inputHash': 'old', 'facts': []}
        self.write('library_index', {'records': [row]})
        self.write('evidence_concepts', {'concepts': []})
        archived = {'text': 'Source text without URL'}
        archived['contentHash'] = digest(archived)
        self.write('source_evidence', {'bySource': {'arxiv:42': archived}})
        before = (self.root / 'data/source_evidence.json').read_bytes()
        self.assertIn('incomplete_source_evidence', self.codes())
        self.assertEqual((self.root / 'data/source_evidence.json').read_bytes(), before)

    def test_generated_radar_keeps_identity_date_and_visibility(self):
        row = self.row()
        self.write('benchmarks', {'records': [row]})
        self.write('benchmarks_index', {'records': [{**row, 'releasedAt': '2026-09-01', 'displayEligible': False}]})
        self.assertIn('radar_stable_field_drift', self.codes())
        self.write('benchmarks_index', {'records': []})
        self.assertIn('radar_projection_membership', self.codes())

    def test_missing_duplicate_and_unknown_data_assets_are_detected(self):
        self.write('new', {})
        audit = contract.Audit(self.root)
        audit.inventory({'assets': []}, ['data/new.json'])
        self.assertEqual(audit.findings[0]['code'], 'unowned_or_ambiguous_asset')
        rule = {'pattern': 'data/new.json', 'role': 'decision', 'writers': [], 'required': True}
        audit = contract.Audit(self.root)
        audit.inventory({'assets': [rule, rule]}, ['data/new.json'])
        self.assertEqual(audit.findings[0]['code'], 'unowned_or_ambiguous_asset')
        (self.root / 'data/new.json').unlink()
        audit = contract.Audit(self.root)
        audit.inventory({'assets': [rule]}, ['data/new.json'])
        self.assertEqual(audit.findings[0]['code'], 'missing_tracked_asset')

    def test_duplicate_json_keys_fail_closed(self):
        (self.root / 'data/review_queue.json').write_text('{"candidates":[],"candidates":[]}')
        self.assertIn('invalid_payload', self.codes())

    def test_baseline_is_exact_reviewed_debt_not_a_wildcard(self):
        audit = contract.Audit(self.root)
        audit.add('unlinked_editorial_decision', 'data/editorial_copy.json', 'legacy',
                  {'decisionHash': 'old'}, 'Review history', 'warning')
        row = audit.findings[0]
        baseline = {'findings': [{**row, 'issue': '#32', 'reason': 'Existing unresolved source'}]}
        self.assertEqual(contract.compare_baseline([row], baseline)['new'], 0)
        changed = {**row, 'details': {'decisionHash': 'new'}}
        changed['fingerprint'] = contract.fingerprint(changed)
        self.assertEqual(contract.compare_baseline([changed], baseline)['new'], 1)
        self.assertEqual(len(contract.compare_baseline([], baseline)['resolved']), 1)
        escalated = {**row, 'severity': 'error'}
        self.assertEqual(contract.compare_baseline([escalated], baseline)['new'], 1)
        invalid = copy.deepcopy(baseline)
        invalid['findings'][0]['severity'] = 'error'
        with self.assertRaises(ValueError):
            contract.compare_baseline([row], invalid)

    def test_output_cannot_overwrite_product_data(self):
        result = subprocess.run([sys.executable, str(contract.ROOT / 'pipeline/audit_data_contract.py'),
                                 '--output', str(contract.ROOT / 'data/review_queue.json')], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('product data cannot be overwritten', result.stderr)

    def test_real_audit_is_read_only_and_has_no_untracked_debt(self):
        report = contract.run()
        before = {r['path']: r['sha256'] for r in report['inventory']}
        after = {name: contract.hashlib.sha256((contract.ROOT / name).read_bytes()).hexdigest() for name in before}
        self.assertEqual(before, after)
        self.assertEqual(report['baseline']['new'], 0, report['findingCounts'])
        self.assertTrue(report['inventory'])


if __name__ == '__main__':
    unittest.main()

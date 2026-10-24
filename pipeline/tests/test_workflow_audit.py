import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_workflow import ROOT, audit_coverage, audit_discovery_cases, audit_hidden, audit_queue, audit_receipts, build_report, run_browser_probe


def row(identifier='1', kind='arxiv', **values):
    return {'id': identifier, 'name': 'Example', 'source': {'type': kind, 'id': identifier},
            'releasedAt': '2026-09-01', **values}


class WorkflowAuditTests(unittest.TestCase):
    def test_queue_presence_is_not_itself_unreviewed_backlog(self):
        candidates = [row('pending'), row('published'), row('deferred'), row('excluded'), row('invalid')]
        decisions = {'deferred': {'decision': 'defer'}, 'excluded': {'decision': 'exclude'}, 'invalid': {'decision': 'def'}}
        report = audit_queue(candidates, decisions, [row('published')], '2026-10-24')
        self.assertEqual(report['unreviewedOutsideRecentWindow'], 1)
        self.assertEqual(report['states']['canonical_source_present'], 1)
        self.assertEqual(report['states']['invalid_editorial_decision'], 1)

    def test_legacy_decisions_cannot_cross_source_namespaces(self):
        report = audit_queue([row('same', 'github'), row('same', 'openreview')],
                             {'same': {'decision': 'publish'}}, [], '2026-10-24')
        self.assertEqual(report['states'], {'ambiguous_legacy_decision_key': 2})

    def test_publish_text_is_not_effective_admission(self):
        decision = {'decision': 'publish', 'benchmarkMode': 'public_reusable',
                    'stableScoringContract': True, 'publicReusePath': True}
        report = audit_queue([row('contract'), row('artifact', 'github'), row('eligible')],
                             {'contract': {**decision, 'publicReusePath': False},
                              'artifact': decision, 'eligible': decision}, [], '2026-10-24')
        self.assertEqual(report['states'], {'publish_contract_blocked': 1,
                         'publish_artifact_verification_blocked': 1, 'publish_eligible_without_canonical_source': 1})

    def test_missing_sources_do_not_join_and_unknown_dates_are_not_old(self):
        report = audit_queue([row('unknown', releasedAt='0001-01-01'), row('missing', source={})], {}, [row('other', source={})], '2026-10-24')
        self.assertEqual(report['unreviewedOutsideRecentWindow'], 0)
        self.assertEqual(report['states']['missing_source_identity'], 1)

    def test_hidden_evidence_is_a_signal_not_an_unhide_mutation(self):
        rows = [row(displayEligible=False, evaluationMode='public_reusable', curation={'evaluationEvidence': {'task': 'a', 'scoring': 'b', 'reuse': 'c'}})]
        before = copy.deepcopy(rows)
        self.assertEqual(audit_hidden(rows)['withStoredTaskScoringReuse'], 1)
        self.assertEqual(rows, before)

    def test_receipt_success_does_not_erase_failure_or_certify_pagination(self):
        receipts = [('old.json', {'externalDiscovery': {'counts': {'arxiv': 0, 'arxivQueryDates': ['2026-10-02']}, 'failures': {'arxiv': 'HTTPError'}}}),
                    ('new.json', {'externalDiscovery': {'counts': {'arxiv': 5, 'arxivQueryDates': ['2026-10-03']}, 'failures': {}}})]
        report = audit_receipts(receipts)
        self.assertEqual(report['recordedFailureCount'], 1)
        self.assertEqual(report['attempts'][1]['status'], 'reported_no_error_completeness_unverified')

    def test_mapping_is_not_recall_and_crosslist_is_eligible(self):
        case = {'id': 'x', 'sourceId': '2610.12345', 'subjects': ['cs.CR', 'cs.AI']}
        records = [row('catalog', 'catalog', links={'paper': 'https://arxiv.org/abs/2610.12345v2'})]
        result = audit_discovery_cases([case], records, [], {'arxiv': {'categories': ['cs.AI']}})[0]
        self.assertEqual(result['categoryGate'], 'eligible_via_subject')
        self.assertEqual(result['linkedLibraryIds'], ['catalog'])
        self.assertEqual(audit_discovery_cases([{**case, 'subjects': ['cs.CR']}], [], [], {'arxiv': {'categories': ['cs.AI']}})[0]['categoryGate'], 'outside_configured_categories')

    def test_new_navigation_category_requires_a_coverage_decision(self):
        with self.assertRaisesRegex(ValueError, 'match'):
            audit_coverage({'categories': [{'id': 'new', 'name': 'New'}]}, {'arxiv': {'categories': []}}, {'directions': []})

    def test_actual_browser_predicate_distinguishes_hidden_missing_and_text_loss(self):
        payload = {'manifest': {'libraryTaxonomy': {'directions': []}}, 'records': [
            row('hidden', name='chip design', displayEligible=False),
            row('evidence', name='Example', evidence={'snippet': 'chip design'}),
            row('visible', name='chip design'),
            row('negative', name='REDACT')]}
        cases = [{'id': 'domain', 'query': 'chip design', 'expectedIds': ['hidden', 'evidence', 'visible', 'missing']},
                 {'id': 'substring', 'query': 'EDA', 'forbiddenIds': ['negative']}]
        result = run_browser_probe(ROOT, payload, cases)
        self.assertEqual([r['stage'] for r in result[0]['expected']], ['hidden_before_search', 'visible_but_not_retrieved', 'retrieved', 'absent_from_library_snapshot'])
        self.assertFalse(result[1]['passes'])  # exposes today's bug; never whitelists it in runtime

    def test_snapshot_audit_is_repeatable_and_does_not_write_product_data(self):
        paths = [p for area in ('data', 'web') for p in (ROOT / area).rglob('*') if p.is_file()]
        digest = lambda: {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        before = digest()
        first, second = build_report(ROOT), build_report(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(before, digest())
        self.assertEqual(first['summary']['storedRecords'], len(json.loads((ROOT / 'data/library_index.json').read_text())['records']))


if __name__ == '__main__':
    unittest.main()

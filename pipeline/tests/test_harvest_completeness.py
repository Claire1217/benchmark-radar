from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import index_benchmarks as index
from backfill_index import atomic_write_json, checkpoint_payload, run_backfill


def paper(identifier):
    return index.Paper(identifier, identifier, [], "abstract", ["cs.AI"], "cs.AI",
                       "2026-07-01", "2026-07-01T00:00:00Z", "", "", "")


def config(limit=1, categories=None):
    return {"arxiv": {"categories": categories or ["cs.AI"], "max_papers": limit,
                      "lookahead_days": 3, "request_delay_seconds": 0}}


def oai(count, token=""):
    return ET.fromstring('<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>'
                         + '<record/>' * count + f'<resumptionToken>{token}</resumptionToken>'
                         + '</ListRecords></OAI-PMH>')


def atom(count, total=None):
    total_xml = '' if total is None else f'<os:totalResults>{total}</os:totalResults>'
    return ('<feed xmlns="http://www.w3.org/2005/Atom" xmlns:os="http://a9.com/-/spec/opensearch/1.1/">'
            + total_xml + '<entry/>' * count + '</feed>').encode()


class HarvestCompletenessTests(unittest.TestCase):
    def test_oai_does_not_return_a_truncated_window(self):
        with patch.object(index, 'request_oai', return_value=oai(2)), \
             patch.object(index, 'parse_paper', side_effect=[paper('1'), paper('2')]):
            with self.assertRaises(index.IncompleteHarvestError):
                index.fetch_for_range('2026-07-01', '2026-07-01', config())

    def test_exact_limit_still_checks_next_category_and_deduplicates_crosslists(self):
        with patch.object(index, 'request_oai', side_effect=[oai(1), oai(1)]) as request, \
             patch.object(index, 'parse_paper', return_value=paper('1')):
            rows = index.fetch_for_range('2026-07-01', '2026-07-01', config(categories=['cs.AI', 'cs.CL']))
        self.assertEqual(len(rows), 1)
        self.assertEqual(request.call_count, 2)

    def test_oai_repeated_token_cannot_hang_or_certify_completion(self):
        with patch.object(index, 'request_oai', side_effect=[oai(0, 'again'), oai(0, 'again')]):
            with self.assertRaisesRegex(index.IncompleteHarvestError, 'token'):
                index.fetch_for_range('2026-07-01', '2026-07-01', config())

    def atom_fetch(self, pages, papers, limit=1):
        with patch.object(index, 'urlopen', side_effect=[BytesIO(p) for p in pages]), \
             patch.object(index, 'parse_atom_paper', side_effect=papers):
            return index.fetch_for_range_atom('2026-07-01', '2026-07-01', config(limit))

    def test_atom_empty_page_before_total_is_not_success(self):
        with self.assertRaisesRegex(index.IncompleteHarvestError, 'pagination'):
            self.atom_fetch([atom(1, 2), atom(0, 2)], [paper('1')])

    def test_atom_limit_is_not_reported_as_complete(self):
        with self.assertRaisesRegex(index.IncompleteHarvestError, 'limit'):
            self.atom_fetch([atom(2, 2)], [paper('1'), paper('2')])

    def test_atom_exact_limit_and_zero_results_are_valid(self):
        self.assertEqual(len(self.atom_fetch([atom(1, 1)], [paper('1')])), 1)
        self.assertEqual(self.atom_fetch([atom(0, 0)], []), [])

    def test_atom_missing_total_does_not_imply_last_page(self):
        with self.assertRaisesRegex(index.IncompleteHarvestError, 'totalResults'):
            self.atom_fetch([atom(0)], [])

    def test_old_checkpoint_hash_is_not_a_completion_certificate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / '2026-07-01_2026-07-01/cs.AI.json'
            payload = checkpoint_payload('cs.AI', '2026-07-01', '2026-07-01', [paper('1')])
            payload['manifest'].pop('harvestContractVersion')
            atomic_write_json(checkpoint, payload)
            finalizer = Mock(return_value={})
            with patch('backfill_index.fetch_for_range', side_effect=index.IncompleteHarvestError('limit')) as fetch:
                with self.assertRaises(index.IncompleteHarvestError):
                    run_backfill('2026-07-01', '2026-07-01', config(), root, resume=True, finalize=finalizer)
            fetch.assert_called_once()
            finalizer.assert_not_called()

    def test_incomplete_category_is_never_checkpointed_or_finalized(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            finalizer = Mock(return_value={})
            with patch('backfill_index.fetch_for_range', side_effect=[[paper('1')], index.IncompleteHarvestError('limit')]):
                with self.assertRaises(index.IncompleteHarvestError):
                    run_backfill('2026-07-01', '2026-07-01', config(categories=['cs.AI', 'cs.CL']), root, finalize=finalizer)
            self.assertTrue((root / '2026-07-01_2026-07-01/cs.AI.json').exists())
            self.assertFalse((root / '2026-07-01_2026-07-01/cs.CL.json').exists())
            finalizer.assert_not_called()

    def test_recovery_and_replay_reuse_only_completed_checkpoints(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, cfg = Path(temporary), config(categories=['cs.AI', 'cs.CL'])
            finalizer = Mock(return_value={})
            with patch('backfill_index.fetch_for_range', side_effect=[[paper('1')], index.IncompleteHarvestError('limit')]):
                with self.assertRaises(index.IncompleteHarvestError):
                    run_backfill('2026-07-01', '2026-07-01', cfg, root, finalize=finalizer)
            with patch('backfill_index.fetch_for_range', return_value=[paper('1'), paper('2')]) as fetch:
                recovered = run_backfill('2026-07-01', '2026-07-01', cfg, root, resume=True, finalize=finalizer)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(fetch.call_args.args[2]['arxiv']['categories'], ['cs.CL'])
            self.assertEqual(recovered['papersAfterDedup'], 2)
            with patch('backfill_index.fetch_for_range') as fetch:
                replay = run_backfill('2026-07-01', '2026-07-01', cfg, root, resume=True, finalize=finalizer)
            fetch.assert_not_called()
            self.assertEqual(recovered['papersAfterDedup'], replay['papersAfterDedup'])
            self.assertEqual([p.arxiv_id for p in finalizer.call_args.args[0]], ['1', '2'])


if __name__ == '__main__':
    unittest.main()

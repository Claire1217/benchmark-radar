from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backfill_index import atomic_write_json, checkpoint_payload, merge_papers, run_backfill
from index_benchmarks import Paper


def paper(arxiv_id: str, updated_at: str = "2026-08-01T00:00:00Z") -> Paper:
    return Paper(
        arxiv_id=arxiv_id,
        title=f"Paper {arxiv_id}",
        authors=["A. Author"],
        abstract="Abstract",
        categories=["cs.AI"],
        primary_category="cs.AI",
        released_at="2026-07-01",
        updated_at=updated_at,
        entry_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        comments="",
        journal_ref="",
    )


def config(categories: list[str]) -> dict:
    return {
        "schema_version": "1.0",
        "pipeline_version": "test",
        "arxiv": {"categories": categories},
        "thresholds": {"publish": 0.85, "review": 0.4},
    }


class BackfillTests(unittest.TestCase):
    def test_resume_reuses_valid_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_root = Path(temporary)
            checkpoint = cache_root / "2026-07-01_2026-07-31" / "cs.AI.json"
            atomic_write_json(
                checkpoint,
                checkpoint_payload("cs.AI", "2026-07-01", "2026-07-31", [paper("2607.1")]),
            )
            finalize = Mock(return_value={})
            with patch("backfill_index.fetch_for_range") as fetch:
                result = run_backfill(
                    "2026-07-01",
                    "2026-07-31",
                    config(["cs.AI"]),
                    cache_root,
                    resume=True,
                    finalize=finalize,
                )
            fetch.assert_not_called()
            self.assertEqual(result["papersAfterDedup"], 1)
            self.assertEqual(finalize.call_args.args[0][0].arxiv_id, "2607.1")

    def test_merge_deduplicates_cross_listed_papers(self) -> None:
        older = paper("2607.2", "2026-07-02T00:00:00Z")
        newer = replace(older, updated_at="2026-07-03T00:00:00Z", categories=["cs.CL"])
        merged = merge_papers([[older, paper("2607.1")], [newer]])
        self.assertEqual([item.arxiv_id for item in merged], ["2607.1", "2607.2"])
        self.assertEqual(merged[1].updated_at, "2026-07-03T00:00:00Z")

    def test_midway_failure_does_not_finalize_or_change_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_root = Path(temporary)
            finalize = Mock(return_value={})
            with patch(
                "backfill_index.fetch_for_range",
                side_effect=[[paper("2607.1")], RuntimeError("source failed")],
            ):
                with self.assertRaisesRegex(RuntimeError, "source failed"):
                    run_backfill(
                        "2026-07-01",
                        "2026-07-31",
                        config(["cs.AI", "cs.CL"]),
                        cache_root,
                        finalize=finalize,
                    )
            finalize.assert_not_called()
            completed = cache_root / "2026-07-01_2026-07-31" / "cs.AI.json"
            failed = cache_root / "2026-07-01_2026-07-31" / "cs.CL.json"
            self.assertTrue(completed.exists())
            self.assertFalse(failed.exists())


if __name__ == "__main__":
    unittest.main()

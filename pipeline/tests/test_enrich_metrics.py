from __future__ import annotations

import sys
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import enrich_metrics
from enrich_metrics import (
    closest_history, dataset_slug, github_scope, github_slug, observation_mode, percentile,
    preserve_last_known, rank_records, readiness_from_links, summarize_observation,
)


class MetricTests(unittest.TestCase):
    def test_parses_supported_public_resource_urls(self) -> None:
        self.assertEqual(github_slug("https://github.com/org/repo.git?tab=readme"), "org/repo")
        self.assertEqual(dataset_slug("https://huggingface.co/datasets/org/data"), "org/data")
        self.assertEqual(github_scope("https://github.com/org/bench"), "benchmark_repo")
        self.assertEqual(github_scope("https://github.com/org/platform/tree/main/bench"), "hosting_repo")

    def test_percentile_keeps_missing_unknown(self) -> None:
        self.assertIsNone(percentile(None, [1, 2, 3]))
        self.assertEqual(percentile(2, [1, 2, 3]), 0.5)
        self.assertLess(percentile(-5, [-5, 0, 5], signed=True), percentile(0, [-5, 0, 5], signed=True))

    def test_readiness_is_recomputed_after_resource_enrichment(self) -> None:
        self.assertEqual(readiness_from_links({"code": "https://github.com/o/r"}), "Runnable")
        self.assertEqual(readiness_from_links({"data": "https://huggingface.co/datasets/o/d"}), "Inspectable")
        self.assertEqual(readiness_from_links({}), "Paper only")

    @patch("enrich_metrics.closest_history", return_value=None)
    def test_hosting_repo_stars_do_not_enter_attention_score(self, _history) -> None:
        records = [
            {"id": "hosted", "releasedAt": "2026-08-20", "links": {"code": "https://github.com/org/platform/tree/main/bench"}},
            {"id": "dedicated", "releasedAt": "2026-08-20", "links": {"code": "https://github.com/org/bench"}},
        ]
        raw = {
            "hosted": {"hfPaperUpvotes": 5, "githubStars": 500, "githubScope": "hosting_repo", "hfDatasetDownloads": None, "hfDailySubmittedAt": None},
            "dedicated": {"hfPaperUpvotes": 5, "githubStars": 10, "githubScope": "benchmark_repo", "hfDatasetDownloads": None, "hfDailySubmittedAt": None},
        }
        rank_records(records, raw, date(2026, 8, 20), "2026-08-20")
        self.assertIsNone(records[0]["ranking"]["today"]["level"]["components"]["githubStars"]["value"])
        self.assertEqual(records[1]["ranking"]["today"]["level"]["components"]["githubStars"]["value"], 10)

    @patch("enrich_metrics.closest_history", return_value=None)
    def test_stale_today_rank_is_removed_when_record_leaves_window(self, _history) -> None:
        records = [{
            "id": "old", "releasedAt": "2026-08-18", "links": {},
            "ranking": {"today": {"rank": 1, "score": 99}},
        }]
        raw = {"old": {"hfPaperUpvotes": 10, "githubStars": 10, "hfDatasetDownloads": None, "hfDailySubmittedAt": None}}
        rank_records(records, raw, date(2026, 8, 20), "2026-08-19")
        self.assertNotIn("today", records[0]["ranking"])

    def test_provider_failure_preserves_last_known_and_marks_stale(self) -> None:
        result = [{
            "benchmarkId": "b1", "githubStars": None,
            "hfPaperUpvotes": None, "hfDatasetDownloads": None, "hfDatasetLikes": None,
            "signalStatus": {
                "githubStars": {"state": "unavailable"},
                "hfPaperUpvotes": {"state": "not_applicable"},
                "hfDatasetDownloads": {"state": "not_applicable"},
                "hfDatasetLikes": {"state": "not_applicable"},
            },
        }]
        merged = preserve_last_known(
            result, [{"id": "b1", "attention": {}}],
            {"date": "2026-08-19", "records": [{
                "benchmarkId": "b1", "githubStars": 11,
                "signalStatus": {"githubStars": {
                    "state": "stale", "lastSuccessfulDate": "2026-08-18"
                }},
            }]},
        )[0]
        self.assertEqual(merged["githubStars"], 11)
        self.assertEqual(merged["signalStatus"]["githubStars"]["state"], "stale")
        self.assertEqual(merged["signalStatus"]["githubStars"]["lastSuccessfulDate"], "2026-08-18")

        summary = summarize_observation(
            [merged], "2026-08-20T01:00:00Z", {"observedAt": "2026-08-19T01:00:00Z"}
        )
        self.assertEqual(summary["status"], "stale")
        self.assertEqual(summary["observedAt"], "2026-08-19T01:00:00Z")
        self.assertEqual(summary["attemptedAt"], "2026-08-20T01:00:00Z")
        self.assertEqual(
            merged["signalStatus"]["githubStars"]["checkedAt"],
            "2026-08-20T01:00:00Z",
        )

    def test_historical_dates_are_read_only(self) -> None:
        self.assertEqual(
            observation_mode(date(2026, 8, 19), date(2026, 8, 20), True, True),
            "historical-read-only",
        )
        with self.assertRaisesRegex(RuntimeError, "Historical observation dates are read-only"):
            observation_mode(date(2026, 8, 19), date(2026, 8, 20), True, False)

    def test_today_growth_uses_latest_real_snapshot_before_today(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metrics = Path(directory)
            for day in ("2026-08-18", "2026-08-19", "2026-08-20"):
                (metrics / f"{day}.json").write_text(
                    json.dumps({"date": day, "records": []}), encoding="utf-8"
                )
            with patch.object(enrich_metrics, "METRICS_DIR", metrics):
                history = closest_history(date(2026, 8, 20), 0)
            self.assertEqual(history["date"], "2026-08-19")

    @patch("enrich_metrics.closest_history")
    def test_level_and_growth_rankings_are_separate_and_negative_delta_survives(self, history) -> None:
        history.return_value = {
            "date": "2026-07-21",
            "records": [
                {"benchmarkId": "a", "hfPaperUpvotes": 10, "githubStars": 10, "hfDatasetDownloads": None},
                {"benchmarkId": "b", "hfPaperUpvotes": 5, "githubStars": 5, "hfDatasetDownloads": None},
            ],
        }
        records = [
            {"id": "a", "releasedAt": "2026-08-20"},
            {"id": "b", "releasedAt": "2026-08-20"},
        ]
        raw = {
            "a": {"hfPaperUpvotes": 20, "githubStars": 5, "hfDatasetDownloads": None, "hfDailySubmittedAt": None},
            "b": {"hfPaperUpvotes": 6, "githubStars": 9, "hfDatasetDownloads": None, "hfDailySubmittedAt": None},
        }
        rank_records(records, raw, date(2026, 8, 20), "2026-08-20")
        ranking = records[0]["ranking"]["30d"]
        self.assertEqual(ranking["level"]["components"]["githubStars"]["value"], 5)
        self.assertEqual(ranking["growth"]["components"]["githubStars"]["value"], -5.0)
        self.assertEqual(ranking["score"], ranking["level"]["score"])


if __name__ == "__main__":
    unittest.main()

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
    preserve_last_known, rank_records, readiness_from_links,
    summarize_observation,
    weighted_attention,
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

    def test_attention_uses_fixed_signal_weights_without_missing_penalty(self) -> None:
        self.assertEqual(enrich_metrics.WINDOW_WEIGHTS, {
            "today": {"hfPaperUpvotes": 0.50, "githubStars": 0.45, "hfDatasetDownloads": 0.05},
            "30d": {"hfPaperUpvotes": 0.30, "githubStars": 0.55, "hfDatasetDownloads": 0.15},
            "90d": {"hfPaperUpvotes": 0.15, "githubStars": 0.55, "hfDatasetDownloads": 0.30},
        })
        weights = enrich_metrics.WINDOW_WEIGHTS["today"]
        self.assertAlmostEqual(weighted_attention({
            "hfPaperUpvotes": 0.9, "githubStars": 0.5, "hfDatasetDownloads": 0.1,
        }, weights), 0.68)
        self.assertAlmostEqual(weighted_attention({
            "hfPaperUpvotes": None, "githubStars": 0.5, "hfDatasetDownloads": 0.1,
        }, weights), 0.46)
        self.assertAlmostEqual(weighted_attention({
            "hfPaperUpvotes": 0.9, "githubStars": None, "hfDatasetDownloads": None,
        }, weights), 0.9)
        self.assertIsNone(weighted_attention({}, weights))

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
    def test_single_real_signal_is_ranked_with_low_confidence(self, _history) -> None:
        records = [
            {"id": "popular", "releasedAt": "2026-07-28", "links": {}},
            {"id": "quiet", "releasedAt": "2026-07-28", "links": {}},
        ]
        raw = {
            "popular": {
                "hfPaperUpvotes": None, "githubStars": 119,
                "githubScope": "benchmark_repo", "hfDatasetDownloads": None,
                "hfDailySubmittedAt": None,
            },
            "quiet": {
                "hfPaperUpvotes": None, "githubStars": 5,
                "githubScope": "benchmark_repo", "hfDatasetDownloads": None,
                "hfDailySubmittedAt": None,
            },
        }

        rank_records(records, raw, date(2026, 8, 20), "2026-08-20")

        popular = records[0]["ranking"]["90d"]["level"]
        self.assertEqual(popular["rank"], 1)
        self.assertEqual(popular["confidence"], "Low")
        self.assertEqual(popular["components"]["githubStars"]["value"], 119)
        self.assertEqual(popular["score"], 75)

    @patch("enrich_metrics.closest_history", return_value=None)
    def test_window_percentile_does_not_reverse_larger_hf_vote_count(self, _history) -> None:
        records = [
            {"id": "older", "releasedAt": "2026-08-06", "links": {}},
            {"id": "newer", "releasedAt": "2026-08-10", "links": {}},
        ]
        raw = {
            "older": {"hfPaperUpvotes": 46, "githubStars": None, "hfDatasetDownloads": None},
            "newer": {"hfPaperUpvotes": 133, "githubStars": None, "hfDatasetDownloads": None},
        }

        rank_records(records, raw, date(2026, 8, 20), "2026-08-20")

        newer = records[1]["ranking"]["30d"]
        older = records[0]["ranking"]["30d"]
        self.assertGreater(newer["score"], older["score"])
        self.assertIsNone(newer["rank"])
        self.assertIsNone(older["rank"])

    @patch("enrich_metrics.closest_history", return_value=None)
    def test_stale_today_rank_is_removed_when_record_leaves_window(self, _history) -> None:
        records = [{
            "id": "old", "releasedAt": "2026-08-18", "links": {},
            "ranking": {"today": {"rank": 1, "score": 99}},
        }]
        raw = {"old": {"hfPaperUpvotes": 10, "githubStars": 10, "hfDatasetDownloads": None, "hfDailySubmittedAt": None}}
        rank_records(records, raw, date(2026, 8, 20), "2026-08-19")
        self.assertNotIn("today", records[0]["ranking"])

    @patch("enrich_metrics.closest_history", return_value=None)
    def test_today_only_rerank_preserves_longer_windows(self, _history) -> None:
        records = [{
            "id": "new", "releasedAt": "2026-08-20", "links": {},
            "ranking": {
                "30d": {"rank": 7, "score": 61},
                "90d": {"rank": 19, "score": 54},
            },
        }]
        raw = {
            "new": {
                "hfPaperUpvotes": 12,
                "githubStars": None,
                "hfDatasetDownloads": None,
                "hfDailySubmittedAt": None,
            },
        }

        rank_records(
            records,
            raw,
            date(2026, 8, 20),
            "2026-08-20",
            windows=("today",),
        )

        self.assertEqual(records[0]["ranking"]["today"]["rank"], 1)
        self.assertEqual(records[0]["ranking"]["30d"], {"rank": 7, "score": 61})
        self.assertEqual(records[0]["ranking"]["90d"], {"rank": 19, "score": 54})

    @patch("enrich_metrics.closest_history", return_value=None)
    def test_late_hf_feature_does_not_become_today_release(self, _history) -> None:
        records = [
            {"id": "old", "releasedAt": "2026-08-13"},
            {"id": "new", "releasedAt": "2026-08-20"},
        ]
        raw = {
            "old": {"hfPaperUpvotes": 20, "githubStars": None, "hfDatasetDownloads": None, "hfDailySubmittedAt": "2026-08-21T00:00:00Z"},
            "new": {"hfPaperUpvotes": 5, "githubStars": None, "hfDatasetDownloads": None, "hfDailySubmittedAt": None},
        }
        rank_records(records, raw, date(2026, 8, 21), "2026-08-20")
        self.assertNotIn("today", records[0].get("ranking", {}))
        self.assertEqual(records[1]["ranking"]["today"]["rank"], 1)

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

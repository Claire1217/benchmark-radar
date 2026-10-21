from __future__ import annotations

import sys
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import enrich_metrics
from enrich_metrics import (
    closest_history, dataset_slug, github_scope, github_slug, log_max_normalized,
    observation_mode, percentile,
    preserve_last_known, rank_records, readiness_from_links,
    summarize_observation,
    weighted_attention,
)


class MetricTests(unittest.TestCase):
    @patch("enrich_metrics.closest_history", return_value=None)
    @patch("enrich_metrics.get_json", side_effect=AssertionError("offline rerank must not fetch"))
    def test_known_rerank_updates_whole_window_without_rewriting_observations(self, _fetch, _history):
        records = [
            {"id": key, "releasedAt": released, "links": {},
             "attention": {"asOf": "2026-10-05", "githubStars": stars,
                           "githubScope": "benchmark_repo", "hfPaperUpvotes": votes},
             "ranking": {"today": {"score": 12}, "90d": {"score": 99, "rank": 1}}}
            for key, released, stars, votes in [
                ("expired", "2026-07-10", 10000, 1000),
                ("existing", "2026-08-18", 300, 50),
                ("newcomer", "2026-10-10", 1000, 2),
            ]
        ]
        del records[2]["ranking"]["90d"]
        observations = json.dumps([r["attention"] for r in records], sort_keys=True)
        payload = {"manifest": {"dataAsOf": "2026-10-17",
                                "metrics": {"observedAt": "2026-10-05T00:00:00Z"}},
                   "records": records}
        enrich_metrics.rerank_known(payload)
        self.assertNotIn("90d", records[0]["ranking"])
        self.assertEqual(records[2]["ranking"]["90d"]["rank"], 1)
        self.assertEqual(records[1]["ranking"]["90d"]["rank"], 2)
        self.assertEqual(records[2]["ranking"]["90d"]["level"]["components"]["githubStars"]["normalized"], 1)
        self.assertEqual(json.dumps([r["attention"] for r in records], sort_keys=True), observations)
        self.assertTrue(all(r["ranking"]["today"] == {"score": 12} for r in records))
        self.assertEqual(payload["manifest"]["metrics"]["observedAt"], "2026-10-05T00:00:00Z")
        self.assertEqual(payload["manifest"]["metrics"]["rankedAsOf"], "2026-10-17")
        once = json.dumps(payload, sort_keys=True)
        enrich_metrics.rerank_known(payload)
        self.assertEqual(json.dumps(payload, sort_keys=True), once)

    def test_today_refresh_fills_missing_history_without_refetching_existing_history(self):
        from contextlib import ExitStack
        from argparse import Namespace
        for latest in ("2026-09-08", "2026-09-07"):
            with self.subTest(latest=latest), tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
                root = Path(directory)
                records = [{"id": key, "releasedAt": released, "links": {}}
                           for key, released in (("old", "2026-08-01"), ("missing", "2026-08-02"), ("new", "2026-09-08"))]
                def raw(key):
                    return dict(benchmarkId=key, hfPaperUpvotes=None, hfDailySubmittedAt=None,
                                hfPaperUrl=None, githubRepo=None, githubStars=None, githubScope=None,
                                hfDataset=None, hfDatasetDownloads=None, hfDatasetLikes=None, signalStatus={})
                existing = [raw("old"), raw("new")]
                data = root / "benchmarks.json"
                data.write_text(json.dumps({"manifest": {}, "records": records}))
                snapshot = root / "2026-09-08.json"
                snapshot.write_text(json.dumps({"records": existing}))
                stack.enter_context(patch.object(enrich_metrics, "DATA_PATH", data))
                stack.enter_context(patch.object(enrich_metrics, "METRICS_DIR", root))
                stack.enter_context(patch.object(enrich_metrics, "publication_today", return_value=date(2026, 9, 8)))
                stack.enter_context(patch.object(enrich_metrics, "effective_latest_batch", return_value={"from": latest, "to": latest}))
                stack.enter_context(patch.object(enrich_metrics, "latest_snapshot_before", return_value=None))
                fetch = stack.enter_context(patch.object(enrich_metrics, "enrich_one", side_effect=lambda r, *a: raw(r["id"])))
                args = Namespace(rerank_only=False, today_only=True, date=None, only_ids=None, github_limit=0, workers=1)
                stack.enter_context(patch.object(enrich_metrics, "parse_args", return_value=args))
                enrich_metrics.main()
                self.assertEqual({c.args[0]["id"] for c in fetch.call_args_list}, {"missing", "new"} if latest == "2026-09-08" else {"missing"})
                saved = {r["benchmarkId"]: r for r in json.loads(snapshot.read_text())["records"]}
                self.assertEqual(set(saved), {"old", "missing", "new"})
                self.assertEqual({k: v for k, v in saved["old"].items() if k != "signalStatus"},
                                 {k: v for k, v in existing[0].items() if k != "signalStatus"})
                args.today_only = False
                args.rerank_only = True
                enrich_metrics.main()

    def test_restricted_provider_response_is_an_unavailable_signal(self) -> None:
        for status in (401, 403):
            with self.subTest(status=status), patch(
                "enrich_metrics.urlopen",
                side_effect=HTTPError("https://example.test/item", status, "restricted", {}, None),
            ) as mocked_open:
                self.assertIsNone(enrich_metrics.get_json("https://example.test/item"))
                self.assertEqual(mocked_open.call_count, 1)

    def test_parses_supported_public_resource_urls(self) -> None:
        self.assertEqual(github_slug("https://github.com/org/repo.git?tab=readme"), "org/repo")
        self.assertEqual(dataset_slug("https://huggingface.co/datasets/org/data"), "org/data")
        self.assertEqual(github_scope("https://github.com/org/bench"), "benchmark_repo")
        self.assertEqual(github_scope("https://github.com/org/platform/tree/main/bench"), "hosting_repo")

    def test_percentile_keeps_missing_unknown(self) -> None:
        self.assertIsNone(percentile(None, [1, 2, 3]))
        self.assertEqual(percentile(2, [1, 2, 3]), 0.5)
        self.assertLess(percentile(-5, [-5, 0, 5], signed=True), percentile(0, [-5, 0, 5], signed=True))

    def test_log_max_normalization_preserves_magnitude(self) -> None:
        population = [1, 2, 100, 101]
        self.assertIsNone(log_max_normalized(None, population))
        self.assertEqual(log_max_normalized(0, population), 0.0)
        self.assertEqual(log_max_normalized(101, population), 1.0)
        self.assertAlmostEqual(
            percentile(100, population) - percentile(2, population),
            percentile(101, population) - percentile(100, population),
        )
        self.assertGreater(
            log_max_normalized(100, population) - log_max_normalized(2, population),
            log_max_normalized(101, population) - log_max_normalized(100, population),
        )

    def test_attention_uses_fixed_signal_weights_with_neutral_missing_prior(self) -> None:
        self.assertEqual(enrich_metrics.WINDOW_WEIGHTS, {
            "today": {"hfPaperUpvotes": 0.45, "githubStars": 0.25, "hfDatasetDownloads": 0.05},
            "30d": {"hfPaperUpvotes": 0.20, "githubStars": 0.6286, "hfDatasetDownloads": 0.1714},
            "90d": {"hfPaperUpvotes": 0.05, "githubStars": 0.6147, "hfDatasetDownloads": 0.3353},
        })
        self.assertEqual(enrich_metrics.TODAY_FORECAST_BONUS_WEIGHT, 0.25)
        weights = enrich_metrics.WINDOW_WEIGHTS["today"]
        self.assertAlmostEqual(weighted_attention({
            "hfPaperUpvotes": 0.9, "githubStars": 0.5, "hfDatasetDownloads": 0.1,
        }, weights), 0.7133333333333334)
        self.assertAlmostEqual(weighted_attention({
            "hfPaperUpvotes": None, "githubStars": 0.5, "hfDatasetDownloads": 0.1,
        }, weights), 0.47333333333333333)
        self.assertAlmostEqual(weighted_attention({
            "hfPaperUpvotes": 0.9, "githubStars": None, "hfDatasetDownloads": None,
        }, weights), 0.74)
        self.assertIsNone(weighted_attention({}, weights))

    def test_missing_downloads_do_not_outrank_stronger_complete_signals(self) -> None:
        weights = enrich_metrics.WINDOW_WEIGHTS["30d"]
        asi = weighted_attention({
            "hfPaperUpvotes": 0.9646,
            "githubStars": 0.9883,
            "hfDatasetDownloads": 0.8684,
        }, weights)
        playworld = weighted_attention({
            "hfPaperUpvotes": 0.9343,
            "githubStars": 0.9805,
            "hfDatasetDownloads": None,
        }, weights)
        self.assertGreater(asi, playworld)

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
    def test_latest_attention_adds_forecast_bonus_to_observed_signals(self, _history) -> None:
        records = [
            {"id": "forecast", "releasedAt": "2026-08-24", "links": {}, "attentionForecast": {"score": 80}},
            {"id": "quiet", "releasedAt": "2026-08-24", "links": {}, "attentionForecast": {"score": 20}},
        ]
        raw = {
            key: {
                "hfPaperUpvotes": 5, "githubStars": None, "githubScope": None,
                "hfDatasetDownloads": None, "hfDailySubmittedAt": None,
            }
            for key in ("forecast", "quiet")
        }
        rank_records(records, raw, date(2026, 8, 26), "2026-08-24")
        self.assertEqual(records[0]["ranking"]["today"]["score"], 58)
        self.assertEqual(records[1]["ranking"]["today"]["score"], 43)
        self.assertEqual(records[0]["ranking"]["today"]["rank"], 1)
        self.assertEqual(records[0]["ranking"]["today"]["level"]["components"]["llmAttentionForecast"]["value"], 80)
        self.assertEqual(records[0]["ranking"]["today"]["level"]["components"]["llmAttentionForecast"]["role"], "bonus")

    @patch("enrich_metrics.closest_history", return_value=None)
    def test_latest_attention_uses_bounded_forecast_when_signals_are_unavailable(self, _history) -> None:
        records = [{
            "id": "forecast-only", "releasedAt": "2026-08-24", "links": {},
            "attentionForecast": {"score": 80},
        }]
        raw = {
            "forecast-only": {
                "hfPaperUpvotes": None, "githubStars": None, "githubScope": None,
                "hfDatasetDownloads": None, "hfDailySubmittedAt": None,
            }
        }

        rank_records(records, raw, date(2026, 8, 26), "2026-08-24")

        latest = records[0]["ranking"]["today"]
        self.assertEqual(latest["score"], 20)
        self.assertIsNone(latest["rank"])
        self.assertEqual(latest["confidence"], "Low")
        self.assertEqual(
            latest["level"]["components"]["llmAttentionForecast"]["value"], 80
        )

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
        self.assertEqual(popular["score"], 81)

    @patch("enrich_metrics.closest_history", return_value=None)
    def test_window_log_normalization_does_not_reverse_larger_hf_vote_count(self, _history) -> None:
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


class RateLimitTests(unittest.TestCase):
    def test_429_waits_for_retry_after_then_succeeds(self):
        import io
        from email.message import Message
        from urllib.error import HTTPError
        import enrich_metrics as em
        headers = Message(); headers['Retry-After'] = '7'
        calls, sleeps = [], []
        class Ok(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): pass
        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            if len(calls) < 3:
                raise HTTPError(request.full_url, 429, 'Too Many', headers, None)
            return Ok(b'{"upvotes": 12}')
        original = em.urlopen
        em.urlopen = fake_urlopen
        try:
            self.assertEqual(em.get_json('https://example.org/x', sleep=sleeps.append), {'upvotes': 12})
        finally:
            em.urlopen = original
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [7.0, 7.0])

    def test_backoff_without_header_and_throttle_spacing(self):
        from urllib.error import HTTPError
        import enrich_metrics as em
        error = HTTPError('u', 429, 'x', None, None)
        self.assertEqual([em.retry_delay(error, a) for a in range(5)], [5, 10, 20, 40, 60])
        clock = iter([0.0, 0.0, 0.1, 0.8]).__next__
        waits = []
        em._host_next.pop('huggingface.co', None)
        em.throttle('https://huggingface.co/api/papers/1', waits.append, clock)
        em.throttle('https://huggingface.co/api/papers/2', waits.append, clock)
        self.assertEqual(len(waits), 1)
        self.assertAlmostEqual(waits[0], 0.6)
        em.throttle('https://api.github.com/x', waits.append, clock)  # unthrottled host
        self.assertEqual(len(waits), 1)


class FetchBudgetTests(unittest.TestCase):
    def test_hf_404_skips_the_public_page_fallback(self):
        record = {"id": "b", "source": {"type": "arxiv", "id": "2610.00001"},
                  "links": {"data": "https://huggingface.co/datasets/org/set"}}
        for status, page_calls in ((404, 0), (401, 2)):
            with self.subTest(status=status), \
                    patch.object(enrich_metrics, "get_json_status", return_value=(status, None)), \
                    patch.object(enrich_metrics, "get_public_html", return_value="") as page:
                item = enrich_metrics.enrich_one(record, None, False)
            self.assertEqual(page.call_count, page_calls)
            self.assertEqual(item["signalStatus"]["hfPaperUpvotes"]["state"], "unavailable")

    def test_rate_limit_wait_past_the_deadline_gives_up_without_sleeping(self):
        error = HTTPError("https://example.test/x", 429, "slow down", None, None)
        sleeps = []
        with patch.object(enrich_metrics, "urlopen", side_effect=error), \
                patch.object(enrich_metrics, "_deadline", enrich_metrics.time.monotonic() + 1):
            self.assertEqual(enrich_metrics.get_json_status("https://example.test/x", sleep=sleeps.append), (429, None))
        self.assertEqual(sleeps, [])

    def test_priority_is_latest_batch_then_unseen_then_least_recently_fetched(self):
        records = [{"id": key, "releasedAt": released} for key, released in (
            ("recent-fetch", "2026-09-01"), ("old-fetch", "2026-09-02"), ("legacy", "2026-09-03"),
            ("unseen", "2026-08-01"), ("today", "2026-10-19"))]
        previous = {"attemptedAt": "2026-10-05T00:00:00Z", "records": [
            {"benchmarkId": "recent-fetch", "fetchedAt": "2026-10-19T00:00:00Z"},
            {"benchmarkId": "old-fetch", "fetchedAt": "2026-10-10T00:00:00Z"},
            {"benchmarkId": "legacy"},
            {"benchmarkId": "today", "fetchedAt": "2026-10-19T00:00:00Z"},
        ]}
        order = enrich_metrics.fetch_priority(records, previous, "2026-10-19", "2026-10-19")
        self.assertEqual([r["id"] for r in order], ["today", "unseen", "legacy", "old-fetch", "recent-fetch"])

    def test_deferred_record_keeps_last_known_values_as_stale(self):
        previous_row = {
            "benchmarkId": "b", "hfPaperUpvotes": 9, "githubStars": 40, "githubRepo": "https://github.com/o/r",
            "hfDailySubmittedAt": "2026-09-01T00:00:00Z", "fetchedAt": "2026-10-04T00:00:00Z",
            "signalStatus": {"hfPaperUpvotes": {"state": "fresh"}, "githubStars": {"state": "fresh"},
                             "hfDatasetDownloads": {"state": "not_applicable"},
                             "hfDatasetLikes": {"state": "not_applicable"}},
        }
        row = enrich_metrics.unfetched_row({"id": "b"}, previous_row)
        self.assertEqual(row["fetchedAt"], "2026-10-04T00:00:00Z")
        self.assertEqual(row["hfDailySubmittedAt"], "2026-09-01T00:00:00Z")
        [item] = preserve_last_known([row], [{"id": "b"}], {"date": "2026-10-04", "records": [previous_row]})
        self.assertEqual((item["hfPaperUpvotes"], item["githubStars"]), (9, 40))
        self.assertEqual(item["signalStatus"]["githubStars"], {"state": "stale", "lastSuccessfulDate": "2026-10-04"})
        self.assertEqual(item["signalStatus"]["hfDatasetDownloads"]["state"], "not_applicable")

    def test_budget_defers_records_instead_of_running_past_it(self):
        from argparse import Namespace
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            records = [{"id": key, "releasedAt": "2026-10-19", "links": {}} for key in ("a", "b", "c")]
            data = root / "benchmarks.json"
            data.write_text(json.dumps({"manifest": {}, "records": records}))
            stack.enter_context(patch.object(enrich_metrics, "DATA_PATH", data))
            stack.enter_context(patch.object(enrich_metrics, "METRICS_DIR", root))
            stack.enter_context(patch.object(enrich_metrics, "publication_today", return_value=date(2026, 10, 20)))
            stack.enter_context(patch.object(enrich_metrics, "effective_latest_batch",
                                             return_value={"from": "2026-10-19", "to": "2026-10-19"}))
            calls = []
            def slow_fetch(record, *args):
                calls.append(record["id"])
                enrich_metrics._deadline = 0  # the budget runs out during the first fetch
                return {**{field: None for field in enrich_metrics.RESULT_FIELDS},
                        "benchmarkId": record["id"], "hfPaperUpvotes": 3,
                        "signalStatus": {"hfPaperUpvotes": {"state": "fresh"}}}
            stack.enter_context(patch.object(enrich_metrics, "enrich_one", side_effect=slow_fetch))
            args = Namespace(rerank_only=False, today_only=False, date=None, only_ids=None,
                             github_limit=0, workers=1, max_minutes=10)
            stack.enter_context(patch.object(enrich_metrics, "parse_args", return_value=args))
            enrich_metrics.main()
            self.assertEqual(len(calls), 1)
            self.assertIsNone(enrich_metrics._deadline)
            saved = {r["benchmarkId"]: r for r in json.loads((root / "2026-10-20.json").read_text())["records"]}
            self.assertEqual(set(saved), {"a", "b", "c"})
            deferred = [r for r in saved.values() if r["benchmarkId"] not in calls]
            self.assertTrue(all(r["signalStatus"]["hfPaperUpvotes"]["state"] == "not_refreshed" for r in deferred))
            self.assertIsNotNone(saved[calls[0]]["fetchedAt"])

    def test_budget_rotates_through_records_across_days(self):
        # Rows deferred on day 1 must sort before rows fetched on day 1; otherwise
        # the newest records are refetched every day and older ones never are.
        from argparse import Namespace
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            records = [{"id": key, "releasedAt": released, "links": {}}
                       for key, released in (("a", "2026-09-01"), ("b", "2026-09-02"), ("c", "2026-09-03"))]
            data = root / "benchmarks.json"
            data.write_text(json.dumps({"manifest": {}, "records": records}))
            legacy = {"date": "2026-10-05", "attemptedAt": "2026-10-05T00:00:00Z", "records": [
                {"benchmarkId": key, "hfPaperUpvotes": 1, "signalStatus": {}} for key in ("a", "b", "c")]}
            (root / "2026-10-05.json").write_text(json.dumps(legacy))
            stack.enter_context(patch.object(enrich_metrics, "DATA_PATH", data))
            stack.enter_context(patch.object(enrich_metrics, "METRICS_DIR", root))
            stack.enter_context(patch.object(enrich_metrics, "effective_latest_batch",
                                             return_value={"from": "2026-10-30", "to": "2026-10-30"}))
            calls = []
            def one_fetch_per_day(record, *args):
                calls.append(record["id"])
                enrich_metrics._deadline = 0
                return {**{field: None for field in enrich_metrics.RESULT_FIELDS},
                        "benchmarkId": record["id"], "hfPaperUpvotes": 2,
                        "signalStatus": {"hfPaperUpvotes": {"state": "fresh"}}}
            stack.enter_context(patch.object(enrich_metrics, "enrich_one", side_effect=one_fetch_per_day))
            args = Namespace(rerank_only=False, today_only=False, date=None, only_ids=None,
                             github_limit=0, workers=1, max_minutes=10)
            stack.enter_context(patch.object(enrich_metrics, "parse_args", return_value=args))
            for day in (20, 21, 22):
                with patch.object(enrich_metrics, "publication_today", return_value=date(2026, 10, day)):
                    enrich_metrics.main()
            self.assertEqual(calls, ["c", "b", "a"])

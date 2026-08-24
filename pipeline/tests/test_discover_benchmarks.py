from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import discover_benchmarks


class SourceScheduleTests(unittest.TestCase):
    def test_arxiv_is_skipped_on_its_two_no_announcement_days(self) -> None:
        self.assertFalse(discover_benchmarks.arxiv_enabled_for_date("2026-08-21"))  # Friday
        self.assertFalse(discover_benchmarks.arxiv_enabled_for_date("2026-08-22"))  # Saturday
        self.assertTrue(discover_benchmarks.arxiv_enabled_for_date("2026-08-23"))   # Sunday

    def test_generic_repository_names_do_not_enter_review(self) -> None:
        self.assertTrue(discover_benchmarks.generic_artifact_name("benchmarks"))
        self.assertFalse(discover_benchmarks.generic_artifact_name("AgentBench"))

    def test_every_run_rechecks_a_three_day_arxiv_window(self) -> None:
        self.assertEqual(
            discover_benchmarks.arxiv_query_dates("2026-08-23"),
            ["2026-08-21", "2026-08-22", "2026-08-23"],
        )
        self.assertEqual(
            discover_benchmarks.arxiv_query_dates("2026-08-24"),
            ["2026-08-22", "2026-08-23", "2026-08-24"],
        )


class AdapterTests(unittest.TestCase):
    @patch("discover_benchmarks.fetch_text", return_value="100 agent tasks scored by task success rate")
    @patch("discover_benchmarks.fetch_json")
    def test_github_keeps_new_ai_benchmark_repositories(self, fetch_json, _fetch_text) -> None:
        fetch_json.return_value = {"items": [{
            "name": "AgentBench", "full_name": "lab/AgentBench", "description": "LLM agent benchmark",
            "created_at": "2026-08-22T04:00:00Z", "updated_at": "2026-08-22T05:00:00Z",
            "html_url": "https://github.com/lab/AgentBench", "homepage": "", "topics": ["llm"],
            "owner": {"login": "lab"}, "fork": False, "archived": False, "disabled": False,
        }]}
        rows = discover_benchmarks.github_candidates("2026-08-22")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["links"]["code"], "https://github.com/lab/AgentBench")

    @patch("discover_benchmarks.fetch_json")
    def test_huggingface_uses_dataset_creation_date(self, fetch_json) -> None:
        fetch_json.return_value = [{
            "id": "lab/AgentBench", "author": "lab", "description": "AI agent benchmark with 100 tasks and success-rate scoring",
            "createdAt": "2026-08-22T07:00:00.000Z", "lastModified": "2026-08-22T08:00:00.000Z",
            "tags": ["task_categories:question-answering"],
        }]
        rows = discover_benchmarks.huggingface_candidates("2026-08-22")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["type"], "huggingface")

    @patch("discover_benchmarks.fetch_json")
    def test_openreview_unwraps_v2_content_values(self, fetch_json) -> None:
        fetch_json.return_value = {"notes": [{
            "id": "note1", "forum": "forum1", "cdate": 1787396400000,
            "content": {
                "title": {"value": "AgentBench: A Tool-Use Benchmark"},
                "abstract": {"value": "A reusable AI agent benchmark with 100 tasks scored by success rate."},
                "authors": {"value": ["A. Researcher"]},
            },
        }]}
        rows = discover_benchmarks.openreview_candidates("2026-08-22")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["links"]["report"], "https://openreview.net/forum?id=forum1")

    def test_external_candidate_drops_empty_arxiv_link_slots(self) -> None:
        record = discover_benchmarks.candidate_record({
            "type": "github",
            "id": "github:lab/agentbench",
            "title": "AgentBench",
            "description": "A reusable AI agent benchmark with scored tasks.",
            "releasedAt": "2026-08-21",
            "updatedAt": "2026-08-21T05:00:00Z",
            "url": "https://github.com/lab/AgentBench",
            "links": {"code": "https://github.com/lab/AgentBench"},
            "authors": ["lab"],
        }, "2026-08-23T00:00:00Z", {"thresholds": {"review": 0.35}})
        self.assertNotIn("pdf", record["links"])
        self.assertTrue(all(record["links"].values()))


class DeduplicationTests(unittest.TestCase):
    def test_same_name_merges_paper_repo_and_dataset_links(self) -> None:
        paper = {
            "name": "AgentBench", "source": {"id": "1234", "url": "https://arxiv.org/abs/1234"},
            "links": {"report": "https://arxiv.org/abs/1234"}, "discoverySources": [],
        }
        repo = {
            "name": "Agent-Bench", "source": {"id": "github:lab/agentbench", "url": "https://github.com/lab/AgentBench"},
            "links": {"code": "https://github.com/lab/AgentBench"},
            "discoverySources": [{"type": "github", "id": "github:lab/agentbench", "url": "https://github.com/lab/AgentBench"}],
        }
        self.assertTrue(discover_benchmarks.same_identity(paper, repo))
        discover_benchmarks.merge_candidate(paper, repo)
        self.assertEqual(paper["links"]["code"], "https://github.com/lab/AgentBench")
        self.assertEqual(len(paper["discoverySources"]), 1)


if __name__ == "__main__":
    unittest.main()

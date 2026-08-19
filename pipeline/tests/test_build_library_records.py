from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_library_records import build_payload, normalized_official_url, radar_duplicate


def seed_record(name: str, project: str, record_id: str = "lib_example") -> dict:
    return {
        "id": record_id,
        "familyId": "family_example",
        "name": name,
        "aliases": [],
        "recordType": "family",
        "primaryDomain": "General AI",
        "area": "Knowledge & Reasoning",
        "firstRelease": {"year": 2024, "date": None},
        "links": {"paper": None, "project": project, "code": project},
        "sourceAttribution": [{"role": "official-project", "url": project}],
        "adoptionRefs": ["model-report"],
        "catalogDiscoveryRefs": ["catalog"],
    }


def seed_payload(record: dict) -> dict:
    return {
        "schemaVersion": "1.0",
        "description": "test",
        "reviewedAt": "2026-08-19",
        "modelReportSources": {"model-report": "https://example.com/model-report"},
        "catalogsConsulted": {"catalog": "https://example.com/catalog"},
        "records": [record],
    }


def radar_record(name: str, project: str, record_id: str = "bm_example") -> dict:
    return {
        "id": record_id,
        "name": name,
        "aliases": [],
        "links": {"project": project},
        "source": {"id": "2601.00001", "url": "https://arxiv.org/abs/2601.00001"},
    }


class LibraryBuilderTests(unittest.TestCase):
    def test_normalizes_arxiv_and_github_identity_links(self) -> None:
        self.assertEqual(
            normalized_official_url("https://arxiv.org/pdf/2607.07946v2.pdf"),
            "arxiv.org/2607.07946",
        )
        self.assertEqual(
            normalized_official_url("https://github.com/DataCurve-AI/deep-swe.git/"),
            "https://github.com/datacurve-ai/deep-swe",
        )

    def test_deepswe_style_name_and_link_match_is_removed(self) -> None:
        source = seed_record("DeepSWE", "https://github.com/datacurve-ai/deep-swe", "lib_deepswe")
        radar = radar_record("DeepSWE", "https://github.com/DataCurve-AI/deep-swe/")
        payload = build_payload(seed_payload(source), {"manifest": {"dataAsOf": "2026-08-19"}, "records": [radar]})
        self.assertEqual(payload["records"], [])
        self.assertEqual(payload["generation"]["excludedRadarDuplicates"][0]["seedId"], "lib_deepswe")

    def test_name_only_collision_does_not_remove_a_family(self) -> None:
        source = seed_record("SWE-bench", "https://www.swebench.com/")
        radar = radar_record("SWE-Bench", "https://example.com/swe-bench-promax")
        self.assertIsNone(radar_duplicate(source, [radar]))

    def test_report_refs_are_preserved_without_inventing_usage_dates(self) -> None:
        source = seed_record("ExampleBench", "https://example.com/benchmark")
        payload = build_payload(seed_payload(source), {"manifest": {"dataAsOf": "2026-08-19"}, "records": []})
        record = payload["records"][0]
        self.assertEqual(record["familyId"], "family_example")
        self.assertEqual(record["adoptionRefs"], ["model-report"])
        self.assertEqual(record["catalogDiscoveryRefs"], ["catalog"])
        self.assertEqual(record["sourceAttribution"][0]["role"], "official-project")
        self.assertEqual(record["usageObservations"], [])

    def test_committed_output_is_reproducible(self) -> None:
        root = Path(__file__).resolve().parents[2]
        seed = json.loads((root / "data/library_seed_records.json").read_text(encoding="utf-8"))
        radar = json.loads((root / "data/benchmarks.json").read_text(encoding="utf-8"))
        output = json.loads((root / "data/library_records.json").read_text(encoding="utf-8"))
        self.assertEqual(output, build_payload(seed, radar))


if __name__ == "__main__":
    unittest.main()

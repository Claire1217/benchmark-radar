#!/usr/bin/env python3
"""Generate a compact, source-linked Awesome list from canonical data."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "benchmarks.json"
OUTPUT_PATHS = [ROOT / "README.md", ROOT / "AWESOME_BENCHMARKS.md"]


def link(label: str, url: str | None) -> str | None:
    return f"[{label}]({url})" if url else None


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in payload.get("records", []):
        groups[record.get("primaryDomain") or "General AI"].append(record)

    lines = [
        "# Awesome Emerging AI Benchmarks",
        "",
        "[![Daily update](https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml/badge.svg)](https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml)",
        "",
        "A source-audited, daily-updated index of newly released AI benchmarks.",
        "",
        "**[Browse and filter on Benchmark Radar →](https://claire1217.github.io/benchmark-radar/)**",
        "",
        "> This is a discovery index, not an endorsement or quality leaderboard. Ambiguous candidates are held for review, and missing resources remain unknown.",
        "",
        f"**Snapshot:** {payload['manifest']['dataAsOf']} · **Benchmark releases:** {payload['manifest']['recordCount']}",
        "",
        "## Contents",
        "",
    ]
    for domain in sorted(groups):
        anchor = domain.lower().replace("&", "").replace(" ", "-")
        lines.append(f"- [{domain}](#{anchor}) ({len(groups[domain])})")
    lines.append("")

    for domain in sorted(groups):
        lines.extend([f"## {domain}", ""])
        records = sorted(groups[domain], key=lambda item: (item["releasedAt"], item["name"]), reverse=True)
        for record in records:
            links = [
                link("Paper", record.get("links", {}).get("paper")),
                link("HF", record.get("links", {}).get("hfPaper")),
                link("Code", record.get("links", {}).get("code")),
                link("Data", record.get("links", {}).get("data")),
            ]
            resources = " · ".join(item for item in links if item)
            evidence = record.get("evidence", {}).get("snippet", "").replace("\n", " ")
            if len(evidence) > 220:
                evidence = evidence[:219].rstrip() + "…"
            lines.append(f"- **{record['name']}** ({record['releasedAt']}) — {evidence} {resources}")
        lines.append("")

    lines.extend(
        [
            "## Method",
            "",
            "Records start from primary-source metadata. A release must have a named benchmark/evaluation-suite title or an explicit source sentence that introduces a benchmark. Attention metrics are snapshotted separately and never treated as quality.",
            "",
            "See [`docs/PROJECT.md`](docs/PROJECT.md) for the data model and update pipeline, [`data/runs/`](data/runs/) for dated indexing receipts, and [`data/metrics/`](data/metrics/) for raw public-signal snapshots.",
            "",
            "## Contributing",
            "",
            "Corrections and additions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening an issue or pull request.",
            "",
        ]
    )
    content = "\n".join(lines)
    for output_path in OUTPUT_PATHS:
        output_path.write_text(content, encoding="utf-8")
    print(f"generated={','.join(str(path) for path in OUTPUT_PATHS)} groups={len(groups)} records={sum(map(len, groups.values()))}")


if __name__ == "__main__":
    main()

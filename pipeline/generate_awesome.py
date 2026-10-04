#!/usr/bin/env python3
"""Generate a compact, source-linked Awesome list from canonical data."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import json
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "benchmarks.json"
OUTPUT_PATH = ROOT / "AWESOME_BENCHMARKS.md"
README_PATH = ROOT / "README.md"
SITE_URL = "https://benchmark-radar.com"
README_START = "<!-- GENERATED_OVERVIEW_START -->"
README_END = "<!-- GENERATED_OVERVIEW_END -->"


def link(label: str, url: str | None) -> str | None:
    return f"[{label}]({url})" if url else None


def site_filter(kind: str, value: str) -> str:
    return f"{SITE_URL}/#library?{kind}={quote(value)}"


def attention_text(record: dict) -> str:
    attention = record.get("attention") or {}
    parts = []
    if attention.get("hfPaperUpvotes") is not None:
        parts.append(f"{attention['hfPaperUpvotes']:,} HF votes")
    if attention.get("githubStars") is not None and attention.get("githubScope") != "hosting_repo":
        parts.append(f"{attention['githubStars']:,} GitHub stars")
    if attention.get("hfDatasetDownloads") is not None:
        parts.append(f"{attention['hfDatasetDownloads']:,} dataset downloads")
    return " · ".join(parts) or "Public signals not measured yet"


def short_text(value: str, limit: int) -> str:
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def update_readme() -> None:
    radar = json.loads((ROOT / "data" / "benchmarks_index.json").read_text(encoding="utf-8"))
    library = json.loads((ROOT / "data" / "library_index.json").read_text(encoding="utf-8"))
    as_of = date.fromisoformat(radar["manifest"]["dataAsOf"])
    month = as_of.strftime("%Y-%m")
    candidates = [
        record for record in radar.get("records", [])
        if record.get("releasedAt", "").startswith(month)
        and (record.get("ranking", {}).get("30d", {}).get("rank") is not None)
    ]
    candidates.sort(
        key=lambda record: (
            record.get("ranking", {}).get("30d", {}).get("rank", 10**9),
            record.get("releasedAt", ""),
        ),
    )

    overview = [
        f"<sub>Updated {as_of.isoformat()} · benchmarks first released in {as_of.strftime('%B %Y')}</sub>",
        "",
        "| # | Benchmark | Field | Public signals |",
        "|---:|---|---|---|",
    ]
    for position, record in enumerate(candidates[:10], 1):
        links = record.get("links") or {}
        sources = " · ".join(
            item for item in (
                link("Paper", links.get("report") or links.get("paper")),
                link("Code", links.get("code")),
            ) if item
        )
        names = {d["id"]: d["name"] for d in library["manifest"]["libraryTaxonomy"]["directions"]}
        area = " · ".join(names[t] for t in record.get("libraryCategories", [])[:2] if t in names) or "Other benchmark tasks"
        source_line = f"<br><sub>{sources}</sub>" if sources else ""
        overview.append(
            f"| {position} | **{record['name']}**{source_line} | {area} | {attention_text(record)} |"
        )

    records = [r for r in library.get("records", []) if r.get("displayEligible") is not False and r.get("evaluationMode") != "viewpoint_probe"]
    taxonomy = library["manifest"]["libraryTaxonomy"]
    directions = taxonomy["directions"]
    group_cells = []
    for group in taxonomy["groups"]:
        links = [f"[{d['name']}]({site_filter('direction', d['id'])}) · {d['count']:,}" for d in directions if d["group"] == group["id"]]
        if links:
            group_cells.append((group["name"], "<br>".join(links)))
    # Two columns keep the README table readable on GitHub.
    half = (len(group_cells) + 1) // 2
    column = lambda cells: "<br><br>".join(f"**{name}**<br>{links}" for name, links in cells)
    overview.extend([
        "",
        "### Explore the library",
        "",
        "| Capabilities | Agents, safety & domains |",
        "|---|---|",
        f"| {column(group_cells[:half])} | {column(group_cells[half:])} |",
        "",
        f"**[Browse all {len(records):,} Library records →]({SITE_URL}/#library)**",
    ])

    readme = README_PATH.read_text(encoding="utf-8")
    before, separator, remainder = readme.partition(README_START)
    if not separator or README_END not in remainder:
        raise RuntimeError("README generated overview markers are missing")
    _, _, after = remainder.partition(README_END)
    README_PATH.write_text(
        before + README_START + "\n" + "\n".join(overview) + "\n" + README_END + after,
        encoding="utf-8",
    )


def main() -> None:
    payload = json.loads((ROOT / "data" / "benchmarks_index.json").read_text(encoding="utf-8"))
    library = json.loads((ROOT / "data" / "library_index.json").read_text())
    categories = {t["id"]: t["name"] for t in library["manifest"]["libraryTaxonomy"]["directions"]}
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in payload.get("records", []):
        if record.get("displayEligible") is False or record.get("evaluationMode") == "viewpoint_probe": continue
        # Each release is listed once, under its primary category.
        primary = (record.get("libraryCategories") or [None])[0]
        groups[categories.get(primary, "Other benchmark tasks")].append(record)

    lines = [
        "# Awesome Emerging AI Benchmarks",
        "",
        "<!-- Generated by pipeline/generate_awesome.py. Do not edit this file directly. -->",
        "",
        "[![Daily update](https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml/badge.svg)](https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml)",
        "",
        "A daily-updated discovery index grouped by the same categories as Radar, Library and Trends. Each entry is listed once, under its primary category.",
        "",
        f"**[Browse and filter on Benchmark Radar →]({SITE_URL}/)**",
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
                link("Paper", record.get("links", {}).get("report") or record.get("links", {}).get("paper")),
                link("HF", record.get("links", {}).get("hfPaper")),
                link("Code", record.get("links", {}).get("code")),
                link("Data", record.get("links", {}).get("data")),
            ]
            resources = " · ".join(item for item in links if item)
            evidence = record.get("description") or record.get("evidence", {}).get("snippet", "").replace("\n", " ")
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
            "See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for the indexing and evidence rules, [`data/runs/`](data/runs/) for dated indexing receipts, and [`data/metrics/`](data/metrics/) for raw public-signal snapshots.",
            "",
            "## Contributing",
            "",
            "Corrections and additions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening an issue or pull request.",
            "",
        ]
    )
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    update_readme()
    print(f"generated={OUTPUT_PATH} groups={len(groups)} records={sum(map(len, groups.values()))}")


if __name__ == "__main__":
    main()

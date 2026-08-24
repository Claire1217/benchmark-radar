#!/usr/bin/env python3
"""Generate a compact, source-linked Awesome list from canonical data."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from html import escape
import json
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "benchmarks.json"
OUTPUT_PATH = ROOT / "AWESOME_BENCHMARKS.md"
README_PATH = ROOT / "README.md"
README_IMAGE_PATH = ROOT / "docs" / "assets" / "benchmark-radar-90-days.svg"
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


def generate_readme_image(radar: dict) -> None:
    """Generate the README's current 90-day Radar preview from public data."""
    as_of = date.fromisoformat(radar["manifest"]["dataAsOf"])
    window_start = (as_of - timedelta(days=89)).isoformat()
    records = [
        record for record in radar.get("records", [])
        if record.get("ranking", {}).get("90d", {}).get("rank") is not None
        and window_start <= record.get("releasedAt", "") <= as_of.isoformat()
    ]
    records.sort(key=lambda record: record["ranking"]["90d"]["rank"])
    rows = records[:4]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">',
        '<rect width="1600" height="900" fill="#fbfbfa"/>',
        '<style>text{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#171717}.muted{fill:#667085}.inverse{fill:#fff}.small{font-size:14px}.label{font-size:13px;font-weight:700;letter-spacing:1px}.body{font-size:17px}.link{fill:#1769ff}.tag{font-size:13px;font-weight:600}</style>',
        '<circle cx="139" cy="32" r="15" fill="#171717"/><circle cx="143" cy="29" r="7" fill="#fbfbfa"/><circle cx="146" cy="35" r="3" fill="#fbfbfa"/>',
        '<text x="164" y="39" font-size="19" font-weight="700">Benchmark Radar</text>',
        '<text x="610" y="39" font-size="15" font-weight="700">Radar</text><text x="679" y="39" class="muted" font-size="15">Library</text><text x="745" y="39" class="muted" font-size="15">Trends</text><text x="808" y="39" class="muted" font-size="15">Saved 0</text>',
        '<text x="1290" y="39" class="muted" font-size="15">GitHub ↗</text><line x1="0" y1="64" x2="1600" y2="64" stroke="#dededb"/>',
        '<text x="155" y="165" font-size="48" font-weight="760">Track emerging benchmarks.</text>',
        '<text x="155" y="208" class="muted" font-size="20">See what is new and what is gaining public attention.</text>',
        f'<text x="1160" y="185" font-size="34" font-weight="760">{len(records):,}</text>',
        '<text x="1248" y="174" class="muted" font-size="14">releases indexed</text><text x="1248" y="193" class="muted" font-size="14">past 90 days</text>',
        '<line x1="130" y1="258" x2="1470" y2="258" stroke="#d8d8d5"/>',
        '<text x="155" y="299" class="label muted">TIME WINDOW</text><rect x="155" y="315" width="330" height="48" rx="6" fill="#fff" stroke="#d6d6d2"/>',
        f'<text x="176" y="345" class="body">Latest · {escape(radar["manifest"]["latestSourceDate"][8:10])} Aug</text><text x="297" y="345" class="body">30 days</text><rect x="386" y="319" width="95" height="40" rx="5" fill="#171717"/><text x="404" y="345" class="inverse" font-size="17">90 days</text>',
        '<text x="530" y="299" class="label muted">SORT BY</text><rect x="530" y="315" width="186" height="48" rx="6" fill="#fff" stroke="#d6d6d2"/><rect x="534" y="319" width="94" height="40" rx="5" fill="#171717"/><text x="551" y="345" class="inverse" font-size="17">Attention</text><text x="647" y="345" class="body">Newest</text>',
        '<text x="155" y="416" font-size="26" font-weight="740">Rising benchmarks</text>',
        f'<text x="455" y="416" class="muted" font-size="17">{len(records):,} results</text>',
        f'<text x="1280" y="416" class="muted" font-size="15">Updated {as_of.isoformat()}</text>',
        '<line x1="130" y1="438" x2="1470" y2="438" stroke="#bfc0bc"/>',
    ]
    for index, record in enumerate(rows):
        y = 472 + index * 105
        ranking = record["ranking"]["90d"]
        field = (record.get("capabilityGroups") or record.get("applicationDomains") or [record.get("area") or "General AI"])[0]
        signals = short_text(attention_text(record), 72)
        parts.extend([
            f'<text x="155" y="{y + 25}" class="label muted">{escape(record.get("releasedAt", "")[5:])}</text>',
            f'<rect x="252" y="{y}" width="88" height="27" rx="5" fill="#eef1f6"/><text x="266" y="{y + 19}" class="tag">General AI</text>',
            f'<rect x="349" y="{y}" width="{max(95, len(field) * 8 + 20)}" height="27" rx="5" fill="#f1f2ef"/><text x="361" y="{y + 19}" class="small muted">{escape(field)}</text>',
            f'<text x="252" y="{y + 57}" font-size="25" font-weight="760">{escape(short_text(record["name"], 42))}</text>',
            f'<text x="252" y="{y + 84}" class="body muted">{escape(short_text(record.get("oneLine") or "", 112))}</text>',
            f'<text x="1120" y="{y + 31}" font-size="18" font-weight="700">Attention {ranking.get("score", 0):.0f}</text>',
            f'<text x="1250" y="{y + 31}" class="muted" font-size="16">#{ranking["rank"]} · 90d</text>',
            f'<text x="1120" y="{y + 61}" class="muted" font-size="15">{escape(signals)}</text>',
            f'<line x1="130" y1="{y + 101}" x2="1470" y2="{y + 101}" stroke="#dededb"/>',
        ])
    parts.append('</svg>')
    README_IMAGE_PATH.write_text("\n".join(parts) + "\n", encoding="utf-8")


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
        area = (record.get("capabilityGroups") or record.get("applicationDomains") or [record.get("area") or "—"])[0]
        source_line = f"<br><sub>{sources}</sub>" if sources else ""
        overview.append(
            f"| {position} | **{record['name']}**{source_line} | {area} | {attention_text(record)} |"
        )

    records = library.get("records", [])
    capability_counts = {
        label: sum(label in (record.get("capabilityGroups") or []) for record in records)
        for label in (
            "Knowledge & Reasoning", "Coding & Software Engineering", "Agents",
            "Multimodal Perception", "Safety & Trustworthiness",
            "Mathematics & Formal Sciences",
        )
    }
    rsi_count = sum("Self-Evolution" in (record.get("topics") or []) for record in records)
    domain_counts = {
        label: sum(label in (record.get("applicationDomains") or []) for record in records)
        for label in (
            "Science & Research", "Robotics & Autonomous Systems",
            "Health & Life Sciences", "Finance & Economics", "Cybersecurity",
        )
    }
    capability_links = [
        f"[{label}]({site_filter('capability', label)}) · {count:,}"
        for label, count in capability_counts.items()
    ]
    capability_links.append(
        f"[Self-Evolution / RSI]({site_filter('topic', 'Self-Evolution')}) · {rsi_count:,}"
    )
    domain_links = [
        f"[{label}]({site_filter('domain', label)}) · {count:,}"
        for label, count in domain_counts.items()
    ]
    overview.extend([
        "",
        "### Explore the library",
        "",
        "| General AI capabilities | Application fields |",
        "|---|---|",
        f"| {'<br>'.join(capability_links)} | {'<br>'.join(domain_links)} |",
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
    generate_readme_image(radar)


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in payload.get("records", []):
        groups[record.get("primaryDomain") or "General AI"].append(record)

    lines = [
        "# Awesome Emerging AI Benchmarks",
        "",
        "<!-- Generated by pipeline/generate_awesome.py. Do not edit this file directly. -->",
        "",
        "[![Daily update](https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml/badge.svg)](https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml)",
        "",
        "A source-audited, daily-updated index of newly released AI benchmarks.",
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

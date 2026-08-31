#!/usr/bin/env python3
"""Assemble the dependency-free static artifact deployed by GitHub Pages."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
import json
from pathlib import Path
import shutil
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web"
OUTPUT = ROOT / "_site"
BASE_URL = "https://benchmark-radar.com"


def visible(record: dict) -> bool:
    return record.get("displayEligible") is not False and record.get("evaluationMode") != "viewpoint_probe"


def write_feed(records: list[dict], data_as_of: str) -> None:
    recent = sorted(
        records,
        key=lambda item: (str(item.get("releasedAt") or ""), str(item.get("name") or "")),
        reverse=True,
    )[:50]
    build_date = format_datetime(datetime.fromisoformat(data_as_of).replace(tzinfo=timezone.utc))
    items = []
    for record in recent:
        released_at = record.get("releasedAt") or data_as_of
        released = datetime.fromisoformat(released_at).replace(tzinfo=timezone.utc)
        description = record.get("description") or record.get("oneLine") or "Public AI benchmark indexed by Benchmark Radar."
        name = str(record.get("name") or "Unnamed benchmark")
        identifier = str(record.get("id") or name)
        items.append(
            f'<item><title>{xml_escape(name)}</title><link>{BASE_URL}/#library</link>'
            f'<guid isPermaLink="false">benchmark-radar:{xml_escape(identifier)}</guid>'
            f'<pubDate>{format_datetime(released)}</pubDate>'
            f'<description>{xml_escape(str(description))}</description></item>'
        )
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<rss version="2.0"><channel><title>Benchmark Radar updates</title><link>{BASE_URL}/</link>'
        '<description>New and updated public AI benchmarks indexed by Benchmark Radar.</description>'
        f'<language>en</language><lastBuildDate>{build_date}</lastBuildDate>'
        f'<atom:link xmlns:atom="http://www.w3.org/2005/Atom" href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>'
        f'{"".join(items)}</channel></rss>\n'
    )
    (OUTPUT / "feed.xml").write_text(content, encoding="utf-8")


def main() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(SOURCE, OUTPUT)
    shutil.copy2(ROOT / "docs" / "assets" / "benchmark-radar-overview.png", OUTPUT / "social-preview.png")
    data_dir = OUTPUT / "data"
    data_dir.mkdir()
    for name in ("benchmarks_index.json", "library_index.json", "domain_trends.json"):
        shutil.copy2(ROOT / "data" / name, data_dir / name)
    library = json.loads((ROOT / "data" / "library_index.json").read_text(encoding="utf-8"))
    write_feed([record for record in library["records"] if visible(record)], library["manifest"]["dataAsOf"])
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built={OUTPUT}")


if __name__ == "__main__":
    main()

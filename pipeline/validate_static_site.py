#!/usr/bin/env python3
"""Smoke-test the exact dependency-free GitHub Pages artifact."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "_site"


class Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.scripts: list[str] = []
        self.styles: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "script" and values.get("src"):
            self.scripts.append(str(values["src"]))
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.styles.append(str(values["href"]))


def main() -> None:
    index = OUTPUT / "index.html"
    if not index.exists():
        raise SystemExit("missing _site/index.html; run the Pages build first")
    document = Document()
    html = index.read_text(encoding="utf-8")
    document.feed(html)
    if len(document.ids) != len(set(document.ids)):
        raise SystemExit("duplicate HTML id")
    for asset in [*document.scripts, *document.styles]:
        target = OUTPUT / asset.removeprefix("./")
        if not target.exists():
            raise SystemExit(f"missing referenced asset: {asset}")
    expected_ids = {"radar-view", "library-view", "trends-view", "saved-count", "benchmark-list", "library-list", "line-chart"}
    if missing := expected_ids - set(document.ids):
        raise SystemExit(f"missing interactive regions: {sorted(missing)}")
    app = (OUTPUT / "app.js").read_text(encoding="utf-8")
    if 'sort:"attention"' not in app:
        raise SystemExit("Attention must remain the default sort")
    details = (OUTPUT / "details.js").read_text(encoding="utf-8")
    if "data-surface" not in app or not all(name in details for name in ("renderRadarDetails", "renderLibraryDetails")):
        raise SystemExit("Radar and Library detail contexts must remain distinct")
    if 'evaluationMode!=="viewpoint_probe"' not in app:
        raise SystemExit("viewpoint probes must remain outside public views")
    if any(f'href="#{route}"' not in html for route in ("library", "saved", "trends")):
        raise SystemExit("Library, Saved, or Trends navigation missing")
    for name in ("benchmarks_index.json", "library_index.json", "domain_trends.json"):
        json.loads((OUTPUT / "data" / name).read_text(encoding="utf-8"))
    print(f"validated_static_site assets={len(document.scripts) + len(document.styles)} ids={len(document.ids)}")


if __name__ == "__main__":
    main()

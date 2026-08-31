#!/usr/bin/env python3
"""Smoke-test the exact dependency-free GitHub Pages artifact."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


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
        target = OUTPUT / urlsplit(asset).path.removeprefix("./")
        if not target.exists():
            raise SystemExit(f"missing referenced asset: {asset}")
    expected_ids = {"radar-view", "library-view", "trends-view", "saved-count", "benchmark-list", "library-list", "library-domain-list", "line-chart"}
    if missing := expected_ids - set(document.ids):
        raise SystemExit(f"missing interactive regions: {sorted(missing)}")
    app = (OUTPUT / "app.js").read_text(encoding="utf-8")
    if 'sort:"attention"' not in app:
        raise SystemExit("Attention must remain the default sort")
    if "description-toggle" in app or "details-panel" in app:
        raise SystemExit("descriptions must display directly without secondary disclosure controls")
    if 'button.textContent=previous?"Show the previous day":""' not in app:
        raise SystemExit("Latest must offer a date-free previous-day control")
    if "state.latestFrom=latestAvailableDate()" not in app:
        raise SystemExit("Latest must automatically fall back to the newest non-empty day")
    if "dayDivider" in app or ".day-divider" in (OUTPUT / "styles.css").read_text(encoding="utf-8"):
        raise SystemExit("Latest must rely on card dates without redundant day dividers")
    if "new IntersectionObserver" in app:
        raise SystemExit("previous days must load only after an explicit button click")
    if 'evaluationMode!=="viewpoint_probe"' not in app:
        raise SystemExit("viewpoint probes must remain outside public views")
    if any(f'href="#{route}"' not in html for route in ("library", "saved", "trends")):
        raise SystemExit("Library, Saved, or Trends navigation missing")
    for name in ("benchmarks_index.json", "library_index.json", "domain_trends.json"):
        json.loads((OUTPUT / "data" / name).read_text(encoding="utf-8"))
    for name in ("robots.txt", "sitemap.xml", "feed.xml", "llms.txt", "social-preview.png", "about/index.html", "benchmarks/index.html", "detail.css", "3bf256ad2bac3dbab62facad3a131fdd.txt"):
        if not (OUTPUT / name).exists():
            raise SystemExit(f"missing discovery asset: {name}")
    if '<link rel="canonical" href="https://benchmark-radar.com/">' not in html:
        raise SystemExit("canonical production URL missing")
    if '<link rel="icon" href="/benchmark-radar-mark.png"' not in html:
        raise SystemExit("stable site-wide favicon URL missing")
    structured = re.search(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.DOTALL)
    if not structured:
        raise SystemExit("structured data missing")
    schema = json.loads(structured.group(1))
    website = next(item for item in schema["@graph"] if item.get("@type") == "WebSite")
    if website.get("name") != "Benchmark Radar" or "benchmark-radar" not in website.get("alternateName", []):
        raise SystemExit("Benchmark Radar site-name signals missing")
    if "Benchmark Radar" not in document_title(html):
        raise SystemExit("Benchmark Radar missing from page title")
    if not any(item.get("@type") == "Dataset" for item in schema["@graph"]):
        raise SystemExit("public benchmark Dataset schema missing")
    sitemap = ET.parse(OUTPUT / "sitemap.xml")
    urls = sitemap.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url")
    detail_pages = list((OUTPUT / "benchmarks").glob("*/index.html"))
    if len(detail_pages) < 1000 or len(urls) != len(detail_pages) + 3:
        raise SystemExit("crawlable benchmark pages or sitemap inventory incomplete")
    print(f"validated_static_site assets={len(document.scripts) + len(document.styles)} ids={len(document.ids)}")


def document_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


if __name__ == "__main__":
    main()

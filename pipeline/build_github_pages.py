#!/usr/bin/env python3
"""Assemble the dependency-free static artifact deployed by GitHub Pages."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web"
OUTPUT = ROOT / "_site"
BASE_URL = "https://benchmark-radar.com"


def visible(record: dict) -> bool:
    if record.get("displayEligible") is False or record.get("evaluationMode") == "viewpoint_probe":
        return False
    source_type = (record.get("source") or {}).get("type")
    if source_type not in {"github", "huggingface"}:
        return True
    links = record.get("links") or {}
    paper_hosts = {"arxiv.org", "www.arxiv.org", "openreview.net"}
    has_paper = any(
        value and urlsplit(value).hostname and urlsplit(value).hostname.lower() in paper_hosts
        for value in (links.get("report"), links.get("paper"), links.get("project"))
    )
    attention = record.get("attention") or {}
    stars = int(attention.get("githubStars") or 0)
    downloads = int(attention.get("hfDatasetDownloads") or 0)
    likes = int(attention.get("hfDatasetLikes") or 0)
    return has_paper or bool(links.get("hfPaper")) or stars >= 25 or downloads >= 1000 or likes >= 10


def record_path(record: dict) -> str:
    identifier = str(record["id"])
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", identifier):
        raise ValueError(f"unsafe benchmark id: {identifier}")
    return f"benchmarks/{identifier}/"


def resource_links(record: dict) -> str:
    links = record.get("links") or {}
    candidates = [
        ("Paper", links.get("report")), ("Project", links.get("project")),
        ("Code", links.get("code")), ("Data", links.get("data")),
        ("Hugging Face", links.get("hfPaper")),
    ]
    seen: set[str] = set()
    rendered = []
    for label, url in candidates:
        if not url or url in seen:
            continue
        seen.add(url)
        rendered.append(f'<a href="{escape(url, quote=True)}" rel="noreferrer">{label} ↗</a>')
    return "".join(rendered) or "<span>No public resource link recorded yet.</span>"


def detail_page(record: dict) -> str:
    name = str(record.get("name") or "Unnamed benchmark")
    description = str(record.get("description") or record.get("oneLine") or "Public AI benchmark indexed by Benchmark Radar.")
    canonical = f"{BASE_URL}/{record_path(record)}"
    domains = record.get("applicationDomains") or [record.get("primaryDomain") or "General AI"]
    capabilities = record.get("capabilityGroups") or record.get("capabilities") or []
    publishers = [item.get("name") for item in record.get("publishers") or [] if item.get("name")]
    tags_html = "".join(f"<span>{escape(str(tag))}</span>" for tag in [*domains, *capabilities, *publishers][:8])
    why = record.get("whyItMatters")
    motivation = record.get("motivation")
    released = record.get("releasedAt") or "Unknown"
    readiness = record.get("readiness") or "Unknown"
    schema = {
        "@context": "https://schema.org", "@type": "WebPage", "@id": f"{canonical}#webpage",
        "url": canonical, "name": f"{name} Benchmark", "description": description,
        "isPartOf": {"@id": f"{BASE_URL}/#website"},
        "about": {"@type": "Thing", "name": name, "description": description},
        "datePublished": record.get("releasedAt"), "publisher": {"@id": f"{BASE_URL}/#publisher"},
    }
    schema = {key: value for key, value in schema.items() if value is not None}
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(name)} Benchmark | Benchmark Radar</title><meta name="description" content="{escape(description[:300], quote=True)}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1"><link rel="canonical" href="{canonical}"><link rel="alternate" type="application/rss+xml" href="{BASE_URL}/feed.xml" title="Benchmark Radar updates"><link rel="icon" href="/benchmark-radar-mark.png" type="image/png" sizes="167x167"><meta property="og:type" content="article"><meta property="og:site_name" content="Benchmark Radar"><meta property="og:title" content="{escape(name, quote=True)} Benchmark"><meta property="og:description" content="{escape(description[:300], quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE_URL}/social-preview.png"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script><link rel="stylesheet" href="/detail.css"></head>
<body><header><a class="brand" href="/"><img src="/benchmark-radar-mark.png" width="26" height="26" alt="">Benchmark Radar</a><nav><a href="/#radar">Radar</a><a href="/benchmarks/">Browse benchmarks</a><a href="/about/">About</a></nav></header>
<main><nav class="crumb" aria-label="Breadcrumb"><a href="/">Benchmark Radar</a> / <a href="/benchmarks/">Benchmarks</a> / {escape(name)}</nav><article><div class="eyebrow">AI BENCHMARK PROFILE</div><h1>{escape(name)}</h1><div class="tags">{tags_html}</div><p class="lede">{escape(description)}</p><dl><div><dt>Released</dt><dd>{escape(str(released))}</dd></div><div><dt>Readiness</dt><dd>{escape(str(readiness))}</dd></div><div><dt>Primary field</dt><dd>{escape(str(record.get("primaryDomain") or "General AI"))}</dd></div></dl>{f'<section><h2>Why it matters</h2><p>{escape(str(why))}</p></section>' if why else ''}{f'<section><h2>Motivation</h2><p>{escape(str(motivation))}</p></section>' if motivation and motivation != why else ''}<section><h2>Primary resources</h2><div class="resources">{resource_links(record)}</div></section><p class="source-note">Benchmark Radar records only publicly supported details and links back to primary sources for verification.</p></article></main><footer><a href="/">Benchmark Radar</a> · <a href="/feed.xml">RSS</a> · <a href="https://github.com/Claire1217/benchmark-radar">GitHub</a></footer></body></html>'''


def benchmark_index(records: list[dict], data_as_of: str) -> str:
    rows = "".join(
        f'<li><a href="/{record_path(record)}"><strong>{escape(str(record.get("name") or "Unnamed"))}</strong><span>{escape(str(record.get("primaryDomain") or "General AI"))}</span></a></li>'
        for record in sorted(records, key=lambda item: str(item.get("name") or "").casefold())
    )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Benchmark Library | Benchmark Radar</title><meta name="description" content="Browse {len(records):,} public AI benchmarks with source-grounded descriptions, fields, release dates, readiness, papers, code, and datasets."><meta name="robots" content="index,follow"><link rel="canonical" href="{BASE_URL}/benchmarks/"><link rel="alternate" type="application/rss+xml" href="{BASE_URL}/feed.xml" title="Benchmark Radar updates"><link rel="icon" href="/benchmark-radar-mark.png" type="image/png" sizes="167x167"><link rel="stylesheet" href="/detail.css"></head><body><header><a class="brand" href="/"><img src="/benchmark-radar-mark.png" width="26" height="26" alt="">Benchmark Radar</a><nav><a href="/#radar">Radar</a><a href="/benchmarks/" aria-current="page">Browse benchmarks</a><a href="/about/">About</a></nav></header><main><article class="directory"><div class="eyebrow">PUBLIC AI EVALUATION INDEX</div><h1>AI Benchmark Library</h1><p class="lede">Browse {len(records):,} public benchmarks tracked by Benchmark Radar. Updated {escape(data_as_of)}.</p><ul class="benchmark-directory">{rows}</ul></article></main><footer><a href="/">Benchmark Radar</a> · <a href="/feed.xml">RSS</a> · <a href="https://github.com/Claire1217/benchmark-radar">GitHub</a></footer></body></html>'''


def write_feed(records: list[dict], data_as_of: str) -> None:
    recent = sorted(records, key=lambda item: (str(item.get("releasedAt") or ""), str(item.get("name") or "")), reverse=True)[:50]
    build_date = format_datetime(datetime.fromisoformat(data_as_of).replace(tzinfo=timezone.utc))
    items = []
    for record in recent:
        url = f"{BASE_URL}/{record_path(record)}"
        released = datetime.fromisoformat(record.get("releasedAt") or data_as_of).replace(tzinfo=timezone.utc)
        description = record.get("description") or record.get("oneLine") or "Public AI benchmark indexed by Benchmark Radar."
        items.append(f'<item><title>{xml_escape(str(record.get("name") or "Unnamed benchmark"))}</title><link>{url}</link><guid isPermaLink="true">{url}</guid><pubDate>{format_datetime(released)}</pubDate><description>{xml_escape(str(description))}</description></item>')
    content = f'''<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>Benchmark Radar updates</title><link>{BASE_URL}/</link><description>New and updated public AI benchmarks indexed by Benchmark Radar.</description><language>en</language><lastBuildDate>{build_date}</lastBuildDate><atom:link xmlns:atom="http://www.w3.org/2005/Atom" href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>{''.join(items)}</channel></rss>\n'''
    (OUTPUT / "feed.xml").write_text(content, encoding="utf-8")


def write_sitemap(records: list[dict], data_as_of: str) -> None:
    entries = [(f"{BASE_URL}/", data_as_of), (f"{BASE_URL}/about/", None), (f"{BASE_URL}/benchmarks/", data_as_of)]
    entries.extend((f"{BASE_URL}/{record_path(record)}", record.get("releasedAt")) for record in records)
    body = "".join(f"  <url><loc>{xml_escape(url)}</loc>{f'<lastmod>{lastmod}</lastmod>' if lastmod else ''}</url>\n" for url, lastmod in entries)
    (OUTPUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}</urlset>\n', encoding="utf-8")


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
    records = [record for record in library["records"] if visible(record)]
    data_as_of = library["manifest"]["dataAsOf"]
    benchmark_root = OUTPUT / "benchmarks"
    benchmark_root.mkdir()
    (benchmark_root / "index.html").write_text(benchmark_index(records, data_as_of), encoding="utf-8")
    for record in records:
        target = OUTPUT / record_path(record)
        target.mkdir(parents=True)
        (target / "index.html").write_text(detail_page(record), encoding="utf-8")
    write_feed(records, data_as_of)
    write_sitemap(records, data_as_of)
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built={OUTPUT} benchmark_pages={len(records)}")


if __name__ == "__main__":
    main()

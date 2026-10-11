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
    expected_ids = {"radar-view", "library-view", "saved-count", "benchmark-list", "library-list", "library-domain-list"}
    if missing := expected_ids - set(document.ids):
        raise SystemExit(f"missing interactive regions: {sorted(missing)}")
    app = (OUTPUT / "app.js").read_text(encoding="utf-8")
    styles = (OUTPUT / "styles.css").read_text(encoding="utf-8")
    if 'sort:"attention"' not in app:
        raise SystemExit("Attention must remain the default sort")
    if "description-toggle" in app or "details-panel" in app:
        raise SystemExit("descriptions must display directly without secondary disclosure controls")
    if 'button.textContent=previous?"Show the previous day with results":""' not in app:
        raise SystemExit("Latest must offer a date-free previous-day control")
    if "state.latestFrom=latestAvailableDate()" not in app:
        raise SystemExit("Latest must automatically fall back to the newest non-empty day")
    if "dayDivider" in app or ".day-divider" in styles:
        raise SystemExit("Latest must rely on card dates without redundant day dividers")
    if "new IntersectionObserver" in app:
        raise SystemExit("previous days must load only after an explicit button click")
    if 'evaluationMode!=="viewpoint_probe"' not in app:
        raise SystemExit("viewpoint probes must remain outside public views")
    if any(f'href="#{route}"' not in html for route in ("library", "saved")):
        raise SystemExit("Library, Saved, or Trends navigation missing")
    if 'href="./trends/"' not in html:
        raise SystemExit("Trends page navigation missing")
    trends = (OUTPUT / "trends/index.html").read_text(encoding="utf-8")
    trends_document = Document()
    trends_document.feed(trends)
    if len(trends_document.ids) != len(set(trends_document.ids)):
        raise SystemExit("duplicate Trends HTML id")
    if 'href="../model-evals/"' not in trends or 'href="./model-evals/"' in trends:
        raise SystemExit("Trends must link to the top-level Model Evals page")
    script_ref = re.search(r'src="./(trends\.js\?v=[a-f0-9]{12})"', trends)
    if not script_ref:
        raise SystemExit("Versioned Trends script missing")
    trends_script = (OUTPUT / "trends" / urlsplit(script_ref[1]).path).read_text()
    data_ref = re.search(r"../data/(trends_topics\.json\?v=[a-f0-9]{12})", trends_script)
    if not data_ref:
        raise SystemExit("Versioned Trends data connection missing")
    topic_data = json.loads((OUTPUT / "data" / urlsplit(data_ref[1]).path).read_text())
    if not topic_data.get("topics"):
        raise SystemExit("Trends topics empty")
    if not topic_data.get("coverage", {}).get("completeHistories"):
        raise SystemExit("Trends star-history coverage empty")
    if not all(rule in styles for rule in (".library-domains{position:sticky", "overflow-y:auto", "overscroll-behavior:contain")):
        raise SystemExit("desktop Library sidebar must scroll independently")
    for name in ("benchmarks_index.json", "library_index.json"):
        json.loads((OUTPUT / "data" / name).read_text(encoding="utf-8"))
    for name in ("robots.txt", "sitemap.xml", "feed.xml", "llms.txt", "social-preview.png", "about/index.html", "model-evals/index.html", "3bf256ad2bac3dbab62facad3a131fdd.txt"):
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
    repository = next(
        (item for item in schema["@graph"] if item.get("@type") == "SoftwareSourceCode"),
        None,
    )
    if not repository or repository.get("codeRepository") != "https://github.com/Claire1217/benchmark-radar":
        raise SystemExit("official GitHub repository schema missing")
    pages = validate_static_pages(OUTPUT)
    model_evals = (OUTPUT / "model-evals" / "index.html").read_text(encoding="utf-8")
    if '<link rel="canonical" href="https://benchmark-radar.com/model-evals/">' not in model_evals:
        raise SystemExit("Model Evals canonical production URL missing")
    if "Model Evals" not in document_title(model_evals):
        raise SystemExit("Model Evals page title missing")
    print(f"validated_static_site assets={len(document.scripts) + len(document.styles)} ids={len(document.ids)} static_pages={pages}")


class StaticPage(HTMLParser):
    """Title, canonical, H1 count and JSON-LD blocks of one generated page."""
    def __init__(self) -> None:
        super().__init__()
        self.titles: list[str] = []
        self.canonical: list[str] = []
        self.h1 = 0
        self.json_ld: list[str] = []
        self.ids: list[str] = []
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical.append(str(values.get("href")))
        self.h1 += tag == "h1"
        if tag == "title":
            self._capture = "title"
            self.titles.append("")
        if tag == "script" and values.get("type") == "application/ld+json":
            self._capture = "json"
            self.json_ld.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("title", "script"):
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._capture == "title":
            self.titles[-1] += data
        elif self._capture == "json":
            self.json_ld[-1] += data


def validate_static_pages(output: Path) -> int:
    """Every generated page is indexable and every sitemap URL is a built page."""
    base = "https://benchmark-radar.com"
    library = json.loads((output / "data" / "library_index.json").read_text(encoding="utf-8"))
    visible = [r for r in library["records"] if r.get("displayEligible") is not False and r.get("evaluationMode") != "viewpoint_probe"]
    categories = [d["id"] for d in library["manifest"]["libraryTaxonomy"]["directions"]]
    pages = sorted(output.glob("benchmarks/*/index.html")) + sorted(output.glob("categories/*/index.html"))
    pages += [output / "benchmarks" / "index.html", output / "categories" / "index.html"]
    if len(list(output.glob("benchmarks/*/index.html"))) != len(visible):
        raise SystemExit("one static page per visible Library record expected")
    if missing := [c for c in categories if not (output / "categories" / c / "index.html").exists()]:
        raise SystemExit(f"missing category pages: {missing}")
    titles = []
    for page in pages:
        path = "/" + page.parent.relative_to(output).as_posix() + "/"
        parsed = StaticPage()
        parsed.feed(page.read_text(encoding="utf-8"))
        if len(parsed.titles) != 1 or "Benchmark Radar" not in parsed.titles[0]:
            raise SystemExit(f"{path}: one Benchmark Radar title expected")
        if parsed.canonical != [base + path]:
            raise SystemExit(f"{path}: canonical must be {base + path}")
        if parsed.h1 != 1:
            raise SystemExit(f"{path}: exactly one h1 expected")
        if len(parsed.ids) != len(set(parsed.ids)):
            raise SystemExit(f"{path}: duplicate HTML id")
        if len(parsed.json_ld) != 1:
            raise SystemExit(f"{path}: one JSON-LD block expected")
        try:
            graph = json.loads(parsed.json_ld[0])["@graph"]
        except (ValueError, KeyError) as error:
            raise SystemExit(f"{path}: invalid JSON-LD ({error})")
        types = {item.get("@type") for item in graph}
        expected = "Dataset" if path.count("/") == 3 and path.startswith("/benchmarks/") else "CollectionPage"
        if not {expected, "BreadcrumbList"} <= types:
            raise SystemExit(f"{path}: JSON-LD needs {expected} and BreadcrumbList")
        titles.append(parsed.titles[0])
    if len(titles) != len(set(titles)):
        raise SystemExit("static page titles must be unique")
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    sitemap = ET.parse(output / "sitemap.xml").getroot()
    locations = []
    for url in sitemap.findall(namespace + "url"):
        location = url.findtext(namespace + "loc") or ""
        modified = url.findtext(namespace + "lastmod")
        if not location.startswith(base + "/") or not (output / location[len(base) + 1:] / "index.html").exists():
            raise SystemExit(f"sitemap URL has no built page: {location}")
        if modified is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", modified):
            raise SystemExit(f"sitemap lastmod must be a date: {location}")
        locations.append(location)
    if len(locations) != len(set(locations)) or len(locations) > 50000:
        raise SystemExit("sitemap URLs must be unique and fit one file")
    expected_urls = {base + p for p in ("/", "/about/", "/model-evals/", "/trends/", "/benchmarks/", "/categories/")}
    if missing := expected_urls - set(locations) or {base + "/" + p.parent.relative_to(output).as_posix() + "/" for p in pages} - set(locations):
        raise SystemExit(f"sitemap misses pages: {sorted(missing)[:5]}")
    feed = ET.parse(output / "feed.xml").getroot()
    for link in feed.iter("link"):
        target = (link.text or "").removeprefix(base + "/").split("#")[0]
        if target and not (output / target / "index.html").exists():
            raise SystemExit(f"feed item links to a missing page: {link.text}")
    for name, marker in (("llms.txt", "<!-- CATEGORY_LIST -->"), ("index.html", "<!-- STATIC_CATEGORY_LINKS -->")):
        text = (output / name).read_text(encoding="utf-8")
        if marker in text or "/categories/" not in text or "/benchmarks/" not in text:
            raise SystemExit(f"{name} must link the static benchmark and category pages")
    for name in ("about/index.html", "trends/index.html", "model-evals/index.html"):
        if 'href="/categories/"' not in (output / name).read_text(encoding="utf-8").replace('href="../categories/"', 'href="/categories/"'):
            raise SystemExit(f"{name} must link the category index")
    return len(pages)


def document_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


if __name__ == "__main__":
    main()

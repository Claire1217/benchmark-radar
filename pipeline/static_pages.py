"""Crawlable static pages for every Library benchmark and category.

The Library is a hash-routed app (/#library?direction=math), which crawlers and
AI search do not read. This writes plain HTML that needs no JavaScript or data
download: /benchmarks/<slug>/, /categories/<id>/, both indexes, sitemap.xml and
llms-full.txt. Pages state only what the record holds; a missing value is left
out, never filled in.

Slugs come from the benchmark name and are reserved over every record, hidden
ones included, so a visibility change never moves another page. When names
collide, the record seen first keeps the plain slug and later ones add a short
hash of their stable id; a newcomer is always seen later, so existing URLs hold.

Sitemap lastmod is the newest dated review of the record itself (first seen,
curation, copy, description, publisher, release-date and catalog reviews,
model-report dates), capped at dataAsOf. Daily star and vote refreshes are not
content changes, so they do not resubmit thousands of URLs to IndexNow.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import html
import json
import math
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

BASE_URL = "https://benchmark-radar.com"
WEBSITE_ID = BASE_URL + "/#website"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
RELATED_COUNT = 8
SLUG_LIMIT = 60
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
GREEK = re.compile(r"GREEK (?:SMALL|CAPITAL) LETTER (\w+)")
SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
ACCENTS = {"=": "\u0304", "'": "\u0301", "`": "\u0300", "^": "\u0302", '"': "\u0308", "~": "\u0303", ".": "\u0307",
           "u": "\u0306", "v": "\u030c", "H": "\u030b", "c": "\u0327", "k": "\u0328", "r": "\u030a", "b": "\u0331",
           "d": "\u0323", "t": "\u0361"}
# Same labels as the Library card (web/app.js).
ROLE_LABELS = {"suite-with-grounding-track": "Includes grounding tracks", "subset": "Evaluation subset",
               "version": "Benchmark version", "validation-split": "Validation split", "test-split": "Test split",
               "observation-setting": "Observation setting", "interactive-suite": "Interactive tasks",
               "benchmark-with-adapter": "Benchmark · adapter available", "suite": "Benchmark suite",
               "aggregate-index": "Aggregate index · not a standalone benchmark"}
MISSING_NOTE = "Missing signals remain unknown rather than being converted to zero."
POLICY_NOTE = ("Benchmark Radar is a discovery index, not a benchmark-quality endorsement or a model leaderboard. "
               "When citing a benchmark, cite its original paper, project, code or dataset.")
esc = lambda value: html.escape(str(value), quote=True)


# Names -----------------------------------------------------------------------

def _accent(name: str) -> str:
    """Apply the TeX accents benchmarkNameHtml supports (\\={a} → ā)."""
    name = re.sub(r"""\\([="'`^~.])\s*(?:\{([^{}])\}|([A-Za-z]))""",
                  lambda m: unicodedata.normalize("NFC", (m[2] or m[3]) + ACCENTS[m[1]]), name)
    return re.sub(r"\\([uvHckbdtr])\s*\{([^{}])\}", lambda m: unicodedata.normalize("NFC", m[2] + ACCENTS[m[1]]), name)


def name_text(name: str) -> str:
    """Plain-text display name for titles, meta tags and JSON-LD."""
    text = _accent(str(name or "")).replace("$\\tau^\\tau$", "τ^τ")
    return re.sub(r"\$\^\{?(\d+)\}?\$", lambda m: m[1].translate(SUPERSCRIPT), text)


def name_html(name: str) -> str:
    """Mirror web/benchmark-name.js: escaped text plus the two supported superscripts."""
    text = esc(_accent(str(name or "")))
    text = text.replace("$\\tau^\\tau$", "τ<sup>τ</sup>")
    return re.sub(r"\$\^\{?(\d+)\}?\$", r"<sup>\1</sup>", text)


def slugify(name: str, limit: int = SLUG_LIMIT) -> str:
    """Lowercase ASCII slug; Greek letters are spelled out (τ²-bench → tau2-bench)."""
    out = []
    for ch in unicodedata.normalize("NFKD", name_text(name)):
        if ch.isascii():
            out.append(ch)
        elif unicodedata.category(ch) != "Mn":
            greek = GREEK.match(unicodedata.name(ch, ""))
            out.append(greek[1].lower() if greek else "-")
    slug = re.sub(r"[^a-z0-9]+", "-", "".join(out).lower()).strip("-")
    if len(slug) > limit:
        slug = slug[:limit + 1].rsplit("-", 1)[0] if "-" in slug[:limit + 1] else slug[:limit]
    return slug.strip("-")


def id_hash(identity: str) -> str:
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()[:6]


def assign_slugs(records: list[dict]) -> dict[str, str]:
    """Stable id → slug; the first-seen record of a name keeps the plain slug."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[slugify(record.get("name") or "") or "benchmark"].append(record)
    slugs = {}
    for base, members in groups.items():
        members.sort(key=lambda r: (str(r.get("firstSeenAt") or "9999"), r["id"]))
        for position, record in enumerate(members):
            slugs[record["id"]] = base if position == 0 else f"{base}-{id_hash(record['id'])}"
    if len(set(slugs.values())) != len(slugs):
        raise ValueError("benchmark slugs collide")
    return slugs


# Record facts (same rules as the Library card in web/app.js) -----------------

def trim(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(" ", 1)[0] if " " in text[:limit - 1] else text[:limit - 1]
    return cut.rstrip(" ,;:.-–—") + "…"


def copy_text(record: dict) -> str:
    value = record.get("description") or record.get("oneLine") or ""
    if re.match(r"^Established benchmark (family|variant)\s*·", value, re.I):
        value = ""
    detail = record.get("detail") or {}
    return " ".join(str(value or detail.get("description") or detail.get("task") or "").split())


def safe_url(url) -> str | None:
    return url if isinstance(url, str) and re.match(r"^https?://", url, re.I) else None


def report_label(url: str) -> str:
    if re.search(r"github\.com/", url, re.I):
        return "Code"
    if re.search(r"huggingface\.co/datasets/", url, re.I):
        return "Data"
    if re.search(r"(?:arxiv\.org|openreview\.net|doi\.org)/", url, re.I) or re.search(r"\.pdf(?:[?#]|$)", url, re.I):
        return "Paper"
    return "Source"


def resource_links(record: dict) -> list[tuple[str, str]]:
    links = record.get("links") or {}
    report = safe_url(links.get("report"))
    items = [(report_label(report) if report else "", report), ("Paper", links.get("paper")),
             ("Project", links.get("project")), ("Code", links.get("code")), ("Data", links.get("data")),
             ("Hugging Face paper", links.get("hfPaper"))]
    seen, out = set(), []
    for label, url in items:
        url = safe_url(url)
        if url and url not in seen:
            seen.add(url)
            out.append((label, url))
    return out


def release(record: dict) -> dict | None:
    """Display label, precision-trimmed date and source; None when unverified."""
    precision, value = record.get("releaseDatePrecision"), str(record.get("releasedAt") or "")
    if precision == "unknown" or not DATE.match(value) or value.startswith("0001"):
        return None
    date = value[:4] if precision == "year" else value[:7] if precision == "month" else value[:10]
    evidence = record.get("releaseEvidence") or {}
    label = ("Results disclosed" if evidence.get("dateScope") == "public-disclosure"
             else "Dataset published" if evidence.get("dateScope") == "underlying-dataset"
             else "Paper published" if evidence.get("basis") == "paper-v1"
             else "Announced" if evidence.get("basis") == "official-announcement" else "Released")
    source = evidence.get("sourceUrl") or (record.get("firstRelease") or {}).get("sourceUrl") or ""
    return {"label": label, "date": date, "source": source if re.match(r"^https://", source, re.I) else None}


def publishers(record: dict) -> list[str]:
    names = [p.get("name") for p in record.get("publishers") or [] if p.get("role") == "benchmark-publisher"]
    return list(dict.fromkeys(n for n in names if n))


def publication_label(record: dict) -> str:
    p = record.get("publication") or {}
    if not p or p.get("status") in (None, "unverified"):
        return ""
    label = {"published": "Published", "accepted": "Accepted", "acceptance_claimed": "Acceptance claimed"}.get(
        p["status"], "Publication reported")
    return label + (f" · {p['venue']}" if p.get("venue") else "")


def hosted_repo(record: dict) -> bool:
    attention = record.get("attention") or {}
    return attention.get("githubScope") == "hosting_repo" or bool(
        re.search(r"github\.com/[^/]+/[^/]+/(?:tree|blob)/", (record.get("links") or {}).get("code") or "", re.I))


def signals(record: dict) -> list[tuple[str, str]]:
    """Observed public signals, each with its observation note."""
    attention = record.get("attention") or {}
    status = attention.get("signalStatus") or {}
    def observed(key):
        when = str((status.get(key) or {}).get("observedAt") or attention.get("observedAt") or attention.get("asOf") or "")
        return f"observed {when[:10]}" if when else ""
    out = []
    if attention.get("hfPaperUpvotes") is not None:
        out.append((f"{attention['hfPaperUpvotes']:,} Hugging Face paper votes", observed("hfPaperUpvotes")))
    if attention.get("githubStars") is not None and not hosted_repo(record):
        out.append((f"{attention['githubStars']:,} GitHub stars", observed("githubStars")))
    if attention.get("hfDatasetDownloads") is not None:
        out.append((f"{attention['hfDatasetDownloads']:,} dataset downloads", observed("hfDatasetDownloads")))
    growth = record.get("growth") or {}
    stars = growth.get("githubStars") or {}
    for window, label in (("3m", "3 months"), ("1m", "1 month")):
        if stars.get(window) is not None and not hosted_repo(record):
            through = f"through {growth['starsThrough']}" if growth.get("starsThrough") else ""
            out.append((f"{stars[window]:+,} GitHub stars gained in {label}", through))
            break
    return out


def attention_maxima(records: list[dict]) -> dict:
    maxima = {}
    for key in ("hfPaperUpvotes", "githubStars", "hfDatasetDownloads"):
        values = [0 if key == "githubStars" and (r.get("attention") or {}).get("githubScope") == "hosting_repo"
                  else (r.get("attention") or {}).get(key) or 0 for r in records]
        maxima[key] = max([1, *values])
    return maxima


def library_attention(record: dict, maxima: dict) -> int | None:
    """The Library's default sort score (libraryAttention in web/app.js)."""
    attention = record.get("attention") or {}
    score, observed = 0.0, False
    for key, weight in (("hfPaperUpvotes", .15), ("githubStars", .55), ("hfDatasetDownloads", .30)):
        value = attention.get(key)
        if value is None or (key == "githubStars" and attention.get("githubScope") == "hosting_repo"):
            score += weight * .5
            continue
        observed = True
        score += weight * math.log1p(value) / math.log1p(maxima[key])
    return round(score * 100) if observed else None


def record_lastmod(record: dict, as_of: str) -> str:
    """Newest dated review of the record's own content, capped at dataAsOf."""
    dates = [record.get("firstSeenAt")]
    for field in ("curation", "descriptionProvenance", "publisherProvenance"):
        dates.append((record.get(field) or {}).get("reviewedAt"))
    dates.append((record.get("copyGeneration") or {}).get("generatedAt"))
    dates.append((record.get("releaseEvidence") or {}).get("checkedAt"))
    dates += [s.get("reviewedAt") for s in record.get("catalogSources") or []]
    dates += [s.get("modelDate") for s in record.get("modelReportReferences") or []]
    found = [d[:10] for d in dates if isinstance(d, str) and DATE.match(d)]
    return min(max(found), as_of) if found else as_of


# Page shell ------------------------------------------------------------------

def json_ld(graph: list[dict]) -> str:
    text = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    # Unicode escapes keep data from closing or confusing the script element.
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def breadcrumb(items: list[tuple[str, str]]) -> dict:
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": name, "item": BASE_URL + path}
        for i, (name, path) in enumerate(items, 1)]}


def crumbs_html(items: list[tuple[str, str]]) -> str:
    links = [f'<a href="{esc(path)}">{esc(name)}</a>' for name, path in items[:-1]]
    return f'<nav class="crumbs" aria-label="Breadcrumb">{" › ".join(links)}</nav>'


def site_header(index_html: str) -> str:
    """The homepage topbar with root-relative links, Library marked current."""
    header = re.search(r'<header class="topbar">.*?</header>', index_html, re.S)[0]
    header = header.replace('href="#', 'href="/#').replace('href="./', 'href="/').replace('src="./', 'src="/')
    header = re.sub(r'\s*data-route="[^"]*"', "", header).replace(' <span id="saved-count">0</span>', "")
    return header.replace('<a href="/#library">Library</a>', '<a href="/#library" class="active">Library</a>')


class Shell:
    def __init__(self, output: Path, data_as_of: str):
        self.output, self.data_as_of = output, data_as_of
        self.header = site_header((output / "index.html").read_text(encoding="utf-8"))
        self.assets = {name: f"/{name}?v={hashlib.sha256((output / name).read_bytes()).hexdigest()[:12]}"
                       for name in ("site-header.css", "github-repositories.css", "static-pages.css", "github-repositories.js")}

    def page(self, path: str, title: str, description: str, body: str, graph: list[dict]) -> str:
        url = BASE_URL + path
        meta = "".join([
            f'<meta property="og:{k}" content="{esc(v)}">' for k, v in (
                ("type", "website"), ("site_name", "Benchmark Radar"), ("title", title), ("description", description),
                ("url", url), ("image", BASE_URL + "/social-preview.png"))
        ] + [f'<meta name="twitter:{k}" content="{esc(v)}">' for k, v in (
            ("card", "summary_large_image"), ("title", title), ("description", description),
            ("image", BASE_URL + "/social-preview.png"))])
        styles = "".join(f'<link rel="stylesheet" href="{self.assets[n]}">'
                         for n in ("site-header.css", "github-repositories.css", "static-pages.css"))
        return (
            '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f"<title>{esc(title)}</title>\n<meta name=\"description\" content=\"{esc(description)}\">\n"
            '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">\n'
            f'<link rel="canonical" href="{esc(url)}">\n{meta}\n'
            f'<script type="application/ld+json">{json_ld(graph)}</script>\n'
            '<link rel="icon" href="/benchmark-radar-mark.png" type="image/png" sizes="167x167">\n'
            f"{styles}\n</head>\n<body>\n{self.header}\n<main class=\"static-page\">\n{body}\n</main>\n"
            '<footer><span>Official Benchmark Radar website · Primary-source index.</span>'
            '<span><a href="/#library">Interactive Library</a> · <a href="/benchmarks/">All benchmarks</a> · '
            '<a href="/categories/">Categories</a> · <a href="/trends/">Trends</a></span>'
            '<span><a href="/about/">About</a> · <a href="/feed.xml">RSS</a> · <a href="/llms.txt">AI access</a></span></footer>\n'
            f'<script src="{self.assets["github-repositories.js"]}" defer></script>\n</body>\n</html>\n'
        )

    def write(self, path: str, text: str) -> None:
        target = self.output / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


# Pages -----------------------------------------------------------------------

def item_html(record: dict, slug: str, limit: int = 180) -> str:
    when = release(record)
    date = f' <span class="date">{esc(when["date"])}</span>' if when else ""
    summary = trim(copy_text(record), limit)
    return (f'<li><a href="/benchmarks/{slug}/">{name_html(record["name"])}</a>{date}'
            + (f"<p>{esc(summary)}</p>" if summary else "") + "</li>")


def benchmark_page(shell: Shell, record: dict, ctx: dict) -> str:
    slug = ctx["slugs"][record["id"]]
    path = f"/benchmarks/{slug}/"
    name = name_text(record["name"])
    categories = [c for c in record.get("libraryCategories") or [] if c in ctx["categories"]]
    primary = ctx["categories"][categories[0]] if categories else None
    copy = copy_text(record)
    when = release(record)
    sources = resource_links(record)
    names = publishers(record)
    aliases = [name_text(a) for a in record.get("aliases") or [] if a and a != record["name"]]
    suffix = f" ({ctx['labels'][record['id']]})" if record["id"] in ctx["labels"] else ""
    if primary:
        title = (f"{name}{suffix} — {primary['name']} benchmark | Benchmark Radar" if "bench" in name.lower()
                 else f"{name} benchmark{suffix} — {primary['name']} | Benchmark Radar")
    else:
        title = f"{name}{suffix} — AI benchmark | Benchmark Radar"
    fallback = f"{name} is a public AI benchmark indexed by Benchmark Radar" + (
        f" under {primary['name']}." if primary else ".")
    description = trim(copy, 155) or fallback

    facts = []
    if categories:
        facts.append(("Categories", " · ".join(
            f'<a href="/categories/{c}/">{esc(ctx["categories"][c]["name"])}</a>' for c in categories)))
    if when:
        text = esc(f"{when['label']} {when['date']}")
        facts.append(("Release", f'<a href="{esc(when["source"])}" rel="noopener">{text}</a>' if when["source"] else text))
    else:
        facts.append(("Release", "Release date unverified"))
    if names:
        facts.append(("Published by", esc(" · ".join(names))))
    if publication_label(record):
        facts.append(("Publication", esc(publication_label(record))))
    if record.get("evaluationRole") in ROLE_LABELS:
        facts.append(("Type", esc(ROLE_LABELS[record["evaluationRole"]])))
    if aliases:
        facts.append(("Also known as", esc(" · ".join(dict.fromkeys(aliases)))))
    body = [crumbs_html(ctx["crumbs"](record, name)),
            f'<p class="eyebrow">AI benchmark{" · " + esc(primary["name"]) if primary else ""}</p>',
            f'<h1>{name_html(record["name"])}</h1>',
            f'<p class="lead">{esc(copy)}</p>' if copy else
            '<p class="lead">Task summary not yet available. See the original source for the evaluation protocol.</p>']
    notes = []
    if (record.get("descriptionProvenance") or {}).get("basis") == "catalog-import-unverified":
        notes.append("Catalog summary · not independently verified")
    if record.get("identityReviewNote"):
        notes.append("Version under review")
    if notes:
        body.append(f'<p class="note">{esc(" · ".join(notes))}</p>')
    body.append('<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts) + "</dl>")
    if sources:
        body.append('<section><h2>Primary sources</h2><ul class="links">' + "".join(
            f'<li><a href="{esc(url)}" rel="noopener">{esc(label)} ↗</a></li>' for label, url in sources) + "</ul></section>")
    observed = "".join(f"<li>{esc(text)}" + (f' <span class="date">{esc(note)}</span>' if note else "") + "</li>"
                       for text, note in signals(record))
    body.append("<section><h2>Public attention</h2>" + (f"<ul>{observed}</ul>" if observed else
                "<p>No public attention signal has been observed for this benchmark yet.</p>")
                + f'<p class="note">{MISSING_NOTE} Attention reflects public interest, not benchmark quality.</p></section>')
    reports, seen = [], set()
    for ref in record.get("modelReportReferences") or []:
        key = (ref.get("provider"), ref.get("model"))
        if key in seen or not ref.get("model"):
            continue
        seen.add(key)
        label = esc(" ".join(filter(None, [ref.get("provider"), ref.get("model")])))
        url = safe_url(ref.get("url"))
        link = f'<a href="{esc(url)}" rel="noopener">{label}</a>' if url else label
        date = f' <span class="date">{esc(ref["modelDate"])}</span>' if ref.get("modelDate") else ""
        reports.append(f"<li>{link}{date}</li>")
    usage = []
    if reports:
        usage.append(f"<p>Referenced in {len(reports)} tracked model report{'s' if len(reports) != 1 else ''}.</p>"
                     f"<ul>{''.join(reports[:12])}</ul>" + (f"<p>and {len(reports) - 12} more.</p>" if len(reports) > 12 else ""))
    if record.get("catalogModelCount"):
        count = record["catalogModelCount"]
        usage.append(f"<p>{count:,} tracked model{'s' if count != 1 else ''} on llm-stats.</p>")
    if usage:
        body.append("<section><h2>Use in model reports</h2>" + "".join(usage) + "</section>")
    body.append(f'<p class="actions"><a href="/#library?q={quote(record["name"])}">Open in the interactive Library →</a></p>')
    if primary:
        related = [r for r in ctx["members"][primary["id"]] if r["id"] != record["id"]][:RELATED_COUNT]
        if related:
            body.append(f'<section><h2>Related {esc(primary["name"])} benchmarks</h2><ul class="items">'
                        + "".join(item_html(r, ctx["slugs"][r["id"]], 140) for r in related)
                        + f'</ul><p><a href="/categories/{primary["id"]}/">All {len(ctx["members"][primary["id"]]):,} '
                          f'{esc(primary["name"])} benchmarks →</a></p></section>')
    body.append(f'<p class="note">Data as of {esc(shell.data_as_of)}. {esc(POLICY_NOTE)}</p>')

    dataset = {"@type": "Dataset", "@id": BASE_URL + path + "#dataset", "name": name, "description": copy or fallback,
               "url": BASE_URL + path, "isPartOf": {"@id": WEBSITE_ID}}
    if aliases:
        dataset["alternateName"] = list(dict.fromkeys(aliases))
    if sources:
        dataset["sameAs"] = [url for _, url in sources]
    if when:
        dataset["datePublished"] = when["date"]
    if categories:
        dataset["keywords"] = [ctx["categories"][c]["name"] for c in categories]
    if names:
        dataset["creator"] = [{"@type": "Organization", "name": n} for n in names]
    return shell.page(path, title, description, "\n".join(body), [dataset, breadcrumb(ctx["crumbs"](record, name))])


def category_page(shell: Shell, category: dict, ctx: dict) -> str:
    path = f"/categories/{category['id']}/"
    members = ctx["members"][category["id"]]
    primary_count = sum((r.get("libraryCategories") or [None])[0] == category["id"] for r in members)
    title = f"{category['name']} benchmarks — {len(members):,} AI benchmarks | Benchmark Radar"
    intro = f"{category['description']} Benchmark Radar lists {len(members):,} public AI benchmarks in this category."
    crumbs = [("Home", "/"), ("Categories", "/categories/"), (category["name"], path)]
    siblings = [c for c in ctx["categories"].values() if c["group"] == category["group"] and c["id"] != category["id"]]
    links = [f'<a href="/#library?direction={quote(category["id"])}">Open in the interactive Library →</a>']
    if category["id"] in ctx["trend_ids"]:
        links.append(f'<a href="/trends/#c={quote(category["id"])}">See the {esc(category["name"])} trend →</a>')
    body = [crumbs_html(crumbs), f'<p class="eyebrow">{esc(category["section"])}</p>',
            f"<h1>{esc(category['name'])} benchmarks</h1>", f'<p class="lead">{esc(intro)}</p>',
            f'<p class="note">{primary_count:,} have this as their primary category; the rest list it as a secondary category. '
            f"Sorted by public attention, as in the Library. {MISSING_NOTE}</p>",
            f'<p class="actions">{" ".join(links)}</p>',
            '<ol class="items">' + "".join(item_html(r, ctx["slugs"][r["id"]]) for r in members) + "</ol>"]
    if siblings:
        body.append(f'<section><h2>More {esc(category["section"])} categories</h2><ul class="links">' + "".join(
            f'<li><a href="/categories/{c["id"]}/">{esc(c["name"])}</a> · {len(ctx["members"][c["id"]]):,}</li>'
            for c in siblings) + "</ul></section>")
    body.append(f'<p class="note">Data as of {esc(shell.data_as_of)}. {esc(POLICY_NOTE)}</p>')
    graph = [{"@type": "CollectionPage", "@id": BASE_URL + path, "url": BASE_URL + path, "name": title,
              "description": intro, "isPartOf": {"@id": WEBSITE_ID},
              "mainEntity": {"@type": "ItemList", "numberOfItems": len(members), "itemListElement": [
                  {"@type": "ListItem", "position": i, "url": f"{BASE_URL}/benchmarks/{ctx['slugs'][r['id']]}/",
                   "name": name_text(r["name"])} for i, r in enumerate(members, 1)]}},
             breadcrumb(crumbs)]
    return shell.page(path, title, trim(intro, 155), "\n".join(body), graph)


def first_letter(record: dict) -> str:
    letter = unicodedata.normalize("NFKD", name_text(record["name"]).lstrip())[:1].upper()
    return letter if "A" <= letter <= "Z" else "#"


def benchmarks_index(shell: Shell, records: list[dict], ctx: dict) -> str:
    path = "/benchmarks/"
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in sorted(records, key=lambda r: (name_text(r["name"]).casefold(), r["id"])):
        groups[first_letter(record)].append(record)
    letters = sorted(groups, key=lambda k: (k != "#", k))
    title = f"All AI benchmarks A–Z — {len(records):,} benchmarks | Benchmark Radar"
    intro = (f"Every public AI benchmark in the Benchmark Radar Library, {len(records):,} in all, from papers, code, "
             "datasets and model reports. Each links to a page with its sources, release date and categories.")
    def entry(r):
        label = f' <span class="date">{esc(ctx["labels"][r["id"]])}</span>' if r["id"] in ctx["labels"] else ""
        return f'<li><a href="/benchmarks/{ctx["slugs"][r["id"]]}/">{name_html(r["name"])}</a>{label}</li>'
    body = [crumbs_html([("Home", "/"), ("Benchmarks", path)]), '<p class="eyebrow">Benchmark Library</p>',
            "<h1>All AI benchmarks A–Z</h1>", f'<p class="lead">{esc(intro)}</p>',
            '<p class="actions"><a href="/categories/">Browse by category →</a> <a href="/#library">Search the interactive Library →</a></p>',
            '<nav class="letters" aria-label="Jump to letter">' + "".join(
                f'<a href="#letter-{"0" if k == "#" else k.lower()}">{esc(k)}</a>' for k in letters) + "</nav>"]
    for k in letters:
        body.append(f'<section id="letter-{"0" if k == "#" else k.lower()}"><h2>{esc(k)}</h2><ul class="az">'
                    + "".join(entry(r) for r in groups[k]) + "</ul></section>")
    body.append(f'<p class="note">Data as of {esc(shell.data_as_of)}. {esc(POLICY_NOTE)}</p>')
    graph = [{"@type": "CollectionPage", "@id": BASE_URL + path, "url": BASE_URL + path, "name": title,
              "description": intro, "isPartOf": {"@id": WEBSITE_ID}},
             breadcrumb([("Home", "/"), ("Benchmarks", path)])]
    return shell.page(path, title, trim(intro, 155), "\n".join(body), graph)


def categories_index(shell: Shell, groups: list[dict], ctx: dict) -> str:
    path = "/categories/"
    categories = list(ctx["categories"].values())
    title = f"AI benchmark categories — {len(categories)} research directions | Benchmark Radar"
    intro = (f"The {len(categories)} categories Benchmark Radar uses across Library, Trends and Radar. A benchmark has "
             "one primary category and up to two secondary ones, so categories overlap.")
    body = [crumbs_html([("Home", "/"), ("Categories", path)]), '<p class="eyebrow">Benchmark Library</p>',
            "<h1>AI benchmark categories</h1>", f'<p class="lead">{esc(intro)}</p>',
            '<p class="actions"><a href="/benchmarks/">All benchmarks A–Z →</a> <a href="/trends/">Category trends →</a></p>']
    for group in groups:
        members = [c for c in categories if c["group"] == group["id"]]
        if members:
            body.append(f'<section><h2>{esc(group["name"])}</h2><ul class="categories">' + "".join(
                f'<li><a href="/categories/{c["id"]}/">{esc(c["name"])}</a> <span class="date">'
                f'{len(ctx["members"][c["id"]]):,} benchmarks</span><p>{esc(c["description"])}</p></li>'
                for c in members) + "</ul></section>")
    body.append(f'<p class="note">Data as of {esc(shell.data_as_of)}. {esc(POLICY_NOTE)}</p>')
    graph = [{"@type": "CollectionPage", "@id": BASE_URL + path, "url": BASE_URL + path, "name": title,
              "description": intro, "isPartOf": {"@id": WEBSITE_ID},
              "mainEntity": {"@type": "ItemList", "numberOfItems": len(categories), "itemListElement": [
                  {"@type": "ListItem", "position": i, "url": f"{BASE_URL}/categories/{c['id']}/", "name": c["name"]}
                  for i, c in enumerate(categories, 1)]}},
             breadcrumb([("Home", "/"), ("Categories", path)])]
    return shell.page(path, title, trim(intro, 155), "\n".join(body), graph)


# Discovery files -------------------------------------------------------------

def sitemap_xml(entries: list[tuple[str, str | None]]) -> str:
    rows = []
    for path, lastmod in entries:
        modified = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        rows.append(f"  <url><loc>{xml_escape(BASE_URL + path)}</loc>{modified}</url>")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="{SITEMAP_NS}">\n' + "\n".join(rows) + "\n</urlset>\n"


def llms_full(records: list[dict], ctx: dict, as_of: str) -> str:
    lines = ["# Benchmark Radar: all benchmarks", "",
             f"> {len(records):,} public AI benchmarks in the Benchmark Radar Library, data as of {as_of}. One line per "
             "benchmark: name and page, primary category, release date, summary. Discovery index, not an endorsement; "
             "cite the original source.", ""]
    for r in sorted(records, key=lambda r: (name_text(r["name"]).casefold(), r["id"])):
        categories = [c for c in r.get("libraryCategories") or [] if c in ctx["categories"]]
        when = release(r)
        parts = [ctx["categories"][categories[0]]["name"] if categories else "Uncategorised",
                 when["date"] if when else "release date unverified"]
        summary = trim(copy_text(r), 160)
        lines.append(f"- [{name_text(r['name'])}]({BASE_URL}/benchmarks/{ctx['slugs'][r['id']]}/): "
                     + " · ".join(parts) + (f" · {summary}" if summary else ""))
    return "\n".join(lines) + "\n"


def category_lines(ctx: dict) -> str:
    return "\n".join(f"- [{c['name']}]({BASE_URL}/categories/{c['id']}/): {len(ctx['members'][c['id']]):,} benchmarks. {c['description']}"
                     for c in ctx["categories"].values())


LLMS_MARKER = "<!-- CATEGORY_LIST -->"
NOSCRIPT_MARKER = "<!-- STATIC_CATEGORY_LINKS -->"
DISCOVERY_NAV = ('<nav class="site-index" aria-label="Browse benchmarks" style="max-width:1180px;margin:24px auto 0;'
                 'padding:16px 24px 28px;border-top:1px solid #dedfdb;font:11px/1.6 system-ui,sans-serif;color:#6b7280">'
                 '<a href="/benchmarks/" style="color:inherit">All benchmarks A–Z</a> · '
                 '<a href="/categories/" style="color:inherit">Benchmark categories</a> · '
                 '<a href="/about/" style="color:inherit">About</a></nav>')


def link_existing_pages(output: Path, ctx: dict) -> None:
    """Crawlable entry points from the app pages, llms.txt and the homepage noscript."""
    llms = output / "llms.txt"
    llms.write_text(llms.read_text(encoding="utf-8").replace(LLMS_MARKER, category_lines(ctx)), encoding="utf-8")
    index = output / "index.html"
    links = " · ".join(f'<a href="./categories/{c["id"]}/">{esc(c["name"])}</a>' for c in ctx["categories"].values())
    index.write_text(index.read_text(encoding="utf-8").replace(NOSCRIPT_MARKER, f"<p>{links}</p>"), encoding="utf-8")
    for name in ("trends/index.html", "model-evals/index.html"):
        page = output / name
        text = page.read_text(encoding="utf-8")
        if 'class="site-index"' not in text:
            page.write_text(text.replace("</main>", "</main>" + DISCOVERY_NAV, 1), encoding="utf-8")


def duplicate_labels(records: list[dict]) -> dict[str, str]:
    """Same-name records are told apart by release date, then arXiv id or id hash."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[name_text(record["name"]).casefold()].append(record)
    labels = {}
    for group in groups.values():
        if len(group) < 2:
            continue
        dates = [(release(r) or {}).get("date", "") for r in group]
        for record, date in zip(group, dates):
            if not date or dates.count(date) > 1:
                source = record.get("source") or {}
                extra = f"arXiv {source['id']}" if source.get("type") == "arxiv" and source.get("id") else id_hash(record["id"])
                date = f"{date} · {extra}" if date else extra
            labels[record["id"]] = date
    return labels


def write_static_pages(output: Path, library: dict, visible, trends_ids: set[str] = frozenset(),
                       page_dates: dict[str, str | None] | None = None) -> dict:
    """Write every static page plus sitemap.xml and llms-full.txt; return page counts."""
    manifest = library["manifest"]
    as_of = manifest["dataAsOf"]
    taxonomy = manifest["libraryTaxonomy"]
    sections = {g["id"]: g["name"] for g in taxonomy["groups"]}
    categories = {d["id"]: {**d, "section": d.get("section") or sections.get(d["group"], "")} for d in taxonomy["directions"]}
    records = [r for r in library["records"] if visible(r)]
    slugs = assign_slugs(library["records"])
    maxima = attention_maxima(library["records"])
    def rank(record):
        score = library_attention(record, maxima)
        return (-(score if score is not None else -1), name_text(record["name"]).casefold(), record["id"])
    members: dict[str, list[dict]] = {c: [] for c in categories}
    for record in sorted(records, key=rank):
        for c in record.get("libraryCategories") or []:
            if c in members:
                members[c].append(record)
    labels = duplicate_labels(records)

    def crumbs(record, name):
        primary = next((c for c in record.get("libraryCategories") or [] if c in categories), None)
        middle = [("Categories", "/categories/"), (categories[primary]["name"], f"/categories/{primary}/")] if primary \
            else [("Benchmarks", "/benchmarks/")]
        return [("Home", "/"), *middle, (name, f"/benchmarks/{slugs[record['id']]}/")]

    ctx = {"slugs": slugs, "categories": categories, "members": members, "trend_ids": set(trends_ids), "crumbs": crumbs,
           "labels": labels}
    shell = Shell(output, as_of)
    lastmods = {r["id"]: record_lastmod(r, as_of) for r in records}
    newest = max(lastmods.values(), default=as_of)
    for record in records:
        shell.write(f"/benchmarks/{slugs[record['id']]}/", benchmark_page(shell, record, ctx))
    for category in categories.values():
        shell.write(f"/categories/{category['id']}/", category_page(shell, category, ctx))
    shell.write("/benchmarks/", benchmarks_index(shell, records, ctx))
    shell.write("/categories/", categories_index(shell, taxonomy["groups"], ctx))

    entries = list((page_dates or {}).items())
    entries += [("/benchmarks/", newest), ("/categories/", newest)]
    entries += [(f"/categories/{c}/", max((lastmods[r["id"]] for r in members[c]), default=as_of)) for c in categories]
    entries += [(f"/benchmarks/{slugs[r['id']]}/", lastmods[r["id"]])
                for r in sorted(records, key=lambda r: slugs[r["id"]])]
    (output / "sitemap.xml").write_text(sitemap_xml(entries), encoding="utf-8")
    (output / "llms-full.txt").write_text(llms_full(records, ctx, as_of), encoding="utf-8")
    link_existing_pages(output, ctx)
    return {"benchmarks": len(records), "categories": len(categories), "sitemap": len(entries)}

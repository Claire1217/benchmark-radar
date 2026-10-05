"""Give catalog-only records the paper (and code/data) they were reviewed against.

Catalog rows (llm-stats, BenchLM...) link to the catalog page, so the signal
fetch had no paper to look up on Hugging Face. Two reviewed sources name the
original paper: release-date evidence based on the paper's v1 (reviewed
identity match), and BenchLM's own paperUrl. Only arXiv papers are used, and
an existing paper link is never replaced. data/catalog_source_alignments.json
holds verified paper/code/dataset links for entries neither source covers.
"""
from __future__ import annotations
import json
from pathlib import Path
import re

ALIGNMENTS = Path(__file__).resolve().parents[1] / 'data/catalog_source_alignments.json'
PAPER_REPOS = Path(__file__).resolve().parents[1] / 'data/paper_repository_links.json'

ARXIV = re.compile(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})')


def has_paper(links):
    return any(ARXIV.search(links.get(k) or '') for k in ('paper', 'report', 'pdf', 'hfPaper'))


def reviewed_paper(record):
    evidence = record.get('releaseEvidence') or {}
    if evidence.get('basis') == 'paper-v1' and (m := ARXIV.search(evidence.get('sourceUrl') or '')):
        return f'https://arxiv.org/abs/{m[1]}', 'release-evidence'
    papers = {m[1] for s in record.get('catalogSources') or [] if (m := ARXIV.search(s.get('paperUrl') or ''))}
    if len(papers) == 1:  # conflicting catalog papers are left for review
        return f'https://arxiv.org/abs/{papers.pop()}', 'catalog-paper-url'
    return None, None


def apply_alignments(records, alignments):
    by_id = {r['id']: r for r in records}
    applied = 0
    for rid, item in alignments.items():
        record = by_id.get(rid)
        if record is None:
            continue
        links = record.setdefault('links', {})
        if item.get('metricScopes'):
            record['metricScopes'] = {**item['metricScopes'], **(record.get('metricScopes') or {})}
        for field, key in (('paper', 'paper'), ('code', 'code'), ('dataset', 'data')):
            url = item.get(field)
            if not url or links.get(key) or (key == 'paper' and has_paper(links)):
                continue
            links[key] = url
            applied += 1
            if key == 'paper':
                record['paperLinkBasis'] = 'source-alignment'
    return applied


def apply_paper_repositories(records, links):
    """Author-linked repositories from the paper text; only fills a missing code link."""
    by_id = {r['id']: r for r in records}
    for rid, item in links.items():
        record = by_id.get(rid)
        if record is None or (record.get('links') or {}).get('code'):
            continue
        record.setdefault('links', {})['code'] = item['code']
        record['codeLinkBasis'] = item['source']
        if item.get('scope') == 'hosting_repo':
            record['metricScopes'] = {'github': 'hosting_repo', **(record.get('metricScopes') or {})}


def link_reviewed_papers(records, alignments=None, paper_repos=None):
    if alignments is None and ALIGNMENTS.exists():
        alignments = json.loads(ALIGNMENTS.read_text()).get('records', {})
    if paper_repos is None and PAPER_REPOS.exists():
        paper_repos = json.loads(PAPER_REPOS.read_text()).get('records', {})
    apply_alignments(records, alignments or {})
    linked = 0
    for record in records:
        links = record.setdefault('links', {})
        if has_paper(links):
            continue
        url, basis = reviewed_paper(record)
        if url:
            links['paper'] = url
            record['paperLinkBasis'] = basis
            linked += 1
    apply_paper_repositories(records, paper_repos or {})
    return linked

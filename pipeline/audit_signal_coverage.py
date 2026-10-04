#!/usr/bin/env python3
"""Measure how many visible Library records carry each public signal.

Writes data/signal_coverage.json. Coverage is reported against all visible
records and against records whose source is known (e.g. stars among records
with a GitHub repository), so a missing link and a missing fetch are
distinguishable.
"""
from datetime import date
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GITHUB = re.compile(r'github\.com/([^/\s#?]+/[^/\s#?]+)')
ARXIV = re.compile(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})')


def visible(r):
    return r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe'


def github_repo(r):
    a, links = r.get('attention') or {}, r.get('links') or {}
    for url in (a.get('githubRepo'), links.get('code'), links.get('project')):
        if url and (m := GITHUB.search(url)):
            return m[1].lower().removesuffix('.git')
    return None


def arxiv_id(r):
    links = r.get('links') or {}
    for url in (links.get('paper'), links.get('report'), links.get('pdf'), links.get('hfPaper')):
        if url and (m := ARXIV.search(url)):
            return m[1]
    if (m := re.search(r'huggingface\.co/papers/(\d{4}\.\d{4,5})', links.get('hfPaper') or '')):
        return m[1]
    return None


def hf_dataset(r):
    url = (r.get('links') or {}).get('data') or ''
    return 'huggingface.co/datasets/' in url


def exact_date(r):
    # Same rule as Trends: Radar records carry an arXiv day without a precision field.
    return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', r.get('releasedAt') or '')) and r.get('releasedAt') != '0001-01-01' \
        and r.get('releaseDatePrecision') not in ('year', 'month', 'unknown')


def coverage(records, history):
    complete = {re.sub(r'^https?://(www\.)?', '', h['url']).lower().rstrip('/').removeprefix('github.com/')
                for h in history.get('records', []) if h.get('status') == 'complete'}
    rows = [r for r in records if visible(r)]
    def share(n, d):
        return {'count': n, 'of': d, 'share': round(n / d, 4) if d else None}
    repo = [r for r in rows if github_repo(r)]
    paper = [r for r in rows if arxiv_id(r)]
    dataset = [r for r in rows if hf_dataset(r)]
    att = lambda r, k: (r.get('attention') or {}).get(k) is not None
    return {
        'records': len(rows),
        'githubRepo': share(len(repo), len(rows)),
        'githubStars': share(sum(att(r, 'githubStars') for r in repo), len(repo)),
        'githubStarHistory': share(sum(github_repo(r) in complete for r in repo), len(repo)),
        'arxivPaper': share(len(paper), len(rows)),
        'hfPaperUpvotes': share(sum(att(r, 'hfPaperUpvotes') for r in paper), len(paper)),
        'hfDataset': share(len(dataset), len(rows)),
        'hfDatasetDownloads': share(sum(att(r, 'hfDatasetDownloads') for r in dataset), len(dataset)),
        'exactReleaseDate': share(sum(exact_date(r) for r in rows), len(rows)),
        'noSignal': share(sum(not any(att(r, k) for k in ('githubStars', 'hfPaperUpvotes', 'hfDatasetDownloads')) for r in rows), len(rows)),
    }


def main():
    load = lambda name: json.loads((ROOT / 'data' / name).read_text())
    result = {'asOf': load('library_index.json')['manifest'].get('dataAsOf') or date.today().isoformat(),
              **coverage(load('library_index.json')['records'], load('github_star_history.json'))}
    (ROOT / 'data/signal_coverage.json').write_text(json.dumps(result, indent=2) + '\n')
    for key, value in result.items():
        if isinstance(value, dict):
            print(f"{key:20s} {value['count']:5d} / {value['of']:5d}  {value['share']:.1%}")


if __name__ == '__main__':
    main()

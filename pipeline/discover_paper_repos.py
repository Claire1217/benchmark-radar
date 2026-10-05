#!/usr/bin/env python3
"""Find benchmark code repositories that the paper authors link themselves.

For Library records with an arXiv paper but no GitHub link, read the paper's
abstract and comments from its arXiv page and keep GitHub links written there
by the authors ("Code is available at github.com/..."). Each candidate is
checked with the GitHub API: it must exist, forks resolve to their upstream,
and a link into a subfolder (/tree/...) is recorded as a shared hosting
repository so its stars are not credited to the benchmark alone.

Results go to data/paper_repository_links.json; paper_links.py applies them
only where a record has no code link.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/paper_repository_links.json'
ATOM = '{http://www.w3.org/2005/Atom}'
ARXIV_NS = '{http://arxiv.org/schemas/atom}'
GITHUB_LINK = re.compile(r'github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)((?:/tree|/blob)/[^\s)\]}>,;"\']*)?', re.I)
NOT_REPOS = {'features', 'topics', 'orgs', 'settings', 'marketplace', 'sponsors', 'about'}


def norm(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', (text or '').lower())


def candidate_links(text: str) -> list[dict]:
    """GitHub repositories mentioned in text, in order, deduplicated."""
    found, seen = [], set()
    for owner, repo, path in GITHUB_LINK.findall(text or ''):
        repo = re.sub(r'\.(git|md|html?)$', '', repo.rstrip('.'), flags=re.I)
        if owner.lower() in NOT_REPOS or not repo:
            continue
        key = f'{owner}/{repo}'.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append({'owner': owner, 'repo': repo, 'subpath': bool(path)})
    return found


def pick(candidates: list[dict], name: str) -> dict | None:
    """Prefer a repository whose name matches the benchmark; otherwise the only one."""
    if not candidates:
        return None
    target = norm(name)
    for c in candidates:
        repo = norm(c['repo'])
        if target and repo and (target in repo or repo in target):
            return c
    return candidates[0] if len(candidates) == 1 else None


BACKOFF = [30, 60, 120, 300]  # arXiv rate limits last minutes, not seconds


def arxiv_entries(ids: list[str], fetch=None, sleep=time.sleep) -> dict[str, str]:
    """arXiv id -> abstract + comment text (one API call per 100 ids)."""
    fetch = fetch or (lambda url: urlopen(Request(url, headers={'User-Agent': 'BenchmarkRadar'}), timeout=60).read())
    out = {}
    for start in range(0, len(ids), 100):
        batch = ids[start:start + 100]
        url = 'https://export.arxiv.org/api/query?max_results=100&id_list=' + ','.join(batch)
        for attempt, wait in enumerate(BACKOFF + [None]):
            try:
                root = ET.fromstring(fetch(url))
                break
            except (HTTPError, URLError, TimeoutError, ET.ParseError):
                if wait is None:
                    raise
                sleep(wait)
        for entry in root.findall(ATOM + 'entry'):
            identifier = (entry.findtext(ATOM + 'id') or '').rsplit('/', 1)[-1]
            arxiv_id = re.sub(r'v\d+$', '', identifier)
            out[arxiv_id] = ' '.join(filter(None, [entry.findtext(ATOM + 'summary'), entry.findtext(ARXIV_NS + 'comment')]))
        if start + 100 < len(ids):
            sleep(3)  # arXiv API guidance: one request every three seconds
    return out


ABSTRACT = re.compile(r'<blockquote class="abstract[^"]*">([\s\S]*?)</blockquote>')
COMMENTS = re.compile(r'<td class="tablecell comments[^"]*">([\s\S]*?)</td>')


def abs_page_text(html: str) -> str:
    """Abstract + comments of an arXiv abs page, with link targets spelled out.

    arXiv renders URLs as "this https URL" anchors, so hrefs carry the address.
    """
    parts = []
    for block in ABSTRACT.findall(html) + COMMENTS.findall(html):
        parts += re.findall(r'href="([^"]+)"', block)
        parts.append(re.sub(r'<[^>]+>', ' ', block))
    return ' '.join(parts)


def abs_pages(ids: list[str], fetch=None, sleep=time.sleep, on_page=None) -> dict[str, str]:
    """arXiv id -> text from https://arxiv.org/abs/<id>, one page every 3 seconds."""
    def default_fetch(url):
        return urlopen(Request(url, headers={'User-Agent': 'BenchmarkRadar (https://github.com/Claire1217/benchmark-radar)'}), timeout=60).read().decode('utf-8', 'ignore')
    fetch = fetch or default_fetch
    out = {}
    for n, arxiv_id in enumerate(ids):
        for wait in BACKOFF + [None]:
            try:
                out[arxiv_id] = abs_page_text(fetch('https://arxiv.org/abs/' + arxiv_id))
                break
            except HTTPError as error:
                if error.code == 404:
                    break
                if wait is None:
                    raise
                sleep(wait)
            except (URLError, TimeoutError):
                if wait is None:
                    raise
                sleep(wait)
        if on_page:
            on_page(n)
        sleep(3)
    return out


def github_repo(owner: str, repo: str, token: str | None, get=None) -> dict | None:
    def default_get(path):
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'BenchmarkRadar'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        try:
            return json.loads(urlopen(Request('https://api.github.com/repos/' + path, headers=headers), timeout=30).read())
        except HTTPError as error:
            if error.code in (404, 451):
                return None
            raise
    get = get or default_get
    info = get(f'{owner}/{repo}')
    if info and info.get('fork') and (info.get('parent') or {}).get('full_name'):
        info = get(info['parent']['full_name']) or info
    return info


def resolve(record: dict, text: str, token: str | None, get=None) -> dict | None:
    choice = pick(candidate_links(text), record['name'])
    if not choice:
        return None
    info = github_repo(choice['owner'], choice['repo'], token, get)
    if not info or not info.get('full_name'):
        return None
    return {'code': 'https://github.com/' + info['full_name'],
            'scope': 'hosting_repo' if choice['subpath'] else 'benchmark_repo',
            'source': 'arxiv-abstract-or-comment', 'arxiv': record['arxiv']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'pipeline'))
    from audit_signal_coverage import arxiv_id, github_repo as record_repo, visible
    library = json.loads((ROOT / 'data/library_index.json').read_text())['records']
    payload = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'records': {}, 'checked': {}}
    rows = [{'id': r['id'], 'name': r['name'], 'arxiv': arxiv_id(r)} for r in library
            if visible(r) and arxiv_id(r) and not record_repo(r) and r['id'] not in payload['checked']]
    if args.limit:
        rows = rows[:args.limit]
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    found = 0
    for start in range(0, len(rows), 25):  # save every 25 papers so a stopped run resumes
        batch = rows[start:start + 25]
        texts = abs_pages(sorted({r['arxiv'] for r in batch}))
        for row in batch:
            result = resolve(row, texts.get(row['arxiv'], ''), token)
            payload['checked'][row['id']] = date.today().isoformat()
            if result:
                payload['records'][row['id']] = result
                found += 1
        payload['method'] = __doc__.strip().split('\n\n')[1].replace('\n', ' ')
        payload['records'] = dict(sorted(payload['records'].items()))
        payload['checked'] = dict(sorted(payload['checked'].items()))
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
        print(f'checked {start + len(batch)}/{len(rows)}: found so far {found}', flush=True)
    print(f'paper_repos checked={len(rows)} found={found} total={len(payload["records"])}')


if __name__ == '__main__':
    main()

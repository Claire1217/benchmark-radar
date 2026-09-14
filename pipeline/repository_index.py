"""Apply source-linked GitHub mappings without guessing among candidates."""
from pathlib import Path
import json
import re


def safe_github(url):
    return bool(isinstance(url, str) and re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[^\s<>"\']*)?', url))


def apply_repository_index(records, registry):
    entries = {row['id']: row for row in registry.get('records', [])}
    for record in records:
        entry = entries.get(record['id'])
        if not entry:
            continue
        linked = [c for c in entry.get('candidates', []) if c.get('verified') and safe_github(c.get('url'))]
        associations = [{
            'url': c['url'], 'scope': c.get('scope', 'unresolved'),
            'verification': 'source-linked', 'evidence': c.get('evidence', []),
        } for c in linked]
        record['githubIndex'] = {
            'status': entry['status'], 'indexedAt': registry.get('generatedAt'),
            'repositories': associations,
            'candidateCount': sum(not c.get('verified') for c in entry.get('candidates', [])),
        }
        # An existing canonical Code link wins. Never choose arbitrarily among
        # multiple repositories or promote a reference-only candidate.
        if record.get('links', {}).get('code') or len(linked) != 1:
            continue
        candidate = linked[0]
        pointers = [e.get('linkedUrl') for e in candidate.get('evidence', []) if safe_github(e.get('linkedUrl'))]
        code = next((u for u in pointers if '/tree/' in u or '/blob/' in u), candidate['url'])
        record.setdefault('links', {})['code'] = code
        record['githubIndex']['addedCodeLink'] = True
        record['githubIndex']['selectedScope'] = candidate.get('scope', 'unresolved')
    return records


def load_and_apply(records, data_dir):
    source = Path(data_dir) / 'github_repository_index.json'
    if source.exists():
        registry = json.loads(source.read_text())
        availability = Path(data_dir) / 'github_star_history.json'
        if availability.exists():
            unavailable = {r['url'].lower() for r in json.loads(availability.read_text()).get('records', []) if r.get('status') == 'http-404'}
            for entry in registry.get('records', []):
                for candidate in entry.get('candidates', []):
                    if candidate.get('url', '').lower() in unavailable:
                        candidate['verified'] = False
                        candidate['availability'] = 'github-history-404'
        apply_repository_index(records, registry)
    return records

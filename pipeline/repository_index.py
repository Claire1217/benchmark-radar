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
        reviews = Path(data_dir) / 'repository_link_reviews.json'
        if reviews.exists():
            by_id = {r['id']: r for r in registry['records']}
            for review in json.loads(reviews.read_text()).get('reviews', []):
                entry = by_id.get(review['id'])
                if not entry: continue
                for candidate in entry.get('candidates', []):
                    candidate['verified'] = candidate['url'].lower().rstrip('/') == review['url'].lower().rstrip('/')
                    if candidate['verified']: candidate['scope'] = review['scope']
                entry['status'] = 'linked' if any(c['verified'] for c in entry.get('candidates', [])) else 'candidates'
        availability = Path(data_dir) / 'github_repository_availability.json'
        if availability.exists():
            from urllib.parse import urlparse
            observed = json.loads(availability.read_text())
            for entry in registry['records']:
                for candidate in entry.get('candidates', []):
                    key = '/'.join(urlparse(candidate['url']).path.strip('/').lower().split('/')[:2])
                    if observed.get(key, {}).get('status') == 'http-404':
                        candidate['verified'] = False
                        candidate['availability'] = 'repository-metadata-404'
                entry['status'] = 'linked' if any(c.get('verified') for c in entry.get('candidates', [])) else 'candidates' if entry.get('candidates') else 'not-found'
        apply_repository_index(records, registry)
    return records

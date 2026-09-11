"""Two deterministic JSON commands for agents: search and show."""
import argparse
import json
import sys
from pathlib import Path
from usage_store import UsageStore, norm

class QueryError(Exception):
    def __init__(self, code, message, status, candidates=None):
        self.code, self.message, self.status, self.candidates = code, message, status, candidates

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise QueryError('invalid_arguments', message, 2)

def positive(value):
    n = int(value)
    if not 1 <= n <= 100:
        raise argparse.ArgumentTypeError('limit must be between 1 and 100')
    return n

def nonnegative(value):
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError('offset cannot be negative')
    return n

def labels(record, store):
    values = [record.get('primaryDomain', ''), *record.get('applicationDomains', []), *record.get('categories', []), *record.get('topics', [])]
    for rid in record.get('usageSourceIds', []):
        values += store.source_records[rid].get('categories', [])
    return sorted({v for v in values if isinstance(v, str) and v})

def run(argv=None):
    manifest = None
    try:
        parser = Parser(prog='benchmark-reader', description=__doc__)
        sub = parser.add_subparsers(dest='command', required=True)
        for name in ('search', 'show'):
            p = sub.add_parser(name)
            p.add_argument('query', nargs='?' if name == 'search' else None, default='')
            p.add_argument('--data-dir', type=Path, help='Directory containing library_index.json and usage/')
            p.add_argument('--limit', type=positive, default=20 if name == 'search' else 50)
            p.add_argument('--offset', type=nonnegative, default=0)
            if name == 'search':
                p.add_argument('--domain')
        args = parser.parse_args(argv)
        store = UsageStore(args.data_dir)
        store.source_records = {r['id']: r for r in store.records}
        manifest = store.manifest
        records = list(store.entities.values())
        if args.command == 'search':
            query = norm(args.query)
            found = []
            for r in records:
                names = [r['name'], *r.get('aliases', [])]
                if query and not any(query in norm(n) for n in names):
                    continue
                domains = labels(r, store)
                if args.domain:
                    target = norm(args.domain)
                    tokens = ('science', 'scientific') if target == 'science' else (target,)
                    if not any(token in norm(d) for token in tokens for d in domains):
                        continue
                found.append({'id': r['id'], 'name': r['name'], 'domains': domains,
                              'sourceIds': r.get('usageSourceIds', []), 'usage': store.summary(r.get('usageSourceIds', []))})
            found.sort(key=lambda r: (-r['usage']['reportedLabCount'], r['name'].casefold(), r['id']))
            data = {'results': found[args.offset:args.offset+args.limit], 'total': len(found),
                    'nextOffset': args.offset+args.limit if args.offset+args.limit < len(found) else None}
        else:
            if args.query in store.entities:
                entity = store.entities[args.query]
            elif args.query in store.alignment and store.alignment[args.query]['localId']:
                entity = store.entities[store.alignment[args.query]['localId']]
            else:
                matches = [r for r in records if norm(args.query) in {norm(r['name']), *(norm(a) for a in r.get('aliases', []))}]
                if not matches:
                    raise QueryError('not_found', 'No exact identity found; use search.', 3)
                if len(matches) != 1:
                    raise QueryError('ambiguous_identity', 'Use one of the exact IDs; versions and sources are not interchangeable.', 2,
                                     sorted([{'id': r['id'], 'name': r['name']} for r in matches], key=lambda r: r['id']))
                entity = matches[0]
            data = store.show(entity)
            count = len(data['observations'])
            data['observations'] = data['observations'][args.offset:args.offset+args.limit]
            data['pagination'] = {'observationTotal': count, 'nextOffset': args.offset+args.limit if args.offset+args.limit < count else None}
        print(json.dumps({'schemaVersion': '1.0', 'ok': True, 'data': data, 'coverage': manifest, 'error': None}, ensure_ascii=False))
        return 0
    except QueryError as e:
        error = {'code': e.code, 'message': e.message, 'candidates': e.candidates}; status = e.status
    except (OSError, ValueError, KeyError, TypeError) as e:
        error = {'code': 'invalid_database', 'message': str(e)}; status = 1
    print(json.dumps({'schemaVersion': '1.0', 'ok': False, 'data': None, 'coverage': manifest, 'error': error}, ensure_ascii=False))
    return status

if __name__ == '__main__':
    sys.exit(run())

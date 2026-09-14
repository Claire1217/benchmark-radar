"""Find benchmarks, explore hot releases, and inspect usage evidence."""
import argparse
import json
import sys
import sqlite3
from pathlib import Path
from usage_store import UsageStore, norm, ROOT
from search_index import SearchIndex, relevance_order

from cli_discovery import valid_date, discover, attention, attention_order, keyword_match, domain_match

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
    argv = list(sys.argv[1:] if argv is None else argv)
    args = None
    try:
        parser = Parser(prog='benchmark-reader', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                        epilog="""Examples:
  benchmark-reader search "scientific coding"
  benchmark-reader hot --window 7d --domain biology
  benchmark-reader daily --date 2026-09-13
  benchmark-reader show lib_gpqa_diamond --json

Output: always one JSON response, including errors. --json is optional.
Agent: inspect ok, error, coverage and nextOffset. Help is plain text.
Data: local checkout only. Run git pull to update. Hot means attention level, not growth.
Run benchmark-reader COMMAND --help for command options.""")
        def output_flags(p):
            p.add_argument('--json', action='store_true', help='Optional: JSON is always the default output')
        output_flags(parser)
        sub = parser.add_subparsers(dest='command', required=True)
        for name in ('search', 'show'):
            p = sub.add_parser(name, help={'search':'Find by name, keywords or domain', 'show':'Inspect one identity and its usage evidence', 'daily':'List releases or discoveries for one day', 'hot':'Rank recent releases by current attention'}[name], description={'search':'Find benchmarks. Exact names first, then relevance. Domain filters use stored labels.', 'show':'Inspect an ID returned by search. Ambiguous names return candidate IDs.', 'daily':'Defaults to latest indexed release date. No previous-day fill.', 'hot':'Filter by release date, rank by current attention. Not a growth or historical-score chart.'}[name])
            output_flags(p)
            p.add_argument('query', nargs='?' if name == 'search' else None, default='')
            p.add_argument('--data-dir', type=Path, help='Local data directory (default: repository data/)')
            p.add_argument('--limit', type=positive, default=20 if name == 'search' else 50)
            p.add_argument('--offset', type=nonnegative, default=0, help='Skip N results; use nextOffset from the previous response')
            if name == 'search':
                p.add_argument('--domain', help='Stored domain label, e.g. biology, chemistry, coding')
                p.add_argument('--sort', choices=['relevance', 'usage', 'attention', 'newest'], default='relevance')
                p.add_argument('--expand', action='append', default=[], help='Explicit alternative search terms; repeatable')
        for name in ('daily', 'hot'):
            p = sub.add_parser(name, help={'search':'Find by name, keywords or domain', 'show':'Inspect one identity and its usage evidence', 'daily':'List releases or discoveries for one day', 'hot':'Rank recent releases by current attention'}[name], description={'search':'Find benchmarks. Exact names first, then relevance. Domain filters use stored labels.', 'show':'Inspect an ID returned by search. Ambiguous names return candidate IDs.', 'daily':'Defaults to latest indexed release date. No previous-day fill.', 'hot':'Filter by release date, rank by current attention. Not a growth or historical-score chart.'}[name])
            output_flags(p)
            p.add_argument('query', nargs='?', default='')
            p.add_argument('--domain', help='Stored domain label, e.g. biology, chemistry, coding')
            p.add_argument('--limit', type=positive, default=20)
            p.add_argument('--offset', type=nonnegative, default=0, help='Skip N results; use nextOffset from the previous response')
            p.add_argument('--data-dir', type=Path, default=ROOT / 'data')
            if name == 'daily':
                p.add_argument('--date', type=valid_date, help='YYYY-MM-DD; default: latest indexed source date')
                p.add_argument('--basis', choices=['released', 'discovered'], default='released')
            else:
                p.add_argument('--window', choices=['7d', '30d', '90d'], default='7d')
                p.add_argument('--as-of', type=valid_date, help='Release-window end date; does not restore historical scores')
        args = parser.parse_args(argv)
        if args.command in {'daily', 'hot'}:
            payload = json.loads((args.data_dir / 'benchmarks_index.json').read_text())
            data = discover(payload, args)
            print(json.dumps({'schemaVersion': '1.2', 'ok': True, 'data': data, 'coverage': payload['manifest'], 'error': None}, ensure_ascii=False))
            return 0
        store = UsageStore(args.data_dir)
        store.source_records = {r['id']: r for r in store.records}
        manifest = store.manifest
        records = list(store.entities.values())
        if args.command == 'search':
            candidates = [r for r in records if r.get('displayEligible') is not False and r.get('evaluationMode') != 'viewpoint_probe']
            index = SearchIndex(candidates, lambda r: labels(r, store))
            try:
                hits, search_meta = index.search(args.query, args.expand)
            finally:
                index.close()
            found = []
            for r in candidates:
                if r.get('displayEligible') is False or r.get('evaluationMode') == 'viewpoint_probe':
                    continue
                domains = labels(r, store)
                if r['id'] not in hits or not domain_match(args.domain, domains):
                    continue
                found.append({'id': r['id'], 'name': r['name'], 'domains': domains,
                              'relevance': hits[r['id']], 'releasedAt': r.get('releasedAt'), 'description': r.get('oneLine') or r.get('description'), 'links': r.get('links', {}), 'attention': attention(r), 'sourceIds': r.get('usageSourceIds', []), 'usage': store.summary(r.get('usageSourceIds', []))})
            found.sort(key=lambda r: (-r['usage']['reportedLabCount'], r['name'].casefold(), r['id']))
            if args.sort == 'relevance':
                found.sort(key=relevance_order)
            elif args.sort == 'attention':
                found.sort(key=attention_order)
            elif args.sort == 'newest':
                found.sort(key=lambda r: r.get('releasedAt') or '', reverse=True)
            data = {'sort': args.sort, 'search': search_meta, 'domainFilter': {'value': args.domain, 'basis': 'stored labels only; missing labels may cause omissions'}, 'results': found[args.offset:args.offset+args.limit], 'total': len(found),
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
        print(json.dumps({'schemaVersion': '1.2', 'ok': True, 'data': data, 'coverage': manifest, 'error': None}, ensure_ascii=False))
        return 0
    except QueryError as e:
        error = {'code': e.code, 'message': e.message, 'candidates': e.candidates}; status = e.status
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as e:
        error = {'code': 'invalid_database', 'message': str(e)}; status = 1
    print(json.dumps({'schemaVersion': '1.2', 'ok': False, 'data': None, 'coverage': manifest, 'error': error}, ensure_ascii=False))
    return status

if __name__ == '__main__':
    sys.exit(run())

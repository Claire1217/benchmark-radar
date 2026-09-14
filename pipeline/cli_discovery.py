"""Read-only discovery queries over the site's published index."""
from datetime import date, timedelta
import math
from usage_store import norm


def valid_date(value):
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
        return value
    except (ValueError, TypeError):
        import argparse
        raise argparse.ArgumentTypeError('date must be YYYY-MM-DD')


def domain_match(domain, labels):
    if not domain:
        return True
    target = norm(domain)
    tokens = ('science', 'scientific') if target == 'science' else (target,)
    return any(token in norm(label) for token in tokens for label in labels)


def keyword_match(query, record, domains):
    text = ' '.join(str(x) for x in [record.get('name', ''), *record.get('aliases', []), record.get('oneLine', ''), record.get('description', ''), *domains])
    return all(norm(word) in norm(text) for word in query.split())


def attention(record):
    # One common population; never mix scores from different ranking windows.
    rank = record.get('ranking', {}).get('90d', {})
    score = rank.get('score')
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score):
        score = None
    return {'score': score, 'rankingWindow': '90d', 'confidence': rank.get('confidence'),
            'coverage': rank.get('coverage'), 'signals': record.get('attention', {})}


def attention_order(row):
    score = row['attention']['score']
    return (score is None, -(score or 0), row['name'].casefold(), row['id'])


def discover(payload, args):
    manifest = payload['manifest']
    end = args.date if args.command == 'daily' else args.as_of
    end = end or manifest.get('latestSourceDate') or manifest['dataAsOf']
    start = (date.fromisoformat(end) - timedelta(days=(1 if args.command == 'daily' else int(args.window[:-1])) - 1)).isoformat()
    basis = args.basis if args.command == 'daily' else 'released'
    field = 'releasedAt' if basis == 'released' else 'firstSeenAt'
    rows = []
    for record in payload['records']:
        if record.get('displayEligible') is False or record.get('evaluationMode') == 'viewpoint_probe':
            continue
        if not start <= (record.get(field) or '') <= end:
            continue
        domains = sorted({x for x in [record.get('primaryDomain', ''), *record.get('applicationDomains', []), *record.get('topics', [])] if x})
        if not domain_match(args.domain, domains) or not keyword_match(args.query, record, domains):
            continue
        rows.append({'id': record['id'], 'name': record['name'], 'description': record.get('oneLine'),
                     'releasedAt': record.get('releasedAt'), 'firstSeenAt': record.get('firstSeenAt'),
                     'domains': domains, 'links': record.get('links', {}), 'attention': attention(record)})
    rows.sort(key=attention_order)
    return {'results': rows[args.offset:args.offset + args.limit], 'total': len(rows),
            'nextOffset': args.offset + args.limit if args.offset + args.limit < len(rows) else None,
            'query': {'from': start, 'to': end, 'basis': basis, 'sort': 'attention', 'keyword': args.query, 'domain': args.domain},
            'ranking': {'window': '90d', 'meaning': 'Current attention level among benchmarks in the 90-day ranking population; not growth or historical scores.',
                        'unrankedCount': sum(r['attention']['score'] is None for r in rows), 'missingScores': 'null; sorted last'},
            'dataAsOf': manifest.get('dataAsOf'), 'latestSourceDate': manifest.get('latestSourceDate')}

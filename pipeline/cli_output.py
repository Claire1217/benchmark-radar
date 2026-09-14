"""Human-readable rendering of the same structured CLI response."""
import re
import shlex
import sys
import textwrap


def clean(value):
    return re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', str(value))


def render(envelope, args):
    data = envelope.get('data') or {}
    if not envelope['ok']:
        error = envelope['error']
        lines = [f"Error [{error['code']}]: {clean(error['message'])}"]
        for candidate in error.get('candidates') or []:
            lines.append(f"  {clean(candidate['name'])}\n    {clean(candidate['id'])}")
        lines.append('Use benchmark-reader --help for commands and examples.')
        return '\n'.join(lines)
    coverage = envelope.get('coverage') or {}
    lines = []
    if 'results' in data:
        query = data.get('query') or {}
        order = data.get('sort') or query.get('sort', 'attention')
        lines.append(f"{args.command.capitalize()} · {data['total']} results · sorted by {order}")
        if query:
            lines.append(f"{query['from']} to {query['to']} · {query['basis']} date")
        if getattr(args, 'query', ''):
            lines.append(f"Query: {clean(args.query)}")
        if getattr(args, 'domain', None):
            lines.append(f"Domain: {clean(args.domain)} (stored labels)")
        for i, row in enumerate(data['results'], args.offset + 1):
            score = (row.get('attention') or {}).get('score')
            lines.extend(['', f"{i}. {clean(row['name'])}", f"   ID: {clean(row['id'])}",
                          f"   Released: {row.get('releasedAt') or 'unknown'} · Attention: {score if score is not None else 'unmeasured'}"])
            if row.get('description'):
                lines.extend(textwrap.wrap(clean(row['description']), width=88, initial_indent='   ', subsequent_indent='   ', max_lines=3, placeholder=' …'))
            match = row.get('relevance')
            if match and match.get('matchedFields'):
                lines.append('   Match: ' + ', '.join(match['matchedFields']) + (' (exact ' + match['exactMatch'] + ')' if match.get('exactMatch') else ''))
        if not data['results']:
            lines.append('\nNo results on this page. Try fewer keywords, remove the domain filter, or reset --offset.')
            suggestions = data.get('search', {}).get('suggestions', [])
            if suggestions:
                lines.append('Possible names: ' + ', '.join(clean(x) for x in suggestions))
        next_offset = data.get('nextOffset')
        if next_offset is not None:
            lines.append(f'\nNext page: repeat this command with --offset {next_offset}')
        if data['results']:
            lines.append('\nInspect: benchmark-reader show ' + shlex.quote(data['results'][0]['id']))
        lines.append('Attention = current 90-day-population score, not growth or research quality.')
    else:
        bench = data['benchmark']; usage = data['usage']
        lines = [clean(bench['name']), 'ID: ' + clean(bench['id'])]
        if not bench.get('sourceIds'):
            lines.append('Usage evidence: no linked records; adoption is unknown.')
        else:
            lines.extend([f"Reporting organizations: {usage['reportedLabCount']} · Reports: {usage['reportCount']}",
                          f"Score records: {usage['scoreObservationCount']} (not execution count)",
                          'Organizations: ' + (', '.join(usage['reportedLabs']) or 'none in this snapshot')])
        lines.append(f"Saturation: {usage['saturation']} · Lifecycle: {usage['lifecycle']}")
        lines.append('\nSources:')
        for document in data.get('documents', []):
            lines.append('  ' + clean(document.get('source_url') or document['id']))
        pagination = data.get('pagination', {})
        if pagination.get('nextOffset') is not None:
            lines.append(f"More score records: --offset {pagination['nextOffset']} --json")
        lines.append('Use --json for complete observations, protocols and evidence fields.')
    as_of = coverage.get('dataAsOf') or coverage.get('latestRegisteredReportDate')
    if as_of:
        label = 'Index as of' if coverage.get('dataAsOf') else 'Latest imported vendor report'
        lines.append(f'\n{label}: {as_of}')
    lines.append('Local snapshot · git pull to update · --json for Agent output')
    return '\n'.join(lines)


def emit(envelope, args, mode):
    import json
    if mode == 'json':
        print(json.dumps(envelope, ensure_ascii=False))
    else:
        print(render(envelope, args), file=sys.stdout if envelope['ok'] else sys.stderr)

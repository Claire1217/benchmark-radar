"""Apply reviewed entity merges only; fuzzy names and shared papers are not identities."""
import copy


def merge_library_identities(records, decisions):
    by_id = {r['id']: copy.deepcopy(r) for r in records}
    redirects = {}
    for decision in decisions.get('merges', []):
        old_id, new_id = decision['fromId'], decision['toId']
        if old_id == new_id or new_id in redirects:
            raise ValueError('Identity merges must be direct and non-cyclic')
        if new_id not in by_id:
            raise ValueError(f'Canonical benchmark missing: {new_id}')
        redirects[old_id] = new_id
        old = by_id.pop(old_id, None)
        if old is None:
            continue
        target = by_id[new_id]
        target['aliases'] = sorted(set(target.get('aliases', []) + old.get('aliases', []) + [old['name']]) - {target['name']})
        target['mergedIds'] = sorted(set(target.get('mergedIds', []) + [old_id]))
        for field in ('catalogSources', 'sourceAttribution', 'modelReportReferences', 'usageObservations'):
            items = target.get(field, []) + old.get(field, [])
            seen = set()
            def key(item):
                import json
                if field == 'catalogSources':
                    return (item['catalog'], item.get('sourceId') or item['url'])
                return json.dumps(item, sort_keys=True)
            target[field] = [r for r in items if not (key(r) in seen or seen.add(key(r)))]
        for field in ('catalogCategories', 'topics'):
            target[field] = sorted(set(target.get(field, []) + old.get(field, [])))
        for field in ('catalogModelCount', 'catalogStarCount'):
            target[field] = max(target.get(field, 0), old.get(field, 0))
        target.setdefault('mergedRecordLinks', {})[old_id] = old.get('links', {})
        for kind, url in old.get('links', {}).items():
            if url and not target.setdefault('links', {}).get(kind):
                target['links'][kind] = url
    return sorted(by_id.values(), key=lambda r: (r['name'].casefold(), r['id'])), redirects

#!/usr/bin/env python3
"""Read-only ownership and referential-integrity audit; never repairs product data."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import fnmatch
import hashlib
import json
from pathlib import Path
import subprocess

from evidence_facets import POLICY_VERSION, digest, evidence_units
from source_identity import source_key

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'pipeline/data_contract.json'
BASELINE = ROOT / 'pipeline/data_contract_baseline.json'
SHARED_FIELDS = ('evidenceFacets', 'classificationEvidence', 'searchDocument', 'libraryCategories',
                 'categoryAssignment', 'researchTopics', 'evaluationRole')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON object key: ' + key)
        result[key] = value
    return result


def fingerprint(item: dict) -> str:
    return digest({k: item[k] for k in ('code', 'path', 'key', 'details')})


class Audit:
    def __init__(self, root: Path):
        self.root = root
        self.cache = {}
        self.findings = []

    def add(self, code, path, key, details, action, severity='error'):
        row = dict(code=code, path=path, key=str(key), details=details, action=action, severity=severity)
        row['fingerprint'] = fingerprint(row)
        self.findings.append(row)

    def read(self, name):
        path = 'data/' + name + '.json'
        if path not in self.cache:
            file = self.root / path
            try:
                value = json.loads(file.read_text(), object_pairs_hook=unique_object) if file.exists() else {}
                if not isinstance(value, dict):
                    raise ValueError('expected JSON object')
            except (ValueError, OSError) as exc:
                self.add('invalid_payload', path, '', {'error': str(exc)}, 'Repair the input format; do not discard its records.')
                value = {}
            self.cache[path] = value
        return self.cache[path]

    def rows(self, name, field='records'):
        rows = self.read(name).get(field, [])
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            self.add('invalid_collection', 'data/' + name + '.json', field, {}, 'Expected an array of record objects.')
            return []
        return rows

    def mapping(self, name, field):
        value = self.read(name).get(field, {})
        if not isinstance(value, dict):
            self.add('invalid_mapping', 'data/' + name + '.json', field, {}, 'Expected an object keyed by stable identities.')
            return {}
        return value

    def inventory(self, contract, paths):
        assets = contract['assets']
        result = []
        for path in sorted(paths):
            matched = [r for r in assets if fnmatch.fnmatchcase(path, r['pattern'])]
            if len(matched) != 1:
                self.add('unowned_or_ambiguous_asset', path, '', {'contracts': [r['pattern'] for r in matched]},
                         'Declare exactly one ownership/retention contract for this data asset.')
                continue
            rule = matched[0]
            file = self.root / path
            if not file.is_file():
                self.add('missing_tracked_asset', path, '', {}, 'Review deletion of a tracked data asset before publication.')
                continue
            result.append({'path': path, 'role': rule['role'], 'bytes': file.stat().st_size,
                           'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                           'contract': rule['pattern']})
        for rule in assets:
            if rule.get('required') and not any(fnmatch.fnmatchcase(p, rule['pattern']) for p in paths):
                self.add('missing_required_asset', rule['pattern'], '', {}, 'Restore the durable input or explicitly review its retirement.')
            for writer in rule['writers']:
                if writer != 'reviewed-repository-change' and not (self.root / writer).is_file():
                    self.add('missing_writer', rule['pattern'], writer, {}, 'Update the ownership contract with the actual writer.')
        return result

    def check(self):
        collections = {name: self.rows(name, 'candidates' if name == 'review_queue' else 'records')
                       for name in ('benchmarks', 'benchmarks_index', 'curated_records', 'review_queue',
                                    'catalog_records', 'library_seed_records', 'library_records', 'library_index')}
        for name, rows in collections.items():
            path = 'data/' + name + '.json'
            ids = Counter(str(r.get('id', '')) for r in rows)
            for identity, count in ids.items():
                if not identity or count > 1:
                    self.add('invalid_record_identity', path, identity, {'count': count}, 'Review identity collisions without inventing a merge.')
            if name in {'benchmarks', 'curated_records', 'review_queue'}:
                sources = defaultdict(list)
                for row in rows:
                    sources[source_key(row)].append(row.get('id'))
                for key, values in sources.items():
                    if not key or len(values) > 1:
                        self.add('source_key_collision', path, key, {'ids': sorted(values)},
                                 'Inspect source-to-entity cardinality; current upsert requires one row per source key.')

        library = {r['id']: r for r in collections['library_index'] if r.get('id')}
        catalog = {r['id'] for r in collections['catalog_records'] if r.get('id')}
        bindings = self.mapping('catalog_identity_bindings', 'bindings')
        edges = {}
        for old, binding in bindings.items():
            if not isinstance(binding, dict):
                self.add('invalid_binding', 'data/catalog_identity_bindings.json', old, {}, 'Restore a targetId and evidence-review status.')
                continue
            target = binding.get('targetId')
            if old != target:
                edges[old] = target
            if old not in catalog:
                self.add('orphan_binding_source', 'data/catalog_identity_bindings.json', old, {'target': target},
                         'Review whether the catalog source was retired; retain historical evidence.', 'warning')
            if binding.get('reviewState') == 'needs-source-review':
                self.add('unverified_legacy_binding', 'data/catalog_identity_bindings.json', old, {'target': target},
                         'Adjudicate with primary sources under #18; retain compatibility until reviewed.', 'warning')
        for merge in self.rows('library_identity_merges', 'merges'):
            old, target = merge.get('fromId'), merge.get('toId')
            if not old or not target or old == target or (old in edges and edges[old] != target):
                self.add('conflicting_redirect', 'data/library_identity_merges.json', old,
                         {'target': target, 'previous': edges.get(old)}, 'Resolve the reviewed redirect conflict explicitly.')
            else:
                edges[old] = target

        def resolve(identity):
            seen = set()
            # Follow explicit edges even if the obsolete row accidentally survives.
            while identity in edges:
                if identity in seen:
                    return None
                seen.add(identity)
                identity = edges[identity]
            return identity if identity in library else None

        for old, target in edges.items():
            if resolve(old) is None:
                self.add('unresolved_redirect', 'data/library_identity_merges.json' if old not in bindings else 'data/catalog_identity_bindings.json',
                         old, {'target': target}, 'Repair a missing target or cycle with source-backed identity evidence.')
        def require_target(name, identity, section, details=None):
            if resolve(identity) is None:
                self.add('orphan_entity_reference', 'data/' + name + '.json', str(section) + ':' + str(identity),
                         details or {'target': identity}, 'Review retirement/redirect evidence; do not guess by name.', 'warning')

        for name, field in [('library_release_dates', 'records')]:
            for row in self.rows(name, field):
                require_target(name, row.get('id'), field)
        for section in ('reviews', 'resourceReviews', 'publisherReviews', 'pending'):
            for row in self.rows('library_source_reviews', section):
                require_target('library_source_reviews', row.get('id'), section)
                if row.get('parentId'):
                    require_target('library_source_reviews', row['parentId'], section + '.parentId')
        assignments = self.mapping('taxonomy_v5_assignments', 'records')
        navigation_used_keys = set()
        for row in library.values():
            for key in (row['id'], row.get('variantOf'), row.get('familyId')):
                if key in assignments:
                    navigation_used_keys.add(key)
                    break
        for name, field in [('library_aliases', 'aliases'), ('taxonomy_v5_assignments', 'records'),
                            ('model_eval_references', 'references'), ('catalog_source_alignments', 'records')]:
            for identity in self.mapping(name, field):
                if name == 'taxonomy_v5_assignments' and identity in navigation_used_keys:
                    continue  # A family/group key may be valid without being a stored entity ID.
                require_target(name, identity, field)
                if name in {'taxonomy_v5_assignments', 'catalog_source_alignments'} and identity not in library and resolve(identity):
                    self.add('redirect_not_consumed', 'data/' + name + '.json', identity,
                             {'target': resolve(identity)}, 'This consumer uses exact IDs; review and migrate the overlay to its explicit target.', 'warning')
        for identity in self.read('research_topic_reviews'):
            require_target('research_topic_reviews', identity, 'review')
        for identity, row in library.items():
            if row.get('benchmarkParentId'):
                parent = row['benchmarkParentId']
                if parent == identity or resolve(parent) is None:
                    self.add('invalid_parent', 'data/library_index.json', identity, {'parent': parent}, 'Review the scoped child/parent relation.')

        source_rows = [r for name in ('benchmarks', 'curated_records', 'review_queue') for r in collections[name]]
        known_sources = {source_key(r) for r in source_rows} - {''}
        legacy_keys = set()
        for row in source_rows:
            source = row.get('source') or {}
            kind, identifier = source.get('type') or 'unknown', str(source.get('id') or '')
            # Match the legacy compatibility reader in source_identity.editorial_decision.
            if kind in {'arxiv', 'unknown'} or identifier.startswith(kind + ':'):
                legacy_keys.add(identifier)
        for field in ('bySourceKey', 'bySourceId'):
            for key, decision in self.mapping('editorial_copy', field).items():
                if key not in (known_sources if field == 'bySourceKey' else legacy_keys):
                    self.add('unlinked_editorial_decision', 'data/editorial_copy.json', field + ':' + key,
                             {'storedKey': key, 'decisionHash': digest(decision)},
                             'Retain historical decision; locate a compatible source or document retirement.', 'warning')
        for name in ('review_state', 'source_refresh_state'):
            for key in self.mapping(name, 'bySource'):
                if key not in known_sources:
                    self.add('unlinked_operational_state', 'data/' + name + '.json', key, {},
                             'Check retired source state; never treat this as a new admission.', 'warning')

        archive = self.read('source_evidence')
        for key, item in self.mapping('source_evidence', 'bySource').items():
            if not isinstance(item, dict):
                self.add('invalid_evidence', 'data/source_evidence.json', key, {}, 'Restore the source observation object.')
                continue
            expected = digest({k: v for k, v in item.items() if k != 'contentHash'})
            if item.get('contentHash') != expected:
                self.add('evidence_hash_mismatch', 'data/source_evidence.json', key, {'expected': expected, 'actual': item.get('contentHash')},
                         'Reconcile the archived text and source receipt; do not simply bless an altered hash.')
            if not item.get('url') or not item.get('text'):
                self.add('incomplete_source_evidence', 'data/source_evidence.json', key, {}, 'Retain source URL and primary text together.')
        # Diagnose incomplete archives without crashing before a report is saved.
        # This is an audit-local view, never a repair/write to the retained input.
        valid_archive = {'bySource': {key: item for key, item in self.mapping('source_evidence', 'bySource').items()
                                    if isinstance(item, dict) and item.get('url') and item.get('text')}}
        concepts = self.read('evidence_concepts')
        if concepts:
            for identity, row in library.items():
                facets = row.get('evidenceFacets') or {}
                if not facets:
                    self.add('missing_evidence_projection', 'data/library_index.json', identity, {}, 'Regenerate the evidence/search projection for this record.')
                    continue
                units = evidence_units(row, valid_archive)
                expected = digest({'policyVersion': POLICY_VERSION, 'conceptRegistry': digest(concepts),
                                   'name': row.get('name'), 'sourceKey': source_key(row), 'evidence': units})
                if facets.get('inputHash') != expected:
                    self.add('stale_evidence_projection', 'data/library_index.json', identity,
                             {'expected': expected, 'actual': facets.get('inputHash')}, 'Regenerate projections from the current evidence/policy, preserving reviewed inputs.')
                search = row.get('searchDocument') or {}
                if search.get('inputHash') != facets.get('inputHash'):
                    self.add('search_evidence_drift', 'data/library_index.json', identity, {}, 'Regenerate search and evidence projections together.')
                expected_concepts = [{k: fact.get(k) for k in ('id', 'label', 'scope', 'basis', 'quote', 'sourceUrl')}
                                     for fact in facets.get('facts', [])]
                if search.get('concepts') != expected_concepts:
                    self.add('search_concept_drift', 'data/library_index.json', identity,
                             {'expectedHash': digest(expected_concepts), 'actualHash': digest(search.get('concepts'))},
                             'Regenerate search concepts from the same scoped evidence facts.')
                for fact in facets.get('facts', []):
                    quote = ' '.join(str(fact.get('quote') or '').split()).casefold()
                    if not quote or not any(u.get('url') == fact.get('sourceUrl') and quote in ' '.join(u.get('text', '').split()).casefold() for u in units):
                        self.add('untraceable_facet_quote', 'data/library_index.json', identity + ':' + str(fact.get('id')),
                                 {'sourceUrl': fact.get('sourceUrl'), 'quoteHash': digest(quote)}, 'Regenerate or review evidence; this checks traceability, not scientific validity.')

        canonical = {r['id']: r for r in collections['benchmarks'] if r.get('id')}
        public = {r['id']: r for r in collections['benchmarks_index'] if r.get('id')}
        if set(canonical) != set(public):
            self.add('radar_projection_membership', 'data/benchmarks_index.json', '',
                     {'missing': sorted(set(canonical)-set(public)), 'extra': sorted(set(public)-set(canonical))}, 'Regenerate Radar projection; hidden rows are retained, not silently removed.')
        for identity, row in public.items():
            if identity in canonical:
                for field in ('releasedAt', 'firstSeenAt', 'displayEligible'):
                    default = True if field == 'displayEligible' else None
                    if row.get(field, default) != canonical[identity].get(field, default):
                        self.add('radar_stable_field_drift', 'data/benchmarks_index.json', identity + ':' + field,
                                 {'canonical': canonical[identity].get(field, default), 'public': row.get(field, default)}, 'Regenerate the projection; correct facts only in their owning input.')
            if identity in library:
                for field in SHARED_FIELDS:
                    if row.get(field) != library[identity].get(field):
                        self.add('shared_projection_drift', 'data/benchmarks_index.json', identity + ':' + field,
                                 {'radarHash': digest(row.get(field)), 'libraryHash': digest(library[identity].get(field))}, 'Regenerate both views in the documented order.')
        return {'records': {name: len(rows) for name, rows in collections.items()},
                'sourceKeys': len(known_sources), 'legacyBindings': len(bindings), 'retainedSources': len(archive.get('bySource', {}))}


def compare_baseline(findings, baseline):
    # Baselines explicitly enumerate debt; there are no wildcard/count allowances.
    known = {r['fingerprint']: r for r in baseline.get('findings', [])}
    if len(known) != len(baseline.get('findings', [])):
        raise ValueError('Duplicate baseline fingerprints')
    for row in known.values():
        if not row.get('issue') or not row.get('reason'):
            raise ValueError('Every baseline entry needs a tracking issue and reason')
        if row.get('severity') != 'warning' or fingerprint(row) != row['fingerprint']:
            raise ValueError('Only intact, explicitly reviewed warning findings may be baselined')
    current = {r['fingerprint'] for r in findings}
    new = [r for r in findings if r['severity'] == 'error' or r['fingerprint'] not in known]
    return {'new': len(new), 'known': len(findings)-len(new),
            'resolved': sorted(set(known)-current), 'newFingerprints': [r['fingerprint'] for r in new]}


def run(root=ROOT, contract=None, baseline=None, paths=None):
    contract = contract if contract is not None else json.loads(CONTRACT.read_text())
    baseline = baseline if baseline is not None else json.loads(BASELINE.read_text())
    if paths is None:
        output = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', 'data'])
        paths = sorted(set(output.decode().strip('\0').split('\0')) - {''})
        # Declared optional runtime files can be present without being tracked yet.
        paths = sorted(set(paths) | {r['pattern'] for r in contract['assets'] if not any(c in r['pattern'] for c in '*?[') and (root/r['pattern']).is_file()})
    audit = Audit(root)
    inventory = audit.inventory(contract, paths)
    counts = audit.check()
    findings = sorted({r['fingerprint']: r for r in audit.findings}.values(), key=lambda r: (r['code'], r['path'], r['key']))
    return {'schemaVersion': 1, 'readOnly': True, 'inventory': inventory, 'counts': counts,
            'findingCounts': dict(sorted(Counter(r['code'] for r in findings).items())),
            'baseline': compare_baseline(findings, baseline), 'findings': findings,
            'limits': ['Traceability and integrity are not scientific identity verification.',
                       'Historical source texts are not fully archived; no full reconstruction claim.',
                       'Coverage and backlog completion are audited separately by audit_workflow.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true', help='Fail on new findings, while retaining explicitly tracked historical debt.')
    args = parser.parse_args()
    if args.output:
        dest = args.output.resolve()
        # Diagnostic writes are restricted to the ignored outputs tree.
        if not dest.is_relative_to((ROOT / 'outputs').resolve()):
            parser.error('--output must be inside outputs/; product data cannot be overwritten')
    report = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'counts': report['counts'], 'findingCounts': report['findingCounts'],
                      'baseline': {k: report['baseline'][k] for k in ('new', 'known')},
                      'resolved': len(report['baseline']['resolved'])}, ensure_ascii=False))
    if args.check and report['baseline']['new']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

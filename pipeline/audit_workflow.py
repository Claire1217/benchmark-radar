#!/usr/bin/env python3
"""Read-only, reproducible diagnosis of discovery -> review -> Library.

Findings are observations, not admission decisions. Legacy source receipts do
not certify pagination completion, and absence is never inferred from a name.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlparse

from site_views import presentation
from source_identity import source_key as observation_key
from generate_editorial_copy import publishable, public_release_ready, selection_fingerprint, ADMISSION_POLICY_VERSION

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = {"publish", "defer", "exclude"}


def visible(row):
    return row.get("displayEligible") is not False and row.get("evaluationMode") != "viewpoint_probe"


def source_key(row):
    source = row.get("source") or {}
    kind, identifier = source.get("type"), source.get("id")
    return (str(kind), str(identifier)) if kind and identifier else None


def reference(row):
    return {"id": row.get("id"), "name": row.get("name"), "source": row.get("source"),
            "releasedAt": row.get("releasedAt")}


def audit_queue(candidates, decisions, canonical, as_of, namespaced=None):
    """Join exact, namespaced sources; legacy decisions are keyed only by id."""
    known = {source_key(r) for r in canonical if source_key(r)}
    known_visible = {source_key(r) for r in canonical if source_key(r) and visible(r)}
    namespaces = defaultdict(set)
    for row in [*candidates, *canonical]:
        if key := source_key(row):
            namespaces[key[1]].add(key[0])
    cutoff = (date.fromisoformat(as_of) - timedelta(days=3)).isoformat()
    counts, details = Counter(), []
    for row in candidates:
        key = source_key(row)
        scoped = (namespaced or {}).get(observation_key(row))
        stored = scoped if scoped is not None else decisions.get(key[1]) if key else None
        if not key:
            state = "missing_source_identity"
        elif scoped is None and len(namespaces[key[1]]) > 1 and stored is not None:
            state = "ambiguous_legacy_decision_key"
        elif row.get('reviewReason') in {'historical-reassessment','source-changed'} and (stored or {}).get('selectionFingerprint') != selection_fingerprint(row, ADMISSION_POLICY_VERSION):
            state = 'historical_reassessment_pending' if row['reviewReason']=='historical-reassessment' else 'source_update_review_pending'
        elif key in known:
            state = "canonical_source_present" if key in known_visible else "canonical_source_hidden"
        elif stored is None:
            state = "no_editorial_or_canonical_source"
        elif stored.get("decision") not in DECISIONS:
            state = "invalid_editorial_decision"
        elif stored.get("decision") == "publish" and not publishable(stored):
            state = "publish_contract_blocked"
        elif stored.get("decision") == "publish" and not public_release_ready(row, stored):
            state = "publish_artifact_verification_blocked"
        elif stored.get("decision") == "publish":
            state = "publish_eligible_without_canonical_source"
        else:
            state = "editorial_" + stored["decision"]
        counts[state] += 1
        raw = row.get("releasedAt")
        try:
            outside = date.fromisoformat(raw).isoformat() < cutoff if raw and raw != "0001-01-01" else None
        except (TypeError, ValueError):
            outside = None
        details.append({**reference(row), "state": state, "outsideRecentReviewWindow": outside})
    return {"count": len(candidates), "recentReviewFrom": cutoff, "states": dict(sorted(counts.items())),
            "unreviewedOutsideRecentWindow": sum(x["state"] == "no_editorial_or_canonical_source"
                                                 and x["outsideRecentReviewWindow"] is True for x in details),
            "limitations": "Exact source-key joins only. Alias or cross-source identity requires separate review; queue membership is not itself a backlog count.",
            "records": details}


def audit_hidden(records):
    hidden = [r for r in records if not visible(r)]
    rows = []
    for row in hidden:
        curation = row.get("curation") or {}
        evidence = curation.get("evaluationEvidence") or {}
        rows.append({**reference(row), "state": curation.get("state"),
                     "evaluationMode": row.get("evaluationMode"),
                     "hasStoredTaskScoringReuse": all(bool(evidence.get(k)) for k in ("task", "scoring", "reuse")),
                     "decisionReason": curation.get("decisionReason")})
    return {"count": len(rows), "states": dict(sorted(Counter(r["state"] or "missing" for r in rows).items())),
            "withStoredTaskScoringReuse": sum(r["hasStoredTaskScoringReuse"] for r in rows),
            "limitations": "Stored positive mode/evidence is a reconciliation signal, not proof that a hidden record should be published.",
            "records": rows}


def audit_coverage(taxonomy, config, policy):
    definitions = {c["id"]: c for c in taxonomy["categories"]}
    mappings = {c["categoryId"]: c for c in policy["directions"]}
    if len(mappings) != len(policy["directions"]):
        raise ValueError("Duplicate source coverage direction")
    if set(definitions) != set(mappings):
        raise ValueError("Source coverage directions must match the navigation registry")
    configured = set(config["arxiv"]["categories"])
    result = []
    for key, category in definitions.items():
        proposed = set(mappings[key]["arxivCandidates"])
        missing, included = sorted(proposed - configured), sorted(proposed & configured)
        status = "no_direct_arxiv_mapping" if not proposed else "none_configured" if not included else "partly_configured" if missing else "listed_categories_configured"
        result.append({"categoryId": key, "name": category["name"], "status": status,
                       "configuredCandidates": included, "missingCandidates": missing,
                       "note": mappings[key].get("note", "")})
    return {"configuredArxiv": sorted(configured), "directions": result,
            "limitations": "This is an explicit audit hypothesis, not an enabled collection policy or a measured recall estimate. Cross-listing may cover individual papers."}


def audit_receipts(receipts):
    attempts, failures = [], []
    for path, run in receipts:
        discovery = run.get("externalDiscovery") or {}
        counts, errors = discovery.get("counts") or {}, discovery.get("failures") or {}
        for source in sorted(set(errors) | {s for s in ("arxiv", "github", "huggingface", "openreview") if s in counts}):
            dates = counts.get("arxivQueryDates" if source == "arxiv" else "publicationBatchDates")
            status = "failed" if source in errors else "not_scheduled" if source == "arxiv" and dates == [] else "reported_no_error_completeness_unverified"
            item = {"receipt": path, "sourceDate": run.get("sourceDate"), "source": source,
                    "queryDates": dates, "status": status, "error": errors.get(source),
                    "count": counts.get(source)}
            attempts.append(item)
            if status == "failed":
                failures.append(item)
    return {"attemptCount": len(attempts), "recordedFailureCount": len(failures), "attempts": attempts,
            "limitations": "Legacy receipts lack pagination and per-scope completion certificates. Later success does not prove an earlier gap was repaired. Missing receipts are unknown."}


def audit_discovery_cases(cases, records, candidates, config):
    def linked_ids(row):
        result = set()
        source = row.get("source") or {}
        if source.get("type") == "arxiv" and source.get("id"):
            result.add(str(source["id"]))
        for value in (row.get("links") or {}).values():
            if not value:
                continue
            url = urlparse(value)
            if url.hostname in {"arxiv.org", "www.arxiv.org", "huggingface.co"}:
                if match := re.fullmatch(r"/(?:abs|pdf|papers)/(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?/?", url.path):
                    result.add(match[1])
        return result
    library_refs = [(r, linked_ids(r)) for r in records]
    queue_refs = [(r, linked_ids(r)) for r in candidates]
    configured = set(config["arxiv"]["categories"])
    return [{**case, "categoryGate": "eligible_via_subject" if configured & set(case["subjects"]) else "outside_configured_categories",
             "linkedLibraryIds": [r["id"] for r, refs in library_refs if case["sourceId"] in refs],
             "linkedCandidateIds": [r["id"] for r, refs in queue_refs if case["sourceId"] in refs],
             "limitation": "Source links show traceability, not identity equality. No link in this snapshot does not prove the source was never fetched."}
            for case in cases]


def run_browser_probe(root, payload, cases):
    # Use the same compact projection shipped to the browser, not richer records.
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "input.json"
        path.write_text(json.dumps({"library": presentation(payload), "cases": cases}), encoding="utf-8")
        output = subprocess.run(["node", str(ROOT / "pipeline" / "probe_library_search.cjs"),
                                 str(root / "web" / "app.js"), str(path)],
                                check=True, capture_output=True, text=True)
        return json.loads(output.stdout)


def audit_operations(root):
    """Read operational ledgers separately from public visibility and editorial truth."""
    def load(name,default):
        p=root/'data'/name
        return json.loads(p.read_text()) if p.exists() else default
    ledger=load('source_coverage.json',{'windows':{}})
    windows=list(ledger.get('windows',{}).values())
    from source_coverage import CONTRACT_VERSION
    counts=Counter(w.get('status','unknown') if w.get('contractVersion')==CONTRACT_VERSION else 'legacy-unverified' for w in windows)
    incomplete=[w for w in windows if w.get('status')!='complete' or w.get('contractVersion')!=CONTRACT_VERSION]
    review=load('review_state.json',{'bySource':{}}).get('bySource',{})
    migration=load('historical_reconciliation.json',{})
    return {'discovery':{'windowCount':len(windows),'states':dict(sorted(counts.items())),
                'oldestUnfinishedFrom':min((w['from'] for w in incomplete),default=None),
                'scope':'Configured source queries only; completion is not exhaustive domain recall.'},
            'review':{'attemptedSources':len(review),'states':dict(sorted(Counter(r.get('status','unknown') for r in review.values()).items()))},
            'reconciliation':{'version':migration.get('migrationVersion'),'cases':migration.get('cases',{}),
                'hiddenOutcomes':dict(sorted(Counter(r['outcome'] for r in migration.get('hidden',[])).items())),
                'unresolvedIdentityBindings':len(migration.get('identityReview',[]))},
            'sourceEvidenceRecords':len(load('source_evidence.json',{'bySource':{}}).get('bySource',{}))}


def build_report(root, as_of=None):
    paths = ["data/library_index.json", "data/benchmarks.json", "data/curated_records.json",
             "data/review_queue.json", "data/editorial_copy.json", "data/taxonomy_v5.json", "pipeline/config.json"]
    loaded = {p: json.loads((root / p).read_text(encoding="utf-8")) for p in paths}
    library = loaded["data/library_index.json"]
    as_of = as_of or library["manifest"]["dataAsOf"]
    date.fromisoformat(as_of)
    # Policy/cases belong to the audit implementation, which may inspect an older snapshot.
    policy_path, cases_path = ROOT / "data/source_coverage_audit_policy.json", ROOT / "data/workflow_audit_cases.json"
    policy, cases = json.loads(policy_path.read_text()), json.loads(cases_path.read_text())
    receipts = [(str(p.relative_to(root)), json.loads(p.read_text())) for p in sorted((root / "data/runs").glob("*.json"))]
    fingerprints = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in [*paths, "web/app.js"]}
    for p in (policy_path, cases_path, ROOT / "pipeline/site_views.py", ROOT / "pipeline/probe_library_search.cjs", ROOT / "pipeline/generate_editorial_copy.py", Path(__file__)):
        fingerprints["audit:" + str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    fingerprints["receipts"] = hashlib.sha256(json.dumps(receipts, sort_keys=True).encode()).hexdigest()
    for name in ('source_coverage.json','review_state.json','historical_reconciliation.json','source_evidence.json'):
        p=root/'data'/name
        if p.exists():fingerprints['data/'+name]=hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ('web/search.js','web/search-policy.js'):
        p=ROOT/name
        if p.exists():fingerprints['audit:'+name]=hashlib.sha256(p.read_bytes()).hexdigest()
    records = library["records"]
    queue_payload = loaded["data/review_queue.json"]
    queue = audit_queue(queue_payload["candidates"], loaded["data/editorial_copy.json"]["bySourceId"],
                        loaded["data/benchmarks.json"]["records"] + loaded["data/curated_records.json"]["records"],
                        queue_payload.get("sourceDate") or as_of,
                        namespaced=loaded["data/editorial_copy.json"].get("bySourceKey", {}))
    queue["windowBasis"] = "queue.sourceDate minus three days; not the attention snapshot date or proof of the last successful review"
    probe = run_browser_probe(root, library, cases["searchCases"])
    return {"schemaVersion": "1.0", "asOf": as_of, "inputSha256": fingerprints,
            "summary": {"storedRecords": len(records), "visibleRecords": sum(visible(r) for r in records),
                        "queueStates": queue["states"], "searchCases": len(probe),
                        "searchCasesPassing": sum(x["passes"] for x in probe)},
            "queue": queue, "hidden": audit_hidden(records),
            "coverage": audit_coverage(loaded["data/taxonomy_v5.json"], loaded["pipeline/config.json"], policy),
            "sourceReceipts": audit_receipts(receipts), "operations": audit_operations(root), "search": probe,
            "discoveryCases": audit_discovery_cases(cases["discoveryCases"], records, queue_payload["candidates"], loaded["pipeline/config.json"]),
            "limitations": cases["limitations"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Read an existing repository snapshot")
    parser.add_argument("--as-of", help="Explicit audit date; defaults to the snapshot manifest")
    parser.add_argument("--output", type=Path, help="Write only this report, never canonical data")
    args = parser.parse_args()
    if args.output:
        destination = args.output.resolve()
        # Protect source and generated product data from an accidental --output.
        for protected in (args.root.resolve() / "data", args.root.resolve() / "pipeline", args.root.resolve() / "web"):
            if destination == protected or protected in destination.parents:
                parser.error("Report output must be outside data/, pipeline/ and web/")
    report = build_report(args.root.resolve(), args.as_of)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(json.dumps(report["summary"], ensure_ascii=False))
        print(f"report={args.output}")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()

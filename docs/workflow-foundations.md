# Workflow foundations: evidence before expansion

This first implementation adds a reproducible diagnostic baseline and prevents
truncated arXiv harvests from being treated as completed backfills. It does not
enable additional source categories, alter Library visibility, merge entities,
or change production search results.

## Reproduce the diagnosis

```sh
make audit-workflow
# Inspect another saved repository snapshot without changing it:
python3 pipeline/audit_workflow.py --root /path/to/snapshot --output outputs/snapshot-audit.json
```

The report records the snapshot date and SHA-256 hashes of its inputs, policy,
browser code, projection, audit implementation and historical receipts. It
contains source coverage hypotheses, source-failure observations, review-state
reconciliation, hidden-record signals, and actual browser-predicate results.
It deliberately does not stamp wall-clock time into otherwise identical reports.
The default command writes only `outputs/workflow-audit.json`; product data is
read-only. Known content gaps are diagnostic findings rather than CI failures.
Malformed inputs, missing coverage mappings and a broken browser adapter fail.

## What the current data actually means

The database is JSON in Git, with distinct authority layers:

| Layer | Authoritative inputs | Important boundary |
| --- | --- | --- |
| Acquisition | `review_queue.json`, `runs/*.json`, backfill checkpoints | Queue membership alone does not mean unreviewed work. Old run receipts do not prove complete pagination. |
| Admission and corrections | `editorial_copy.json`, `curated_records.json`, `curated_overrides.json` | `decision=publish` alone is insufficient: scoring/reuse and artifact-evidence gates also apply. |
| Library identity and evidence | Seeds, catalog snapshots, identity merges, source/release/repository reviews | These can target different IDs and require explicit redirects. A shared paper or repository does not prove identical evaluations. |
| Classification | `taxonomy_v5.json`, reviewed assignments, legacy classifiers | Navigation placement is not a complete inventory of domains or tasks. |
| Projection | `library_index.json`, then `site_views.py` | Browser search uses the compact view, which discards nested audit evidence. |
| Consumer | `web/app.js`, Trends matching, CLI search | These currently have different matching rules. A CLI search score cannot certify the web experience. |

Generation also has side effects: `generate_library_index.py` updates parts of
the Radar public index, and `make build` reranks attention and updates model
evaluation projections. Therefore neither is a read-only audit command.

### Observed baseline

On the initial 4,104-record snapshot, 3,556 rows are visible. The queue has 3,117
rows, but 15 already have a canonical source record. Exact namespaced source
joins find 1,793 rows without editorial or canonical source records. This is
not an instruction to publish them; cross-source aliases require reconciliation.

The 204 queued rows with `decision=publish` but no canonical source record are
all explained by additional admission gates: 114 fail the scoring/reuse contract
and 90 fail artifact-evidence verification. Counting these as lost publications
would be a diagnostic bug. The audit calls the existing admission predicates.

Of 548 hidden rows, 545 have `ai-name-audit-deferred`; 185 retain non-empty task,
scoring and reuse evidence. These are reconciliation signals, not proof of
incorrect hiding or valid source quotations. The report must not unhide them.

The initial browser pilot has 14 cases across chip design, audio, security,
research, mathematics and games. It exposes domain recall, typo handling,
substring false positives and pre-search visibility failures. It is intentionally
small and developer-authored: it is **not** the planned independent 120-query
evaluation, nor a ranking or full-coverage benchmark.

## Bugs and migration hazards considered

| Hazard | Protection in this batch / remaining prerequisite |
| --- | --- |
| OAI or Atom returns only the first `max_papers` records as success | Collectors now raise `IncompleteHarvestError` when a unique-paper limit is exceeded. Exact-limit complete results remain valid. |
| Atom returns an empty page before its advertised total | Raise rather than treat it as end of collection; a missing total is also incomplete. |
| OAI repeats a resumption token | Detect the cycle rather than hang or certify completion. |
| An old truncated checkpoint has a valid content hash | Version the harvest contract; pre-v2 checkpoints must be refetched. A hash authenticates bytes, not source completeness. |
| A failed source is confused with zero releases | Historical receipt failures stay explicit; later success does not close a prior gap without matching completion evidence. |
| Stale global date hides old work | Report the review-window reference from queue source date separately from attention freshness. It is an approximation of scheduling, not proof a review actually ran. |
| Identical source IDs from different providers join | Audit uses `(type, id)`; ambiguous legacy editorial keys are reported separately. |
| A model's `publish` string is mistaken for successful admission | Report effective gate outcomes using existing production predicates. |
| Search audit reads fields unavailable to users | Probe the actual `web/app.js` predicate after applying the actual compact projection. |
| Audits accidentally repair or rewrite inputs | Explicit output path, protected product directories, snapshot hash/no-write integration test. |
| A case-specific fix overfits chip design | Audit fixtures are separate from runtime. No synonyms or benchmark names are injected into production. |

The browser adapter extracts a bounded set of existing functions and fails if
their layout changes. This is a temporary baseline instrument, not the planned
shared search core. It measures predicate retrieval, not ordering, DOM rendering,
category selection or latency. Those require later browser integration tests.

## Boundaries for the next implementation

1. **Source coverage ledger:** store source, scope, immutable attempt ID,
   requested window, actual window, cursor, collector version, completion status
   and failure. Maintain unfinished scopes independently of the calendar.
   Healthy adapters may proceed; a failed source must not be recorded as covered.
   Do not bootstrap old receipt counts as certified completion.
2. **Review work queue:** select by effective state, source/policy changes and
   waiting time. Reserve capacity for old work. Keep API failures, missing
   evidence, explicit rejection and conflicting decisions distinct. Reuse the
   existing fingerprint/invalid-output protections rather than retry forever.
3. **Evidence and identity contracts:** source observations remain separate from
   benchmark, version and subset identity. Names produce possible matches,
   never unconditional merges. Preserve IDs and all consumer redirects. A name
   or copy review must not perform an admission transition implicitly.
4. **Facts and navigation:** build evidence-backed domain/task/tool relationships
   independently of card text and the primary/secondary category display limit.
   Shared top members are not sufficient evidence to merge semantic categories.
5. **Search contract:** shared browser/CLI/Trends behavior, version-aware exact
   identity, scoped domain expansion, explicit typo handling, relevance ranking
   and matched-evidence explanations. Preserve negative/ambiguous query cases.
6. **Backfill and migration:** after the queue can absorb the load, measure a
   representative historical window, then expand sources and backfill gaps.
   Stage record-level additions/removals/merges and verify IDs, model references,
   old URLs, and saved entries before any public switch.

## Acceptance gates

- Source truncation or incomplete pagination cannot write a completed checkpoint
  or call the backfill finalizer.
- Failed work resumes from completed category checkpoints; repeats remain
  idempotent with respect to source IDs and do not duplicate cross-listed papers.
- Existing exact-name and version behavior, hidden-state handling and public
  views continue to pass the repository tests and static build.
- A future coverage expansion must include independent expected examples, not
  only records already in the Library. An absent source link means unknown
  acquisition history, not proof the paper was never fetched.
- Promote the diagnostic pilot to a held-out, cross-domain relevance set before
  claiming search improvement. Evaluate per-domain recall and precision as well
  as ranking; do not optimize only for non-empty results.

Public rollout, broad automatic reclassification, restoration of hidden records,
and changes to the Library/Radar admission policy are not part of this batch.

## Production admission safety (issue #13)

The scheduled job now reviews at most 48 candidates without a lower publication-date
cutoff. Half the slots go to oldest, least-recently-attempted work; the remainder go
to recent work. Operational failures cool down for a day and retain a bounded
per-source attempt history in `data/review_state.json`. Unchanged deferred decisions
are eligible again after 14 days. Unchanged exclusions and successful reviews wait
for changed inputs; invalid-output holds remain in place, with explicit ID retry.

Missing source text never writes an admission decision. A public record is retained
when review defers or cannot verify release evidence. Unpublishing requires an
explicit `--review-public --allow-unpublish` (or curated audit), an `exclude`
decision and an exclusion quote verified against the supplied source text. Scheduled
name audits do not enable that flag. The quote is necessary provenance, not a claim
that substring verification alone proves the editorial judgment correct.

The separate `forecast_attention.py` entry point writes only whitelisted forecast
fields to `data/attention_forecasts.json`. Its generated estimates cannot write
names, descriptions, eligibility or dates. `apply_overrides.py` applies compatible
forecasts after editorial copy, and refuses nonpublishable copy. Publication is
persisted before a review is marked complete, allowing interrupted writes to replay.

Existing hidden rows are not automatically restored. They require the historical
reconciliation in #18. Forecasts require the existing model credential; missing
credentials preserve the last snapshot. The source registry, coverage ledger,
identity, evidence facets and shared search are tracked in #14–#17; they are not
claimed complete by this foundations batch.

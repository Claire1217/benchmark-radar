# Historical reconciliation and verification

The migration covers 2026-07-24 through 2026-10-24. Its default is a read-only plan;
`--apply` is an explicit, bounded staging operation. It never publishes, unhides,
renames or merges Library records. Use the regular evidence-validated admission
review after candidates have been collected.

```sh
python3 pipeline/reconcile_workflow.py --start 2026-07-24 --end 2026-10-24 --output outputs/reconciliation-plan.json
python3 pipeline/reconcile_workflow.py --start 2026-07-24 --end 2026-10-24 --apply --max-cases 5 --max-seconds 150
python3 pipeline/discover_benchmarks.py --start-date 2026-07-24 --date 2026-10-24 --max-windows 20 --max-seconds 180
make audit-workflow
```

`data/historical_reconciliation.json` records baseline and per-run counts, per-case
source URLs, dates, evidence hashes and outcome reasons. Five known cases were
fetched from the official Atom API and durably queued: MobileJailBench, MUSES,
GateTruth, ChipVerilog and SGAnalog. ChipVerilog retains its July 12 first release;
its August 17 revision is not a new release in the three-month window. The other
four first releases fall inside the window. These observations do not certify
that a paper's benchmark is reusable or meets admission policy.

All 548 hidden primary-source records were rehydrated into review work. A one-time
migration version changes their review fingerprint, while the deterministic
admission path refuses historical reassessment records. No stale positive scoring
or reuse field restores visibility. Source evidence and queue writes precede
completion receipts. Replaying the migration reuses persisted source cases and
does not create duplicate queue identities. Existing IDs, first-release dates,
first-seen dates, families and visibility are checked before/after.

The initial acquisition plan contains 979 windows: 700 weekly category windows
for 50 arXiv categories and 279 daily windows across GitHub, Hugging Face and
OpenReview. This is configured-query coverage, not all possible sources. The
bounded real-source run and current remaining debt are recorded in
`source_coverage.json` and the CI audit artifact. The real bounded run attempted 20 arXiv windows: 19 completed and one cs.CV window
failed with a TLS EOF. It fetched 5,307 paper observations (cross-category duplicates
are possible) and recognized 496 candidate observations. The queue grew from 3,117
to 3,718 rows after reassessment and discovery; 379 primary-source texts were retained.
959 windows remain pending and one failed window remains retryable. Pending windows
are intentionally not stamped complete. The normal daily collector drains this ledger, alternating
recent and historical work; failed scopes remain retryable.

The 70 preserved legacy catalog bindings still require primary-source identity
review. `historical_identity_review.json` records two concrete checks: the
potential Analog Design Bench duplicate and HWE homonyms. At least three HWE-named
evaluations have different tasks/sources (CAE simulation, RISC-V CPU design and
hardware bug repair); the CAE repository now redirects to CAE-bench. A title match
cannot resolve these. The ADB mirror relationship is documented by its HF README,
but this migration does not infer a paper/release merge from equal task counts.

No local model credential was available during reconciliation. Fresh source
retrieval, queued admission review, provisional facets and published records are
reported as separate states. The configured daily workflow can perform model
review after this PR stack is merged; no production dispatch, merge or deployment
was performed here.

## Rollback and reproducibility

The code and staged JSON changes are a Git commit. Revert that commit before
production use, or restore the pre-migration queue/ledger/evidence snapshot only
when no subsequent reviews have been written. After production reviews exist,
revert code separately and reconcile new observations by source key; do not erase
later published work with an old snapshot. No destructive cleanup of older
checkpoints or receipts is required.

CI runs the production browser predicate against the compact view and uploads a
workflow audit artifact. It separately counts legacy-unverified, failed and pending
coverage, operational review attempts, hidden outcomes and unresolved bindings.
Full tests include source pagination failures, crash ordering, duplicate replay,
old-date invalidation, recent/backlog fairness, publication retention and shared
search membership. The search pilot deliberately retains a hidden VeriBug miss;
a search patch is not permission to publish it.

# Model Evals batch source review

User-authorized long-running task, started 2026-10-24. Review every collected
model and benchmark using the Kimi two-source design: the selected publisher's
own comparison first, benchmark-maintainer evaluations second. Never mix
competitor scores from separate release reports to assemble a synthetic table.

## Durable state

- `data/model_eval_updates.json`: reviewed comparisons, original values, receipts,
  captured official runs, and model-specific protocol audits.
- `data/model_eval_review_queue.json`: generated inventory of every collected
  model–benchmark pair, ordered by release date. Rebuilt by `update_model_evals.py`.
- `data/model_eval_evidence/`: literal extracted source tables and snapshot hashes.
- `web/model-evals/review.html`: generated public progress and complete evidence.
- `modelAudits.sourceCoverageStatus` must be complete before declaring a model
  complete. Finishing its currently displayed scores is insufficient when the
  system card contains additional performance metrics.

Baseline: 124 models with observations, 2,009 distinct model–benchmark pairs,
2,009 numeric records plus five coverage-only records. Historical duplicate
observations remain preserved. The 1,135 catalog-only identities with no
observations are not counted as reviewed or assigned fabricated scores.

## Completed implementation

Protocol audits now belong to a model–benchmark pair. An unreviewed model cannot
inherit Kimi's leaderboard eligibility from a shared benchmark ID. Pending review
is explicitly distinguished from a checked absence or protocol mismatch.

The generic evidence page retains complete source columns, excluded values,
supporting system-card locations, and all captured official runs. The drawer
stays concise. Every later batch must keep the evidence page reproducible.

## Batch 1

- Kimi K3.1 Pro: previous 48-metric audit retained.
- DeepSeek-V4.1-Flash-1017: all 11 release-table rows transcribed as 12 metric
  comparisons. HLE full and dagger-marked text-only values are separate. The
  named Apex Bench v1.1 still needs source-identity resolution; do not conflate it
  with APEX-Agents. The model is not complete while that review is pending.
- Claude Haiku 5.5: all eight launch-table comparisons added, with supporting
  system-card pp.111–128. The system-card capabilities section has additional
  metrics in the discovery backlog and remains in progress.
- Added official FrontierCode 1.1 Main (136 configurations), Chartography without
  tools (42 rows), and OSWorld v2.1 offline partial-score view (five configurations
  of Opus 5). Preserve the source snapshots and source-specific effort settings.

## Important findings and remaining work

- Haiku system-card section 8.9.3 resolves OSWorld 72.4 to partial credit on 82
  offline tasks; strict pass is 37.1. The matching official view has no Haiku run.
  The report's Opus 4.8 grader is not specified in the official result records;
  do not describe the runs as identically configured.
- Haiku Terminal-Bench uses 660 trials, no internet egress, and no fallback.
  Sonnet/Opus comparison runs use 330 trials and different fallback behavior.
- Haiku's launch FrontierCode table cites Sonnet Xhigh 52.1; the system card also
  lists Sonnet Max 46.2. Preserve the chosen source table, never merge these into
  a single implied same-effort comparison.
- FrontierCode official `new_score` is the composite score. `correct` is a
  separate binary-correctness measure and must not supply this chart.
- DeepSeek ProgramBench does not identify Almost/Fully resolved or raw mean;
  ZeroBench does not identify aggregation. Neither gets an inferred mapping.
- Zapier's private-held-out strict pass protocol is not established for the
  DeepSeek AutomationBench card value. Do not map it into the official board on
  the basis of the shared v1.0.6 label alone.
- Sonnet currently displays later Haiku-reference Elo observations. When doing
  Sonnet's batch, deliberately choose its own launch table and retain later
  reference snapshots separately; update the preferred-source policy and tests.
- Existing catalog links can be wrong (e.g. Qwen3.7 Max points to a Qwen3.8 card).
  Validate model identity, not just whether a URL returns successfully.

## Next batch

1. Finish DeepSeek Apex identification via its own technical report or release
   documentation; record an honest unresolved result if no identity is supported.
2. Ingest Haiku system-card performance metrics, verifying every figure's full
   comparison and matching official protocol. Its source PDF is in
   `outputs/model-evals-batch/haiku.pdf` (144 pages). All capability text from
   pp.111 onward has been extracted; pages 111 and 128 were visually checked.
3. Continue newest-first through GPT-6.1 Sol, Sonnet 5.5, GPT-6 Sol/Luna, Opus 5.5,
   and the remaining model inventory. Sonnet (148 pages) and Opus (230 pages)
   system cards and release HTML are already cached in the same directory.

## Validation / publication

Run `python3 pipeline/update_model_evals.py`, Model Evals regression tests,
JavaScript render checks, and static-site validation for each substantive batch.
Keep the active long-running goal until the inventory and discovered metric
backlog are actually completed. Do not mark the entire task complete merely
because a batch has shipped.

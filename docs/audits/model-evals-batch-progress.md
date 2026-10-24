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
  The initial card did not identify ZeroBench aggregation; the October 17 API changelog resolves Pass@5 (see Batch 2). Exact tool access remains unspecified.
- Zapier's private-held-out strict pass protocol is not established for the
  DeepSeek AutomationBench card value. Do not map it into the official board on
  the basis of the shared v1.0.6 label alone.
- Sonnet currently displays later Haiku-reference Elo observations. When doing
  Sonnet's batch, deliberately choose its own launch table and retain later
  reference snapshots separately; update the preferred-source policy and tests.
- Existing catalog links can be wrong (e.g. Qwen3.7 Max points to a Qwen3.8 card).
  Validate model identity, not just whether a URL returns successfully.

## Next batch after Batch 1 (superseded by the continuation below)

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

## Batch 2 — 2026-10-25

- Added 22 Haiku system-card metrics (30 total model comparisons). All numeric
  source figures used here were visually checked. Each transcription retains
  its page/figure locator and original values; the full PDF SHA-256 is attached.
- Added independent FrontierCode Extended, FrontierSWE v2, OSWorld offline
  strict-pass, and SWE-bench Multilingual/Multimodal maintainer-run snapshots.
  SWE-bench filters require both the SWE-agent organization and checked=true;
  merely hosted third-party submissions are excluded.
- Kept ProgramBench's 166-task mean test pass rate, oracle-text OfficeQA,
  Anthropic BenchCAD subset, changed-judge DRACO/WANDR/healthcare, and multilingual
  blocked-response exclusion separate from incompatible leaderboard metrics.
- DeepSeek's October 17 official API changelog confirms ZeroBench Pass@5. Moved
  that result to a distinct tools/Pass@5 metric; exact tool access is still
  unspecified, so no Python/no-tools official view is inferred. September's
  unreviewed record remains separate. Apex v1.1 is explicitly identity-unresolved
  after reviewing the card, changelog and linked September technical report.
  Reviewed means the evidence/status was checked, not that every source exists.
- Haiku life-science figures pp.136–139 were read and visually inspected, but
  their nine metrics are not ingested yet. Figure labels round to two decimals
  while prose gives some percentages to one decimal; preserve original
  precision and do not invent extra precision or splice reports.
- Additional effort/cost curves remain source detail; the primary comparison
  uses the report's stated headline/Max setting, not a best-effort selection.

### Next continuation

1. Finish Haiku's nine life-science metrics and their maintainer-source checks.
   Cached figure: `outputs/model-evals-batch/haiku-p137.png`. The full section
   states biology safeguards were off for Haiku, and peer safety-blocked attempts
   were excluded. Sequence Generation uses one attempt, Library Ranking three,
   biomedical imaging one; others five. Carry those settings into the audit.
2. Then continue the existing newest-first model queue, beginning GPT-6.1 Sol.
   Sonnet and Opus system cards remain cached. Do not declare the overall goal
   complete at the end of a batch.

Batch 2 checks: 18 Model Evals regression tests passed; all 2,031 drawers rendered
in the JavaScript VM; static build and validation passed. This is programmatic
render validation, not a browser screenshot check.

Primary source leads for the next life-sciences pass:
- https://github.com/latchbio/spatialbench (current README has 159 problems;
  Haiku says SpatialBench Verified without a task count, so version alignment
  must be established before showing that board).
- https://arxiv.org/abs/2602.09063 (LatchBio scBench; do not assume equivalence
  to the card's SingleCellBench name without checking).
- https://www.benchling.com/blog/can-llms-work-in-the-wet-lab
  (BenchBench-Protocol; establish whether it is the card's Understanding V2).
- Ignore the unrelated spatialbench.com visual-spatial reasoning suite.

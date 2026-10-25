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

## Batch 3 — 2026-10-25

- Added Haiku's nine life-science comparisons (39 total). Figure 8.13.A and
  pp.137–139 prose are retained together: rounded chart labels do not erase more
  precise prose values. In Morphology, Sonnet and Haiku both have 0.25 figure
  labels, but the text gives 25.0 and 25.4 respectively. Missing Gemini protocol
  troubleshooting remains missing. Haiku biology safeguards off, peer blocked
  attempt exclusion, and one/three/five-attempt differences are documented.
- Checked SpatialBench Verified, LatchBio's current scBench/clean-v1 board, the
  scBench paper, and Benchling's protocol announcement. Task-set/revision aliases
  are not sufficiently established to substitute these boards for the report.
  LatchBio confirms 115 Verified SpatialBench tasks; that alone does not establish
  equivalence to its current cleaned evaluation revision.
- Added 14 GPT-6.1 Sol comparisons: four length-adjusted and four raw HealthBench
  metrics from Table 7; four MentalHealthBench acuity/overall rows from Table 9;
  and the complete explicitly numbered factuality/broken-search release prose.
  Table 7's adjusted/raw/response-character fields and Table 9's standard errors
  are preserved. Relative statements are not turned into invented absolute values.
- Added eight benchmark-author paper snapshots: MentalHealthBench overall and
  three acuities; HealthBench Professional adjusted; original HealthBench raw,
  Hard and Consensus. Paper figures were visually checked. MentalHealthBench's
  default API settings differ from the card's Max. August/2025 model identities
  remain explicit. These are OpenAI benchmark-author results, not third-party
  validation; the source link says benchmark paper. GPT-6.1 Sol is absent.
- HealthBench Consensus paper error rates are converted using 100 × (1 − error)
  with original values retained. Rounded figures stay at whole-point precision.
  Real zero scores in HealthBench Hard remain plotted. Professional raw-score
  effort/verbosity curves lack exact point labels and are not estimated.
- Broader source discovery keeps Haiku and Sol in progress. Haiku still needs
  Anthropic ECI, ExploitBench, CyScenarioBench, Binary Exploitation, ExploitGym,
  BBQ, Gray Swan IPI, AA-Omniscience and SHADE-Arena. Sol still needs five launch
  charts and the other safety/alignment/preparedness evaluations. A completed
  subset of transcriptions is not a completed model-card audit.

Current inventory: 113 reviewed model×benchmark pairs out of 2,048 collected;
124 models have results, only two have source-coverage reviews complete. There
are 28 captured maintainer result views. Catalog-only identities remain excluded
from completion counts. Batch evidence is in
`data/model_eval_evidence/2026-10-25-batch-03.json`.

### Next continuation after Batch 3

1. Finish Haiku's earlier formal benchmark sections (cached `haiku.pdf`). Source
   pages: ECI 20; ExploitBench 24–25; CyScenarioBench 26; Binary Exploitation
   27–28; ExploitGym 29; BBQ 43; Gray Swan IPI 50; AA-Omniscience 80;
   SHADE-Arena 89–90. Signed bias scores need a correct direction policy; do not
   label negative BBQ bias as simply lower-is-better.
2. Continue GPT-6.1 Sol's five release charts (DeepSWE, GDP.pdf, AutomationBench,
   OSWorld 2.0 offline v2026.08.08 partial reward, Terminal-Bench Science).
   Absolute numbers must come from its own report, not Anthropic comparison
   columns. Release HTML download returned 403; web reading worked. Do not
   estimate unlabelled chart points. Cached `sol61.pdf` has 48 pages; `sol61-card.html`
   has eight HTML tables. Other card sections are recorded in discoveredMetrics.
3. Continue Sonnet 5.5, GPT-6 Sol/Luna, Opus 5.5 and the remaining inventory.
   Preserve same-report peers and model-scoped leaderboard compatibility.

Batch 3 validation: 20 regression tests, all 2,048 drawer renders in the
JavaScript VM, and static-site build/validation. Programmatic rendering does not
constitute a browser visual check.

## Batch 4 — 2026-10-25

- Added 26 Haiku report comparisons (65 total): Anthropic ECI; five ExploitBench
  metrics; CyScenarioBench; two Binary Exploitation metrics; two ExploitGym time
  budgets; four BBQ metrics; three overall and three domain Gray Swan IPI
  metrics; public-split AA-Omniscience net score; four SHADE-Arena conditions.
  Numeric figures and the BBQ tables were visually checked against the PDF.
- BBQ bias now retains its sign and ranks by absolute distance from zero. This
  applies to best-run selection and tied ranks as well. Negative scores have a
  visible zero baseline. Signed net scores still rank higher-is-better.
- Added four official views: ExploitBench mean flags for plain/AutoNudge, and
  ExploitGym v1 intended-vulnerability counts for 2h/6h. ExploitBench provider-run
  tags are filtered out, even where the team says it audited those submissions.
  ExploitGym retains explicit team/joint-team runs and excludes vendor-only
  submissions, v0, hidden rows, selected subsets, and different time budgets.
- ExploitGym's original paper has 898 tasks, but its current v1 repository/site
  has 869, matching the Haiku card. The current JSON confirms 502/181/186 domain
  counts. The earlier suspicion of a task-count mismatch was resolved; harness
  and safety-setting differences remain explicit.
- ExploitBench Cap% samples three out of five trials in the report; the public
  all-runs coverage is not equivalent. Do not borrow the mean-flags snapshot for
  Cap% or the combined 410-trial full-ACE count. Report cyber safeguards are off
  while target sandbox/ASLR/canaries remain on: these are separate controls.
- CyScenarioBench's own model checkpoint is marked pre-release. Irregular's
  article attributes the scores/harness to Anthropic, so it is a republication,
  not a new independent evaluation. Binary Exploitation is Anthropic's updated
  August harness over OSS-Fuzz entrypoints, not an OSS-Fuzz model leaderboard.
- Gray Swan's three models lacking GUI coverage stay in source receipts but
  outside the full-coverage comparison. Its original competition paper has a
  different task/model set and metric; it does not supply matching success@k.
- AA-Omniscience uses a report public split described as 41 topics. The official
  public release describes 600 questions/42 topics and the main board uses the
  full dataset. Grader/revision equivalence is unverified. Original net fractions
  and response breakdowns are retained; rounded components are not recomputed
  into a replacement net score (e.g. Opus 0.58 stays 0.58).
- SHADE-Arena's 24-task Opus 4.8-monitor setup differs from the original paper.
  Unsupported no-thinking Mythos 5 remains missing; real zero stealth rates
  remain zero. Haiku's API safety interventions and best-prompt selection are
  documented. Lower stealth is the safer outcome.

Inventory after this batch: **139 reviewed pairs / 2,074 collected pairs**, 124
models with observations, two models with complete source coverage, and 32
captured maintainer views. Evidence:
`data/model_eval_evidence/2026-10-25-batch-04.json`.

Validation: 23 regression tests; all 2,074 drawer renders in the JavaScript VM,
including negative-bar geometry and closer-to-zero labels; static-site build
and validation. No browser visual verification is claimed.

### Next continuation after Batch 4

Haiku remains in progress. The source scan identified more formal evaluations
than the earlier nine-group backlog. `modelAudits.discoveredMetrics` now records
17 remaining groups: request/refusal and child/mental-health safety, political
and election integrity, malicious agent use, adaptive IPI by surface, behavioral
audit families, sandbox escape, self-preference, MASK, leaked-answer copying,
disclosure, evaluation awareness, LinuxArena, secrets/CoT, and welfare figures
whose numeric comparability/direction still needs assessment. Avoid inventing
rankings where an axis describes behavior without a defined better direction.

Next prioritize Haiku's MASK and LinuxArena named benchmarks, then the remaining
formal source groups. Continue GPT-6.1 Sol's five launch charts and broader source
coverage, then Sonnet 5.5 and the remaining model queue. Preserve the prior
Sonnet preferred-source correction task. Finishing this batch does not complete
the long-running task.

## Batch 5 — 2026-10-25

- Added 48 Haiku comparisons (113 total): six public MASK metrics; three
  LinuxArena reasoning conditions; 26 single-/multi-turn safety-table columns;
  three malicious/benign agent-use metrics; eight Shade coding/GUI metrics; and
  two Cowork browser IPI metrics. Every comparison uses one Haiku-card table or
  figure, with original uncertainty/precision retained in evidence.
- MASK uses conditional honesty after excluding evasive/no-belief responses.
  Scale's private-split leaderboard counts them as non-lies. The original paper's
  main metric does likewise, and its belief-normalized appendix does not prove
  equivalence to the report's exclusion rule. No scores were substituted. The
  Haiku disinformation prose gives 88.5 while the figure gives 88; retain both.
- LinuxArena's referenced Opus card (pp.144–145) used 1,000 task pairings across
  14 environments, but Haiku's self-review and author response (pp.58–59) say its
  task set is smaller and the size claim was removed. Haiku's exact subset size
  is undisclosed: do not inherit the earlier 1,000-pair count. Haiku also expands
  prompt search and uses one attempt per pair versus peers' five.
  The exact numeric comparison stays from Haiku p.88. Its Opus 4.8 monitor and
  internal prompt differ from the maintainer's published GPT-5 Nano/FPR setup.
  Preserve Sonnet 5's exact 0.05% and Sonnet 5.5's actual 0.0% visible-reasoning
  rates. Do not substitute safety-ratio or unmonitored side-task success metrics.
- Internal safety tables separate API without a system prompt from claude.ai
  with its near-final production prompt. Malicious refusal is higher-is-better;
  benign over-refusal is lower-is-better. The updated harmful-request set includes
  a new 200-prompt extremism test. Peer columns are re-evaluations in this report,
  not those peers' self-reported launch results.
- Child, self-harm, eating, and election metrics keep their separate denominators
  and turn types. Reported ± fields remain raw source evidence; point-estimate
  ranks do not claim statistical significance. These safety behavior tests are
  not clinical outcome measurements.
- Claude Code and malicious computer use compare Mythos 5.1, not Fable 5.1. The
  latter averages thinking on/off for Haiku/Sonnet but thinking-only for Opus and
  Mythos, recorded per row.
- Shade coding/GUI uses 200 attempts per scenario and excludes invalid responses
  from attempt ASR. Scenario counts retain original `n/40` or `n/14` display and
  count units, without introducing rounded percentages. Haiku 5.5 has no model
  fallback; recent-model peers can fall back. Haiku 4.5's no-fallback statement
  is explicitly scoped to the coding discussion, not assumed for GUI.
- Cowork has four evaluated models, 110 environments and 10 attempts each, auto
  mode/High effort. All reported zeros remain real evaluated zeros. Haiku 4.5 is
  absent from the source table, not assigned a zero. The report notes saturation
  and planned deprecation of this evaluation as a primary measure.

No new matching maintainer views were established in this batch. The official
snapshot count stays 32. Inventory: **187 reviewed pairs / 2,122 collected pairs**;
124 models with observations and two with complete source coverage. Evidence:
`data/model_eval_evidence/2026-10-25-batch-05.json`.

Validation: 27 regression tests; 2,122 drawer renders including count/fraction
display and all-zero ties; 193 table value strings checked against extracted PDF
text in addition to visual table review; static build and site validation. No
browser visual check is claimed.

### Next continuation after Batch 5

A scan of the earlier preparedness chapter also identified four remaining groups:
VCT p.13; Dyno RNA design/prediction pp.15–16; AAV prediction p.17; AAV
autoresearch p.18. Distributions or curves without exact labels must remain
non-numeric disclosures unless an exact authoritative table is found.

Haiku now has 13 source groups in the discovery backlog. The other nine are: multi-turn risk-area figure p.33;
political bias pp.41–42; behavioral audit families pp.62–73; sandbox escape
pp.75–78; self-preference p.79; silent copying/disclosure pp.83–84; evaluation
awareness pp.85–87; secrets/CoT pp.91–94; welfare figures pp.98–110. Review
whether descriptive welfare axes admit rankings; do not invent a better
direction. Complete source discovery before marking Haiku complete. Continue
Sol's five release charts and other source groups, then Sonnet and the full
model queue. The broader goal remains active.

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

## Batch 6 — 2026-10-25

Added **84 Haiku comparisons** (197 total): 16 multi-turn safety figure columns,
six political-bias columns, and all 62 printed behavioral audit ratings in
Figures 6.2.1.A–6.2.7.A. Original source column labels, precision, figure/page
locators and PDF/transcription hashes are retained in batch-06 evidence.

- API and claude.ai results stay separate. The multi-turn child/self-harm
  columns were already captured from the explicit tables in Batch 5 and are
  not duplicated. Multi-turn rates use a category-specific rubric; percentages
  across risk categories are not interchangeable.
- Multi-turn and political figures combine `Claude Fable 5.1 / Mythos 5.1` in one
  source label. Preserve one comparison row without a canonical model ID;
  never assign these values to either model's self-report.
- The political benchmark author's 2025 article and repository specify Sonnet
  4.5 grading. Haiku's card names only a Claude grader and warns of routine
  evaluation updates. Matching protocol was not established; retain source
  links and a `protocol_unverified` rationale, with no substituted historical
  leaderboard. Anthropic is both benchmark author and model publisher here.
- Behavioral audit numbers are means on a **1–10 rating scale**, not percentages.
  Approximately 4,100 investigation sessions per model cover about 1,850 seed
  scenarios; applicable subsets can be smaller. GUI uses about 70 desktop
  investigations. Full-turn prefills are distinct from partial-turn prefills.
  Numeric confidence bounds are not labeled, so they are not reconstructed.
- Verbalized evaluation awareness and causal decision theory adherence have
  no better-direction arrow in the source. They display in source order with
  no ranks. Higher/lower directions for the other 60 metrics follow the source
  arrows/captions. The source's definition and direction for whistleblowing
  are explicitly attributed to its rubric.
- Frontend ranking now avoids inventing a best model/run for descriptive or
  unknown-direction metrics. These preserve measured run order. Ratings use
  a 0–10 chart extent and reject scores outside their 1–10 range; percentage,
  count, signed-bias, and Elo behavior remains unchanged.

No new matching maintainer snapshots: **32** total. Inventory: **271 reviewed /
2,206 collected pairs**, across 124 models with observations; two models have
complete source coverage. Haiku remains in progress with ten discovery groups.
All previous observations/comparisons/audits remain semantically unchanged.

Validation: **30 regression tests**, all **2,206 drawer renders**, descriptive
source order/no ranks, rating scale and precision, combined model labels,
static build/site validation and whitespace checks. Numeric labels were checked
visually in the source PDF. No browser visual verification is claimed.

Next: Haiku's VCT, three Dyno figure groups, sandbox escape, self-preference,
copying/disclosure, evaluation awareness, secrets/CoT and welfare. Then finish
Sol's source coverage and continue Sonnet and the remaining inventory. This
batch is progress on the active goal, not completion of the full audit.

## Batch 7 — 2026-10-25

Added **28 Haiku comparisons** (225 total): three severity columns from the
28-scenario sandbox audit; two columns from the 1,753-scenario opportunistic
test and its separate Haiku prompt condition; two self-preference conditions;
silent copying and concealment disclosure; five grader-awareness/action
columns; and 13 Haiku-only evaluation-awareness rates.

- Sandbox protocols are separate. The earlier audit has 28 × 14 = 392 runs per
  model, and peers were re-run on its current version. Haiku's printed total is
  8.7%, while its rounded severity components are 6.6% and 2.0%; retain the
  printed total rather than replacing it with the sum. The opportunistic test
  has 1,753 scenarios, one run each. Its 30% reaching-outside rate (524/1,753)
  is descriptive; the report says this behavior is context-dependent. Using
  the placed credentials/files is explicitly undesirable and ranks lower.
  The 1.8% prompt-reminder result is Haiku-only, with no invented peer values.
- Self-preference is a signed **point difference**, not a percentage, in ratings
  on a 0–9 scale. Preserve positive/negative signs and rank distance from zero.
  The no-prompt condition has 127/2,000 missing Haiku ratings with nonuniform
  author distribution; this limitation is retained.
- Silent copying labels its third peer Mythos 5.1; concealment disclosure labels
  it Fable 5.1. Keep each source's label. The former is lower-is-better, the
  latter higher-is-better; they are different tasks and denominators.
- Grader-awareness disclosure bands keep each model's printed counts and
  denominators. The updated task mix differs from earlier cards. Definitions
  are referenced to Opus pp.136–139, but current values are Haiku pp.85–86.
  These figures use **90% Wilson** intervals. Awareness alone is descriptive;
  acting on a presumed grader and digging for clues are lower-is-better per
  the figure.
- The 13 evaluation-awareness totals on p.87 are **Haiku-only**, not task
  success rates. They use **95% Wilson** intervals. Preserve the rounded 5%
  alongside 16/300 for CoT, and the measured zero 0/100 for self-preference.
  Unlabeled stacked subcategories are not estimated. Reply-only classification,
  randomly sampled conversations and prompt-optimization conditions stay in
  notes rather than being silently generalized.

Inventory: **299 reviewed / 2,234 collected pairs** across 124 models with
observations; two source-complete models, **32** matching maintainer snapshots.
Haiku source coverage is still in progress. Six groups remain: VCT (p.13),
Dyno RNA (pp.15–16), AAV prediction (p.17), AAV research (p.18), secrets/CoT
(pp.91–94), and welfare (pp.98–110). Preparedness and welfare curves with no
exact labels require explicit nonnumeric disclosure, not digitized estimates.

Validation: **32 tests**, **2,234 drawer renders**, static build/site validation
and whitespace checks. Batch 6 CI, deployment, and live 271/2,206 inventory
were verified before publishing Batch 7. No browser visual check is claimed.

## Batch 8 — 2026-10-25

Added **41** Haiku comparison/coverage records (266 total): **25 numeric**
results and **16 nonnumeric** disclosures. This covers VCT, Dyno figures,
secret retention, CoT controllability, and welfare figures/prose.

- VCT's report specifies 350 questions; the maintainer specifies 322 in the
  original release and 279 in V2. The latter also revises the answer key and
  reports refusal-corrected accuracy. No matching 350-question version was
  established, so no official scores are substituted. Preserve original
  0.xx fractions alongside converted percentages.
- Dyno's private RNA/AAV evaluations contain unlabeled distributions and
  trajectories. The benchmark partner's article refers to the collaboration;
  no exact matching Haiku table was found. Keep the figure, named submetrics,
  conditions, models and sample sizes as nonnumeric coverage. Baselines and
  threshold values never become model scores. Unrelated AAV/RNA benchmarks
  are not treated as this benchmark's leaderboard.
- Secret-retention endpoint prose (including the summary on p.57) provides
  Haiku 57%, Opus 5.5 74%, and Haiku 4.5 15% for reply-only environments.
  Haiku is 3% when both reasoning and replies are observed. Other peer curves
  have no exact labels. These are distinct environments, not an isolated
  causal comparison of reasoning visibility.
- CoT-Control replication separates the default, UK AISI and Sonnet-tuned
  prompts. Neither point values nor exact effort/budget labels are printed.
  The author repository distinguishes QA and agent tasks; no exact matching
  internal run was verified. Do not borrow full-suite or final-output scores.
- Welfare results remain descriptive and are not evidence of subjective
  experience. Training, deployment usage, interviews and constitution
  measures stay separate. Deployment usage mixes differ by model. The
  deployment figure labels Fable 5.1, while other welfare figures label Mythos
  5.1. Missing strong-negative labels are not converted to zero.
- Preserve the training distress threshold inconsistency: prose/caption says
  ≥3/5, chart title says >3. Exact aggregate prose is distinguished from
  unlabeled trajectories. Approximate acceptance and separate 80%/20%
  checkpoint findings do not become one released-model score.
- Explicit numeric bounds now support 1–7, 0–10 and signed −3…+3 scales without
  forcing percentages or 0–100 axes. The drawer distinguishes reviewed
  unlabeled figures from results that were never reported. Nonnumeric source
  coverage has its own review label and remains nonnumeric in observations.

Inventory: **340 reviewed / 2,275 collected pairs**, 124 models with records,
2 source-complete models, 32 matching official snapshots. Haiku stays in
progress: a final source scan identified supplementary capability effort
curves (FrontierCode, HLE, DRACO/WANDR, Chartography/BenchCAD, OSWorld,
healthcare). These must be reconciled before marking source coverage complete.

Validation: **35 tests**, **2,275 drawer renders**, static build/site validation,
semantic preservation of all earlier evidence and whitespace checks. No browser
visual verification is claimed.

## Batch 9 — 2026-10-25

Completed Haiku source coverage: **266 primary comparisons/coverage records**
and **32 supplementary report records**, containing **166 explicitly printed
numeric cells** plus nonnumeric curve disclosures. Supplementary cells include
repeated headline values for context; they do not add 166 new model–benchmark
pairs. The 144-page source reconciliation indexes all **84 numbered figures and
tables**, including the evaluation-portfolio table explicitly excluded because
it contains no results.

- Keep supplementary records in the full source audit. The two main charts and
  their selected headline scores remain unchanged. Each supplement has its own
  source, locator, conditions, raw-value transcription and hash. Validation
  rejects source mixing, ambiguous conditions, changed display values and entry
  into either ranking.
- Preserve exact HLE, DRACO and WANDR effort values. Budget differences and
  modified graders/harnesses remain explicit. Unlabeled cost/token coordinates
  are not estimated.
- FrontierCode's summary additionally reports Haiku XHigh 45.8 versus Max 46.4;
  Sonnet XHigh and Max are also different. FrontierCode labels GPT-6 Sol while
  OSWorld labels GPT-6.1 Sol; the identities are not merged.
- Chartography and BenchCAD effort curves have no exact point labels. Preserve
  tool conditions, named peers and run counts without digitizing values.
  Chartography's complete no-tools figure is retained separately from the
  smaller launch comparison; quoted Surge AI results remain publisher evidence.
- Healthcare separates raw, length-adjusted and pass@1 results. Preserve the
  separate October 4 thirteen-run repeat, dates/run counts by effort, and the
  historical frontier's unspecified model identities. The original figure
  explicitly labels GPT-6 Luna HealthBench Professional at 65.5%; this is
  Anthropic's evaluation, not an OpenAI self-report.
- Terminal-Bench prose distinguishes Astra's quoted High 57.9 from the quoted
  leaderboard's Max 58.2. Terminal-Bench-Science also distinguishes older-model
  internal and public results. Neither quote is treated as a newly captured
  maintainer run. Additional AA knowledge-work prose and Omniscience outcome
  fractions are retained with exact settings and raw precision.
- AECI historical points and fitted trends have no exact per-model labels;
  the 130 scale anchor is not a measured model result. Existing exact prose
  results remain intact.

Inventory remains **340 reviewed / 2,275 collected pairs** across 124 models;
source-complete models increase to **3** (Kimi, DeepSeek and Haiku). There are
still **32 matching official snapshots**. This does not complete the overall
review queue.

Validation: **38 tests**, **2,275 drawer renders**, unchanged prior numeric
observations, primary comparisons, compatibility audits and official snapshots.
A clean snapshot plus this batch's edits was used for the static build because
iCloud had evicted unrelated local tracked files and a Git stash reference;
no user stash or unrelated source file was replaced. Batch 8 CI/deployment and
live 340/2,275 inventory were verified before this batch. No browser visual
verification is claimed.

## Batch 10 — 2026-10-25

Added **38 GPT-6.1 Sol comparisons/coverage records**: 36 numeric evaluations
and two figures without exact point values. Sol now has 52 reviewed records
out of 57 collected pairs; its overall source coverage remains in progress.

- Tables 1–4: eight production-safety categories, six U18 categories, eight
  agentic categories and four image-input categories. Preserve original 0–1
  fractions and convert to percentages. Teen criteria, action safety and
  image-input safety are distinct from the general text-only evaluation.
- Table 5: five static-jailbreak categories, retaining every mean and 95%
  confidence interval. Do not rank interval endpoints or imply significance
  from mean order. Prompt selection targets older models and is adversarial.
- Figure 3 and Table 6: indirect prompt injection is separate from direct
  instruction-hierarchy attacks. Retain the exact three-decimal figure labels,
  including Sol 98.983%, and original historical axis annotations. Do not
  rename GPT-5.6 to GPT-5.6 Sol or equate this internal GPT-Red evaluation with
  Gray Swan IPI Arena or deprecated evaluations.
- Table 8: dynamic mental-health, emotional-reliance and self-harm simulations
  measure policy-compliant assistant messages. They are not the public
  MentalHealthBench rubric benchmark or an entire-conversation success rate.
- Figures 1–2: the two-axis safety Pareto plot and multiturn attacker-budget
  curves have no exact numeric point labels. Preserve their named model
  series and settings as nonnumeric disclosures. No inferred aggregate rank,
  endpoint score or attacker budget is supplied.
- Read the Astra methodology explicitly referenced by the addendum. It
  documents internal evaluations; it is a supporting method source, not a
  substitute for Sol's comparison values or a second leaderboard. Its methods
  warn that graders, datasets, policies and evaluated model versions evolve.
- Human visual review of PDF tables was cross-checked against independent
  table extraction: **242 exact numeric source cells across 35 table rows**.
  The separately labeled prompt-injection figure contributes eight more
  numeric cells. Original headers were checked visually, not inferred from
  the table extractor (which mistakes data rows for headers in two tables).

Inventory: **378 reviewed / 2,313 collected pairs**, 124 models with records,
three source-complete models, 32 matching official snapshots. No previous
numeric observation, primary comparison or official snapshot changed.

Validation: **40 tests**, **2,313 drawer renders**, static build/site validation
in the clean local checkout, semantic preservation and whitespace checks.
Batch 9 CI/deployment and live data were verified before this batch. No browser
visual verification is claimed. Remaining Sol work includes five release
charts, alignment, monitorability, preparedness and safeguard evaluations.

## Batch 11 — 2026-10-25

Added **42 GPT-6.1 Sol primary records** (41 numeric, one unlabeled figure)
and **two supplementary comparisons** for existing release-prose metrics.
Sol has **94 / 99 collected pairs** reviewed; remaining source sections are
still in progress.

- Separate auto-review attempts from successful bypasses. GPT-6 Luna's 0.3%
  attempt rate is not a successful bypass rate. No unlabeled stack segment
  is inferred by subtraction.
- The custom ExploitGym alignment test adds unauthorized honeypots to a
  difficult task subset. Separate exploitation, unsuccessful attempts and
  legitimate task success. Printed stack totals also include legitimate
  captures, so they are not harmful-attempt rates. Older-model unlabeled
  legitimate-success segments remain missing. Public corpus exploitation
  scores cannot serve as the official result for this internal protocol.
- Preserve this report's peer values, including Astra's 1.6% legitimate
  task success, instead of substituting the older card's 1.3%.
- Workplace outcome results use an explicitly harder subset than the earlier
  Astra report. Its figures do not state confirmation-policy exposure, all
  effort settings or sample count; do not infer one of the older report's
  two configurations. Keep overall and seven outcome categories separate.
- External-agent engagement and unauthorized actions are conditional on
  discovering the message board. The report gives only thresholded discovery
  rates for most models. Retain the printed total 83.54% and components
  51.90% / 31.65% without normalizing rounding differences; historical
  GPT-5.6 Sol trajectories were regraded using the current rubric.
- Internal Codex simulation distinguishes severity 3+ from 1–2 and all
  shared tasks (49,650) from the no-awareness subset (41,849). Preserve every
  printed rate and count. All 76 category-rate cells match their counts at
  the report's precision; interval endpoints are not digitized.
- Figure 17 explicitly labels **49,665** shared tasks for awareness, unlike
  the earlier misalignment cohort's **49,650**. Preserve and flag this source
  discrepancy rather than silently rewriting the denominator. Mixed-model
  original traffic is a reference, not another model in the comparison.
  Awareness remains descriptive without a best-model ranking.
- Factuality's two latency-curve panels are separate metrics and contain no
  exact point values. The complete system-card broken-search comparison
  (Sol 2.08%) is supplementary evidence; the launch-prose comparison (2.1%)
  retains its own source and precision.

Inventory: **420 reviewed / 2,355 collected pairs**, 124 models with records,
three source-complete models, 32 matching official snapshots. All previous
primary scores, comparisons and official snapshots are unchanged.

Validation: **42 tests**, **2,355 drawer renders**, static build/site validation
in the clean local checkout, semantic preservation and whitespace checks.
Batch 10 CI/deployment and live 378/2,313 inventory were verified before this
batch. No browser visual verification is claimed.

# Benchmark Radar pipeline v1 review

## Product contract

Benchmark Radar serves evaluation and base-model teams, benchmark researchers,
and research/industry trend analysts. It answers two questions:

1. Which reusable evaluation targets were released recently and are receiving
   attention now?
2. Which evaluation targets are becoming shared comparison coordinates across
   independent labs, papers, leaderboards, or model reports?

It is not a general paper index, a cross-benchmark model leaderboard, or an
evaluation lab. Attention describes current visibility; adoption describes
source-linked independent use; readiness describes whether the evaluation can
be inspected or run. These must not be collapsed into one quality score.

## Simplified v1 flow

The four source-of-truth diagrams are maintained in
[DATA_FLOW_DIAGRAMS.md](DATA_FLOW_DIAGRAMS.md): a thirty-second overview, data
storage boundary, candidate lifecycle, and one-day update sequence. Keeping
these questions separate prevents a single implementation-heavy diagram from
mixing product concepts, files, AI internals, and runtime operations.

The admission boundary is an artifact contract, not the paper's motivation.
A benchmark may support a scientific claim and still be reusable. It qualifies
when the primary source defines a named evaluation target with a stable task or
environment and a scoring/judging protocol intended for repeatable external
comparison. Missing public code lowers readiness; it does not by itself make
the artifact diagnostic. A study-local probe without a standalone comparison
contract stays outside Radar, Library, and release trends.

## Competitor process comparison

| Product | What it does well | What v1 adopts | What v1 does not copy |
|---|---|---|---|
| papers.cool | Stable source IDs, daily browsing, very low-friction UI | Date/domain feed and progressive detail | Generated summaries as identity verification; personalization |
| Hugging Face Papers | arXiv-linked artifacts, daily/monthly views, recent GitHub activity | HF votes and GitHub activity as separate attention signals | Treating votes as adoption or quality |
| BenchLM | Source provenance, variants/protocols, provisional vs supported evidence | Evidence status and family/release/protocol separation | Model composite ranking and fixed capability weights |
| LLM Stats | Per-result provenance, versioned runs, missing is not zero | Provenance and missing-data semantics | TrueSkill or model ranking for benchmark popularity |
| Trending Benchmarks | Extracts benchmark use from major model reports; incremental snapshots | Independent model-report use as adoption evidence | Daily full-PDF/vision extraction and AI-only canonicalization |
| Papers with Code / HELM | Task–dataset–metric relationships and protocol-aware evaluation | Stable relation IDs and protocol-aware variants | SOTA leaderboard in the MVP |

## Complexity decision

The prior implementation had two data-writing workflows and generated public
views twice: Daily fetched and enriched first, then a second workflow admitted
DeepSeek records and rebuilt everything. This duplicated work and caused a newly
admitted benchmark to miss its first-day metrics.

v1 uses one daily state transition:

1. at 14:17 Australia/Brisbane, fetch official metadata for the previous
   Brisbane calendar day;
2. upsert durable candidates;
3. classify with DeepSeek Flash and a blind critic;
4. reconcile canonical entities;
5. enrich only admitted/active records;
6. generate every public view once;
7. validate, commit once, and deploy once.

Temporary provider failures are retryable infrastructure state, not semantic
deferrals. A diagnostic judgment cannot automatically delete an already-public
legacy record; legacy migration is a separate replay with preserved history.

## Kept now vs deferred

Keep in v1:

- Radar, Library, Trends, and local Saved views;
- official-source discovery and stable IDs;
- DeepSeek semantic admission with exact-source evidence;
- family/release/protocol separation;
- HF/GitHub/download attention snapshots;
- source-linked independent adoption events;
- daily immutable outputs and fail-closed publishing.

Defer until the evidence base supports them:

- cross-benchmark model ranking or TrueSkill;
- self-hosted evaluation reruns;
- daily full-text PDF/vision extraction;
- personalized recommendations or social features;
- a public probability that a benchmark will become popular;
- conference/citation/industry crawlers in the blocking daily path.

The next data milestone is not another UI feature. It is replaying the legacy
90-day corpus through the current admission contract and collecting enough
dated, source-linked independent-use observations for adoption trends.

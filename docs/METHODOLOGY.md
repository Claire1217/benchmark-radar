# Methodology

## What counts as a new Benchmark

Discovery starts from arXiv's official OAI-PMH metadata for selected AI, language, vision, robotics, software, and graphics categories. Automatic publication requires primary-source evidence of a named benchmark/evaluation-suite release or an explicit sentence that introduces, presents, releases, develops, or builds one.

Papers that only compare models on existing benchmarks are not new Benchmark entities. Ambiguous candidates are stored in `data/review_queue.json` for review and are not shown on the website.

## Dates

- `releasedAt`: first public arXiv version date.
- `firstSeenAt`: date the tracker first indexed the entity.
- `sourceUpdatedAt`: most recent observed source update.
- metric and publication observations carry their own timestamps.

These dates are not interchangeable. An arXiv update is not a conference decision date.

## Attention

Attention is a public-interest signal, not quality. The current source families are:

- Hugging Face paper votes
- GitHub repository stars
- Hugging Face dataset downloads and likes

Today, 30-day, and 90-day views rank records inside their respective windows. Dated deltas replace current public levels as enough daily history accumulates. Missing signals remain missing and are never converted to zero. Ranking confidence describes signal coverage; it is not paper-recognition confidence.

The default website view is **30 days · Attention**. `Newest` remains an explicit alternative.

## Readiness

Readiness is independent of Attention:

- `Paper only`: no public evaluation package was found.
- `Protocol available` (stored as `Inspectable` in data): a public dataset,
  project page, or sufficiently detailed evaluation protocol was found. This
  means a reader can inspect how the evaluation is defined; it does **not**
  claim that the benchmark can be run end to end.
- `Runnable`: public evaluation code was found.
- `Maintained`: reserved for stronger versioning and maintenance evidence.

A popular paper can remain `Paper only`; a low-attention benchmark can be `Runnable`.

## Benchmark role and inclusion threshold

The index separates five semantic roles:

- `reusable_benchmark`: released as a reusable evaluation target for other teams;
- `diagnostic_benchmark`: built mainly to reveal a limitation or support a
  scientific claim, but still defines a named and repeatable evaluation;
- `benchmarking_study`: an empirical comparison whose main contribution is the
  analysis rather than a reusable benchmark artifact;
- `uses_existing_benchmarks`: reports results on already established benchmarks;
- `unclear`: the available evidence does not support a confident classification.

Reusable benchmarks are eligible for the Radar when the release and identity
evidence are clear. Diagnostic benchmarks use a higher inclusion bar: they enter
the public Library only after independent use, unusually strong field- and
age-normalized attention, or an explicit evidence-backed human review. A famous
author or lab is provenance, not an automatic pass. Benchmarking studies and
papers that only use existing benchmarks remain source evidence or review
candidates; they do not become Benchmark entities.

Whether a benchmark is suitable for **training** is not an inclusion criterion.
Most benchmarks are evaluation instruments, and keeping their test data held out
can be a sign of sound methodology rather than low usefulness.

## Watch: future adoption forecast

`Watch` is reserved for a future-facing adoption forecast and is never added to Attention. Its target is whether a Benchmark gains independent use in papers, model cards, or external evaluation harnesses—not whether it receives clicks.

The intended contract is:

- estimate at day 14 and day 30 after first public release;
- predict independent adoption by day 180;
- exclude the authors' own papers, repositories, and model cards;
- compare only with same-age, same-field release cohorts;
- use early independent adoption, runnable evaluation resources, task breadth, dedicated leaderboard integration, and capped attention velocity;
- never use author or institution prestige as a public feature;
- show no `Low potential` label because delayed recognition is common.

The public `Watch` badge remains disabled while the project has only a 90-day history. It will first run in shadow mode and requires rolling time-based backtests, calibrated probabilities, and a documented Precision@Watch threshold before any forecast is shown. The frontend already treats `Watch` as an optional field so the badge can be enabled without redesigning cards.

## Construction and annotation

Construction describes where test instances came from. Annotation describes who or what created the labels. These are separate axes. If primary-source evidence is insufficient, both remain unknown and the public detail view omits the empty field.

The complete three-axis category contract and evidence priority are documented
in [Taxonomy and classification evidence](TAXONOMY.md).

## Conference and publication evidence

The data model keeps venue attempts separate from publication records. Evidence priority is:

1. official proceedings or publisher record
2. official OpenReview venue status or Program Chair decision
3. arXiv journal reference or resolved publisher DOI
4. arXiv author comment
5. unverified third-party mention

Current automatic backfill covers arXiv journal references and comments:

- `Acceptance claimed`: an author stated acceptance in arXiv comments.
- `Publication reported`: an arXiv journal reference exists.
- `Accepted` and `Published`: reserved for matched official evidence.

No record means unknown, never rejected or unpublished. Workshop, findings, demo, and main-conference tracks must remain distinct.

## Domain trends

Trend charts count newly released Benchmark families per week. They measure evaluation activity, not technical progress. Conference deadlines, source coverage, and naming conventions can create artificial bursts, so the chart includes sample size and confidence context.

## Human review

Reviewed corrections live in `data/curated_overrides.json` with evidence URLs and review dates. The order is always machine snapshot → reviewed override → validation → public output.

Ambiguous candidates can additionally pass through the evidence-constrained AI
stage documented in [AI-assisted candidate review](AI_REVIEW.md). AI decisions
remain separate from the canonical snapshot: a positive decision must carry an
exact source quote, pass deterministic validation, and remain reviewable.

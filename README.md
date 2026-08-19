# Benchmark Radar

A public, GitHub-based tracker for newly released AI benchmarks.

## What is indexed

The first pipeline uses arXiv's official OAI-PMH feed across selected AI,
language, vision, robotics, software, and graphics categories. A paper is
published to the tracker only when its primary-source metadata contains either:

- a named benchmark or evaluation-suite title; or
- an explicit sentence that introduces, releases, builds, or presents a
  benchmark.

Ambiguous matches are written to `data/review_queue.json`, not shown on the
site. Code, data, and project links are copied only when the arXiv metadata
contains the literal URL. Missing information remains unknown.

## Data and audit trail

- `data/benchmarks.json` is the canonical current snapshot.
- `data/runs/YYYY-MM-DD.json` records the source query, counts, accepted IDs,
  confidence, and exact evidence for that source date.
- `data/review_queue.json` contains candidates that need human review.
- arXiv ID is the source-level identity; a stable tracker ID is derived from
  the canonical name and arXiv ID.
- Re-running a date replaces that date's machine-generated records, so false
  positives do not survive improved rules.

## Daily update

`.github/workflows/daily-index.yml` runs every day and can also be replayed for
an explicit date. It tests the recognizer, indexes the latest arXiv release
date, validates the web app, and commits only validated data.

Run locally:

```bash
python3 -m unittest discover -s pipeline/tests -v
python3 pipeline/index_benchmarks.py --latest-with-papers
npm test
```

## Product boundaries

- Momentum and adoption are not inferred from cumulative stars or citations.
  They remain unavailable until the tracker has enough dated observations.
- Readiness is separate from popularity.
- The MVP does not average model scores across incomparable benchmarks.
- There is no required ChatGPT sign-in; the published tracker is public.

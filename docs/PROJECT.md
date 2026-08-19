# Benchmark Radar project notes

Benchmark Radar is a public, GitHub-based tracker for newly released AI benchmarks. The repository homepage is the generated Awesome-style index; the website provides search, filters, time windows, and attention ranking.

## What is indexed

The first pipeline uses arXiv's official OAI-PMH feed across selected AI, language, vision, robotics, software, and graphics categories. A paper is published only when its primary-source metadata contains a named benchmark or evaluation-suite title, or an explicit sentence that introduces, releases, builds, or presents a benchmark.

Ambiguous matches are written to `data/review_queue.json`, not shown on the site. Code, data, and project links are copied only when source metadata provides the literal URL. Missing information remains unknown.

## Data and audit trail

- `data/benchmarks.json` is the canonical current snapshot.
- `data/benchmarks_index.json` is the compact UI view.
- `data/runs/` records source queries, counts, accepted IDs, confidence, and evidence.
- `data/review_queue.json` contains candidates that need human review.
- `data/metrics/` stores raw Hugging Face and GitHub observations.
- `data/domain_trends.json` stores a release-activity proxy; it is not technical progress.

## Daily update

`.github/workflows/daily-index.yml` tests the recognizer, indexes the latest arXiv release date, snapshots public attention signals, regenerates the GitHub homepage and web index, validates the site, and commits only validated data.

## Product boundaries

- Attention uses dated deltas when sufficient history exists; missing values are never treated as zero.
- Readiness is separate from popularity.
- The tracker does not average model scores across incomparable benchmarks.
- The published website is public and does not require ChatGPT sign-in.


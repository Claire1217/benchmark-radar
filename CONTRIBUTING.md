# Contributing

Thank you for helping improve Benchmark Radar. The fastest path is usually an issue with primary-source evidence; maintainers can then add a reviewed override without rewriting generated data.

## Suggest or correct data

Use the repository's structured issue forms for:

- a new Benchmark release;
- an incorrect field or resource link;
- a false positive or duplicate;
- conference/publication evidence.

A new entry must introduce, extend, or aggregate an evaluation Benchmark. A paper that only compares models on existing Benchmarks is not a new Benchmark entity.

Primary-source evidence includes an official paper, project, repository, dataset, OpenReview decision, proceedings page, or publisher record. Third-party summaries may help discovery but cannot confirm a field by themselves.

## Edit policy

Human-authored files:

- `web/`
- `pipeline/` and `pipeline/tests/`
- `docs/`
- `data/curated_overrides.json`
- `data/curated_records.json`

Generated files must not be edited directly:

- `data/benchmarks.json`
- `data/benchmarks_index.json`
- `data/domain_trends.json`
- `data/metrics/`, `data/publication/`, `data/runs/`
- `data/review_queue.json`
- `AWESOME_BENCHMARKS.md`

For a reviewed correction, add a narrowly scoped patch under the arXiv ID in `data/curated_overrides.json`. Include `curation.sources`, `reviewedAt`, and only the fields supported by those sources.

## Pull requests

1. Fork the repository and create a focused branch.
2. Make the smallest necessary source or override change.
3. Run `make test` and `make build`.
4. Open a pull request and complete the evidence checklist.

CI validates the canonical data, dependency-free JavaScript, pipeline tests, and the exact GitHub Pages artifact.

## Review principles

- Primary sources take precedence over third-party summaries.
- Missing information remains unknown rather than inferred.
- Popularity does not imply quality or readiness.
- Author-reported acceptance is labelled as a claim until official evidence is matched.
- Different releases, tracks, or evaluation protocols are not merged when results are incomparable.
- Semantic similarity may suggest a duplicate but cannot silently merge entities.

## Security

Never put API keys in issues, pull requests, data, or frontend code. Follow [SECURITY.md](SECURITY.md) for private reporting.

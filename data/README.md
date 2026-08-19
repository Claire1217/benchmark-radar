# Data directory

All files except `curated_overrides.json` and `curated_records.json` are generated. Do not edit generated files by hand.

| Path | Role | Retention |
|---|---|---|
| `benchmarks.json` | Canonical current snapshot | current snapshot |
| `benchmarks_index.json` | Compact website view | current snapshot |
| `curated_overrides.json` | Human-reviewed evidence patches | permanent |
| `curated_records.json` | Human-reviewed records from official non-arXiv sources | permanent |
| `domain_trends.json` | Weekly release-count series | current snapshot |
| `metrics/YYYY-MM-DD.json` | Raw public attention observation | dated history |
| `publication/YYYY-MM-DD.json` | Venue metadata refresh receipt | dated history |
| `runs/*.json` | Index queries, counts, and accepted evidence | audit history |
| `review_queue.json` | Machine candidates requiring review | current queue |

`review_queue.json` is not a recommendation list. Its records may be false positives.

## Generated-source policy

- The canonical snapshot is produced by `pipeline/index_benchmarks.py`.
- Reviewed corrections are applied from `curated_overrides.json`.
- Public indexes and Markdown are regenerated; direct edits will be overwritten.
- Schema and pipeline versions live in manifests.
- Missing source fields are represented as null/unknown, never fabricated.

The snapshot contains public scholarly metadata and short evidence snippets from primary sources. The repository does not redistribute paper PDFs or claim ownership of third-party titles, abstracts, links, or metrics.

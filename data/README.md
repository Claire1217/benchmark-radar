# Data directory

All files except `curated_overrides.json`, `curated_records.json`, `library_seed_records.json` are generated. Do not edit generated files by hand.

| Path | Role | Retention |
|---|---|---|
| `benchmarks.json` | Canonical current snapshot | current snapshot |
| `benchmarks_index.json` | Compact website view | current snapshot |
| `library_seed_records.json` | Editorial all-time families, variants, sources, model-report references, and catalog-discovery references | permanent |
| `library_records.json` | Validated Library seeds after Radar reconciliation | generated snapshot |
| `library_index.json` | Generated union of Library classics and recent Radar records | current snapshot |
| `curated_overrides.json` | Source-backed evidence patches | permanent |
| `curated_records.json` | Source-verified records from official non-arXiv sources | permanent |
| `domain_trends.json` | Weekly release-count series | current snapshot |
| `metrics/YYYY-MM-DD.json` | Raw public attention observation | dated history |
| `publication/YYYY-MM-DD.json` | Venue metadata refresh receipt | dated history |
| `runs/*.json` | Index queries, counts, and accepted evidence | audit history |
| `review_queue.json` | Persistent source-upsert queue awaiting automatic semantic classification | persistent queue |
| `ai_review_status.json` | Fingerprinted automatic promoted/deferred/rejected decisions and promoted canonical overlay | persistent audit ledger |

`review_queue.json` is not a recommendation list. Its records may be false positives.

## Generated-source policy

- The canonical snapshot is produced by `pipeline/index_benchmarks.py`.
- Ambiguous candidates may enter canonical data only when the DeepSeek
  classifier and critic agree and the exact evidence, URL, identity, duplicate,
  confidence, and canonical-schema gates pass.
- `pipeline/build_library_records.py` deterministically validates editorial seeds and removes Radar duplicates only when both normalized identity name and an official link match.
- Radar reads only `benchmarks_index.json`; Library records can never enter Today/30d/90d.
- Model-report references are retained as evidence pointers. They are not converted into dated `usageObservations` unless the seed supplies an explicit report date, named organization, context type, and primary-source URL.
- Reviewed corrections are applied from `curated_overrides.json`.
- Public indexes and Markdown are regenerated; direct edits will be overwritten.
- Schema and pipeline versions live in manifests.
- Missing source fields are represented as null/unknown, never fabricated.

The snapshot contains public scholarly metadata and short evidence snippets from primary sources. The repository does not redistribute paper PDFs or claim ownership of third-party titles, abstracts, links, or metrics.

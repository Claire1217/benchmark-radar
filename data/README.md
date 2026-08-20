# Data directory

All files except `curated_overrides.json`, `curated_records.json`, and `library_seed_records.json` are generated. Do not edit generated files by hand.

| Path | Role | Retention |
|---|---|---|
| `benchmarks.json` | Canonical current snapshot | current snapshot |
| `benchmarks_index.json` | Compact website view | current snapshot |
| `library_seed_records.json` | Editorial all-time families, variants, sources, model-report references, and catalog-discovery references | permanent |
| `library_records.json` | Validated Library seeds after Radar reconciliation | generated snapshot |
| `library_index.json` | Generated union of Library classics and recent Radar records | current snapshot |
| `curated_overrides.json` | Source-backed evidence patches | permanent |
| `curated_records.json` | Source-verified releases admitted from Paper, GitHub, and Hugging Face evidence | permanent |
| `editorial_copy.json` | AI admission decisions, third-person Description/Why it matters, and source-backed benchmark publishers | permanent |
| `domain_trends.json` | Weekly release-count series | current snapshot |
| `metrics/YYYY-MM-DD.json` | Raw public attention observation | dated history |
| `publication/YYYY-MM-DD.json` | Venue metadata refresh receipt | dated history |
| `runs/*.json` | Index queries, counts, and accepted evidence | audit history |
| `review_queue.json` | Source-upsert candidates awaiting Paper, GitHub, and Hugging Face evidence checks | persistent queue |

`review_queue.json` is not a recommendation list. Deterministic rules only recall candidates. GPT then classifies each candidate as a reusable public benchmark, viewpoint probe, use of an existing benchmark, non-benchmark, or unclear. Only reusable public benchmarks with a stable scoring contract and a public reuse path are admitted. The same call writes the public Description and Why it matters copy.

## Generated-source policy

- The canonical snapshot is produced by `pipeline/index_benchmarks.py`.
- Ambiguous candidates enter canonical data only after their Paper, GitHub, and
  Hugging Face evidence supports the product inclusion rules.
- `pipeline/build_library_records.py` deterministically validates editorial seeds and removes Radar duplicates only when both normalized identity name and an official link match.
- Radar reads only `benchmarks_index.json`; Library records can never enter Today/30d/90d.
- Model-report references are retained as evidence pointers. They are not converted into dated `usageObservations` unless the seed supplies an explicit report date, named organization, context type, and primary-source URL.
- Reviewed corrections are applied from `curated_overrides.json`.
- Public Description and Why it matters copy is generated from the paper with the OpenAI Responses API. Discovery evidence is never reused as editorial copy.
- Public indexes and Markdown are regenerated; direct edits will be overwritten.
- Schema and pipeline versions live in manifests.
- Missing source fields are represented as null/unknown, never fabricated.

The snapshot contains public scholarly metadata and short evidence snippets from primary sources. The repository does not redistribute paper PDFs or claim ownership of third-party titles, abstracts, links, or metrics.

# Data directory

The repository uses JSON in Git as its database. Files in this directory belong
to five different layers; they do not all have the same authority or retention
policy. Public pages must read only the generated public views listed below.

## 1. Editorial and canonical inputs

These files persist human or source-backed decisions. Do not replace them with
generated output.

| Path | Role |
|---|---|
| `curated_records.json` | Source-verified Radar releases admitted from Paper, GitHub, and Hugging Face evidence. |
| `curated_overrides.json` | Narrow, source-backed corrections to canonical Radar records. |
| `library_seed_records.json` | Editorial all-time benchmark families, variants, source links, and tracked-use references. |
| `editorial_copy.json` | Admission decisions and reviewed public copy. |
| `library_identity_merges.json` | Stable identity redirects for duplicate Library entities. |

## 2. Reviewed evidence overlays

These files are also durable inputs. They add one scoped fact to an existing
record and retain the evidence used for that decision. A resource review must
not silently change a release date or task classification.

| Path | Role |
|---|---|
| `library_source_reviews.json` | Reviewed additions, corrections, and code/data resource links. |
| `library_release_dates.json` | Supported release dates and their precision/evidence. |
| `repository_link_reviews.json` | Decisions linking or rejecting candidate GitHub repositories. |
| `repository_scope_reviews.json` | Whether repository stars represent the benchmark itself. |
| `research_topic_reviews.json` | Source-backed overrides for featured research-topic membership. |

## 3. Acquisition snapshots and operational state

These files are reproducible snapshots or persistent queues used to build the
public views. They are not direct frontend contracts.

| Path | Role | Retention |
|---|---|---|
| `benchmarks.json` | Canonical current Radar snapshot. | current |
| `catalog_records.json` | Normalized BenchLM, llm-stats, and supplemental catalog entities. | current |
| `library_records.json` | Validated Library seeds after Radar reconciliation. | current |
| `review_queue.json` | Candidates awaiting evidence review. | persistent queue |
| `github_repository_index.json` | Repository discovery evidence for Library records. | current |
| `github_repository_availability.json` | Latest GitHub availability observations. | current |
| `github_repository_aliases.json` | Confirmed repository redirects/renames. | persistent |
| `github_star_history.json` | Complete GitHub star-creation histories used by Trends. | current |
| `metrics/YYYY-MM-DD.json` | Dated public attention observations. | dated history |
| `publication/YYYY-MM-DD.json` | Dated venue metadata receipts. | dated history |
| `runs/*.json` | Retrieval and indexing receipts. | audit history |

`data/repository_audit/` contains resumable downloaded source-page caches. It
is ignored by Git and must never be treated as product data.

## 4. Generated public views

These files are build artifacts and must not be edited by hand.

| Path | Consumer |
|---|---|
| `benchmarks_index.json` | Radar. |
| `library_index.json` | Library and the canonical taxonomy used across surfaces. |
| `domain_trends.json` | Legacy domain summaries on the main site. |
| `trends_topics.json` | Topic-level release and GitHub attention Trends. |
| `trends_comparison.json` | Supporting Trends comparison snapshot. |
| `github_history_coverage.json` | Published GitHub-history coverage receipt. |
| `research_topic_audit.json` | Published topic consistency audit. |

`library_index.json.manifest.recordCount` is the number of stored records,
including retained negative review outcomes. `displayRecordCount` is the number
shown in Library and eligible for Trends. `hiddenRecordCount` is the difference.
Keeping these counts explicit prevents review records from being mistaken for
public entries.

## 5. Audit deliverables

Human-readable investigation receipts live under `docs/audits/`. They can
explain a decision but never override a data file. Large continuation scripts,
downloaded page bodies, and local caches should remain untracked unless a small
summary is intentionally selected for long-term review.

## Build contract

The canonical Radar snapshot is produced by `pipeline/index_benchmarks.py`.
Library overlays are applied before repository and metric snapshots so reviewed
code/data links can receive current GitHub metadata. The generated views are
then rebuilt and validated before GitHub Pages is assembled:

```text
canonical inputs + reviewed overlays
  -> benchmarks.json / library_records.json / catalog_records.json
  -> library_index.json
  -> benchmarks_index.json / trends_topics.json / other public views
  -> _site/data/*.json
```

- Radar reads only `benchmarks_index.json`; Library-only records never enter its
  Latest/30d/90d feeds.
- Library and Trends use the same `displayEligible` rule.
- Catalog-only records remain searchable but do not become Radar releases.
- Missing dates, repositories, and metrics remain unknown rather than being
  inferred from unrelated artifacts.
- Model-report references remain evidence pointers unless the record includes
  a dated, named, primary-source usage observation.
- `pipeline/validate_data.py` checks stored and displayed record counts before a
  website build can succeed.

The snapshot contains public scholarly metadata and short evidence snippets
from primary sources. It does not redistribute paper PDFs.

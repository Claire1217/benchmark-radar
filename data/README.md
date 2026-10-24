# Data directory

The repository uses JSON in Git as its persistence layer. The field-level ownership,
actual update order and known modeling gaps are documented in
[`docs/data-model.md`](../docs/data-model.md); the machine-readable asset contract is
[`pipeline/data_contract.json`](../pipeline/data_contract.json). Files in this directory belong
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
| `model_eval_updates.json` | Reviewed provider model releases, exact evaluation settings, scores, coverage-only disclosures, sources and explicit Library IDs. |

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
| `trends_topics.json` | Topic-level release and GitHub attention Trends. |
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

The Radar snapshot is persistent materialized state: discovery/admission,
`apply_overrides`, publication enrichment and metrics enrichment update it. It is
not fully rebuildable from `curated_records.json` alone.
Library overlays are applied before repository and metric snapshots so reviewed
code/data links can receive current GitHub metadata. The generated views are
then rebuilt and validated before GitHub Pages is assembled:

```text
canonical inputs + reviewed overlays
  -> benchmarks.json / library_records.json / catalog_records.json
  -> benchmarks_index.json and library_index.json (Library assembly synchronizes shared classification back into Radar)
  -> trends_topics.json / other public views
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
- Run `make update-model-evals` after editing the reviewed model evidence.
  `pipeline/update_model_evals.py` updates the embedded Model Evals dataset and
  `model_eval_references.json`; the Library generator then projects the links.
  `make build` includes this step. Historical imported dates/counts remain
  unchanged; `manifest.reviewedUpdates` describes the additional review.
- New results preserve report dates, versions, subsets, tool access, effort,
  harnesses and fallbacks. `Reported` means the official source discloses the
  evaluation but its absolute numeric value has not been transcribed. It does
  not enter charts or become zero. Elo snapshots use the latest report, rather
  than the highest historical value. Multiple effort results remain inspectable.
- `pipeline/validate_data.py` checks stored and displayed record counts before a
  website build can succeed.

The snapshot contains public scholarly metadata and short evidence snippets
from primary sources. It does not redistribute paper PDFs.

## Website loading

The static build creates compact `radar_view.json` and `library_view.json`
presentation projections. `pipeline/site_views.py` explicitly retains fields
used by cards, filtering, search and sorting; nested audit receipts stay in the
complete public downloads. Rendering-equivalence tests protect the projections.

`pipeline/render_home.cjs` uses the actual browser renderer to build the latest
feed into `index.html`. An embedded bootstrap includes the same complete release
days and category definitions. The first screen requires no JSON requests.
Full Radar history loads when a user requests another window or previous day;
Library loads on navigation or deliberate pointer/keyboard intent. Generated
data URLs and scripts are versioned by content hash. Library search covers all
records, while the DOM initially contains at most 60 result cards.

Run `make audit-data-contract` for read-only ownership and cross-file integrity checks.
Known unresolved warnings remain individually tracked; a passing check does not
mean all identity bindings or historical decisions have been verified.

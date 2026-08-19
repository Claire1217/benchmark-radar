# Architecture

Benchmark Radar is deliberately small: Git is the auditable database, GitHub Actions is the daily batch processor, and GitHub Pages serves immutable static files.

See [DATA_FLOW_DIAGRAMS.md](DATA_FLOW_DIAGRAMS.md) for the system overview,
storage lineage, admission state machine, daily sequence, and entity model.

## Data flow

```text
official sources ──► high-recall candidate upsert ──► persistent candidate state
                                                        │
                                                        ▼
                                      DeepSeek classifier + blind critic
                                                        │
                          ┌─────────────────────────────┼─────────────────────────┐
                          ▼                             ▼                         ▼
                  reusable release             insufficient evidence      study / existing use
                          │                             │                         │
                          ▼                             ▼                         ▼
                  canonical reconcile          retry or defer ledger       audit ledger only
                          │
                          ├──► active-window attention snapshots
                          ├──► publication metadata enrichment
                          └──► Radar + Library + Trends ──► one static Pages artifact
```

## Radar, Library, and Trends

These are separate views over separate evidence contracts:

- **Radar** reads only the recent-release canonical snapshot. Its Today, 30-day, and 90-day filters never query the all-time Library.
- **Library** is the searchable union of Radar records and source-verified established benchmarks in `data/library_records.json`.
- **Trends** has two independent signals: new benchmark releases from Radar, and timestamped, source-linked usage observations from both recent and established benchmarks. Adding an old benchmark to the Library does not create a fake present-day trend.

A usage observation records who used which benchmark, when, in what context, and the primary source URL. Counts are deduplicated by benchmark, organization, and week.

The workflow is fail-closed: validation completes before generated data is committed or the Pages artifact is deployed. A failed run leaves the previous public site online.
Daily indexing and deployment share one concurrency lock. Candidate discovery,
AI admission, enrichment, view generation, validation, and commit happen in one
daily workflow and in that order. The promotion ledger is also a persistent
canonical overlay, so replaying a source date cannot delete an earlier gated
promotion.

## Components

- `web/` is the only frontend. It is dependency-free HTML, CSS, and JavaScript.
- `pipeline/index_benchmarks.py` discovers and prioritizes candidates but never
  directly publishes new arXiv records.
- `pipeline/review_candidates_with_deepseek.py` runs independent DeepSeek
  classifier and critic passes. Regex only prioritizes the queue; code enforces
  exact-source, URL/date, duplicate, and canonical-schema integrity gates.
- `pipeline/enrich_metrics.py` snapshots public attention signals.
- `pipeline/enrich_publications.py` records author-provided arXiv venue metadata without upgrading it to official acceptance.
- `pipeline/generate_*` builds public views from the canonical snapshot.
- `pipeline/generate_library_index.py` builds the all-time search view without mutating Radar.
- `pipeline/build_github_pages.py` assembles `_site/`; the directory is local build output and is not committed.
- `data/curated_overrides.json` is the source-backed correction layer. Machine refreshes cannot silently erase it.

## Automation

- `ci.yml` validates every pull request and push.
- `daily-index.yml` performs one end-to-end daily transaction: discover,
  classify, reconcile, enrich, generate, validate, and commit. DeepSeek safely
  skips when its key is not configured. It runs at 14:17
  `Australia/Brisbane` and indexes the previous Brisbane calendar day; it never
  silently substitutes a different source date.
- `deploy-pages.yml` publishes once after the daily transaction succeeds.

No browser receives API credentials. External APIs are called only by the indexing workflow.

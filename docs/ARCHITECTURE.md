# Architecture

Benchmark Radar is deliberately small: Git is the auditable database, GitHub Actions is the daily batch processor, and GitHub Pages serves immutable static files.

## Data flow

```text
arXiv OAI-PMH
      │
      ▼
candidate recognition ── explicit release ──► recent canonical snapshot ──► Radar
      │                                               │
      │ ambiguous                                     ├──► attention / venue metadata
      ▼                                               └──► release trend signal
review queue ──► AI semantic shadow review
                    │
                    └──► human-reviewed promotion only

official benchmark sources ──► reviewed all-time Library ──► usage trend signal

Radar + Library + Trends ──► static GitHub Pages artifact
```

## Radar, Library, and Trends

These are separate views over separate evidence contracts:

- **Radar** reads only the recent-release canonical snapshot. Its Today, 30-day, and 90-day filters never query the all-time Library.
- **Library** is the searchable union of Radar records and human-reviewed established benchmarks in `data/library_records.json`.
- **Trends** has two independent signals: new benchmark releases from Radar, and timestamped, source-linked usage observations from both recent and established benchmarks. Adding an old benchmark to the Library does not create a fake present-day trend.

A usage observation records who used which benchmark, when, in what context, and the primary source URL. Counts are deduplicated by benchmark, organization, and week.

The workflow is fail-closed: validation completes before generated data is committed or the Pages artifact is deployed. A failed run leaves the previous public site online.

## Components

- `web/` is the only frontend. It is dependency-free HTML, CSS, and JavaScript.
- `pipeline/index_benchmarks.py` discovers explicit benchmark releases.
- `pipeline/enrich_metrics.py` snapshots public attention signals.
- `pipeline/enrich_publications.py` records author-provided arXiv venue metadata without upgrading it to official acceptance.
- `pipeline/generate_*` builds public views from the canonical snapshot.
- `pipeline/generate_library_index.py` builds the all-time search view without mutating Radar.
- `pipeline/build_github_pages.py` assembles `_site/`; the directory is local build output and is not committed.
- `data/curated_overrides.json` is the human-reviewed correction layer. Machine refreshes cannot silently erase it.

## Automation

- `ci.yml` validates every pull request and push.
- `daily-index.yml` refreshes the index once per day and supports manual runs.
- `deploy-pages.yml` publishes the exact static artifact to GitHub Pages.

No browser receives API credentials. External APIs are called only by the indexing workflow.

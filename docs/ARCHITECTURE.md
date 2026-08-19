# Architecture

Benchmark Radar is deliberately small: Git is the auditable database, GitHub Actions is the daily batch processor, and GitHub Pages serves immutable static files.

## Data flow

```text
arXiv OAI-PMH
      │
      ▼
candidate recognition ── ambiguous ──► review queue
      │ explicit release
      ▼
canonical snapshot
      │
      ├──► Hugging Face / GitHub attention observations
      ├──► arXiv venue metadata
      ├──► curated evidence overrides
      └──► compact index + domain trends + Awesome list
                                      │
                                      ▼
                              GitHub Pages artifact
```

The workflow is fail-closed: validation completes before generated data is committed or the Pages artifact is deployed. A failed run leaves the previous public site online.

## Components

- `web/` is the only frontend. It is dependency-free HTML, CSS, and JavaScript.
- `pipeline/index_benchmarks.py` discovers explicit benchmark releases.
- `pipeline/enrich_metrics.py` snapshots public attention signals.
- `pipeline/enrich_publications.py` records author-provided arXiv venue metadata without upgrading it to official acceptance.
- `pipeline/generate_*` builds public views from the canonical snapshot.
- `pipeline/build_github_pages.py` assembles `_site/`; the directory is local build output and is not committed.
- `data/curated_overrides.json` is the human-reviewed correction layer. Machine refreshes cannot silently erase it.

## Automation

- `ci.yml` validates every pull request and push.
- `daily-index.yml` refreshes the index once per day and supports manual runs.
- `deploy-pages.yml` publishes the exact static artifact to GitHub Pages.

No browser receives API credentials. External APIs are called only by the indexing workflow.

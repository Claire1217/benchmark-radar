# GitHub repository indexing audit — 2026-09-15

Scanned all 2,855 Library records against linked paper, project, and dataset sources. Source evidence is retained in `data/github_repository_index.json`; no downloaded page bodies or credentials are published.

- 698 records have source-linked repository associations, including existing Code links.
- 84 previously missing Code links were added conservatively.
- 310 records have candidates that need review; 1,847 remain unresolved. Inaccessible sources do not establish that a repository does not exist.
- Four newly proposed repositories returned 404 and were excluded from added Code links.
- Star history: 473 complete histories out of 486 requested benchmark repositories; 13 returned 404.
- RSI has 8 complete repository histories. Repositories are deduplicated within each direction; directions may overlap.

Attention growth counts stars created per week for a fixed covered repository cohort. It is not net change after unstars, and does not represent repositories lacking complete history. Hosting and mixed project repositories are excluded from benchmark-specific totals. Missing coverage is not zero. Release charts currently cover the recent indexed release corpus, not all historical publications.

## Reproduction

Run `python3 pipeline/index_github_repositories.py`, `python3 pipeline/generate_library_index.py`, `python3 pipeline/fetch_github_history.py`, then `make build`. History refresh uses GH_TOKEN/GITHUB_TOKEN or the existing local GitHub credential without logging it. Source downloads are cached under ignored `data/repository_audit/`. Review proposed mappings and HTTP failures before publication. This batch is not a newly scheduled automatic history refresh.

Validation: 173 pipeline tests passed; static build, JavaScript syntax, and artifact checks passed. Local chart checks covered all time ranges, RSI aggregate history, and optional contributor exclusion.

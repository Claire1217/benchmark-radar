# Benchmark Radar

[![Daily index](https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml/badge.svg)](https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml)
[![Deploy Pages](https://github.com/Claire1217/benchmark-radar/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/Claire1217/benchmark-radar/actions/workflows/deploy-pages.yml)
[![CI](https://github.com/Claire1217/benchmark-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/Claire1217/benchmark-radar/actions/workflows/ci.yml)

A source-audited, daily-updated tracker for newly released AI benchmarks.

- **[Open Benchmark Radar →](https://claire1217.github.io/benchmark-radar/)**
- **[Browse the full Awesome list →](AWESOME_BENCHMARKS.md)**

Benchmark Radar helps answer two different questions:

- **What is new?** First public releases indexed from primary-source metadata.
- **What is receiving attention?** Hugging Face votes, GitHub stars, and Hugging Face dataset downloads, shown separately from quality and readiness.

The default view is **30 days · Attention**. Users can switch to Today, 90 days, or Newest; inspect domain activity in Trends; and keep a device-local Saved list.

A separate future `Watch` badge will forecast independent adoption. It is intentionally in shadow mode until enough historical outcomes exist for time-based backtesting; it will not be faked from current stars or institution prestige.

> This is a discovery index, not an endorsement, model leaderboard, or prediction guarantee. Missing evidence remains unknown. Popularity never changes readiness.

## Current scope

- 90-day benchmark-release snapshot
- arXiv OAI-PMH as the primary discovery source
- Hugging Face and GitHub public attention signals
- author-reported venue metadata from arXiv, clearly labelled as a claim
- GitHub Actions daily refresh and GitHub Pages deployment

Conference status is evidence-tiered. `Acceptance claimed` means an arXiv author comment; it is not upgraded to `Accepted` until an official OpenReview decision or conference source is matched.

## Repository map

| Path | Purpose | Edit directly? |
|---|---|---|
| `web/` | Dependency-free GitHub Pages frontend | Yes |
| `pipeline/` | Indexing, enrichment, validation, and build scripts | Yes |
| `pipeline/tests/` | Deterministic pipeline tests | Yes |
| `data/curated_overrides.json` | Reviewed corrections backed by primary sources | Yes, with evidence |
| `data/curated_records.json` | Reviewed official releases not discoverable through arXiv | Yes, with evidence |
| `data/benchmarks.json` | Generated canonical snapshot | No |
| `data/benchmarks_index.json` | Generated compact website index | No |
| `data/metrics/`, `data/publication/`, `data/runs/` | Generated observations and audit receipts | No |
| `AWESOME_BENCHMARKS.md` | Generated human-readable catalogue | No |
| `docs/` | Architecture, methodology, and data documentation | Yes |

## Local development

The published site has no runtime framework and no account system.

```bash
make test
make build
make serve
```

Then open `http://localhost:8000`. `make serve` is local-only; the update commands below access public external APIs.

To refresh generated views from the existing canonical snapshot:

```bash
make generate
```

To run a new daily index, read [CONTRIBUTING.md](CONTRIBUTING.md) first; the command updates tracked data.

## Design and data

- [Architecture](docs/ARCHITECTURE.md)
- [Indexing, attention, readiness, and venue methodology](docs/METHODOLOGY.md)
- [Data files and generated-source policy](data/README.md)
- [Contribution guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Privacy

The public site has no login, analytics, or cookies. Saved benchmarks are stored only in the visitor's browser using `localStorage`; they are not uploaded and do not sync across devices.

## License status

No open-source code or data license has been selected yet. Public visibility permits inspection, but does not itself grant reuse rights. Code and third-party-derived metadata will receive separate, explicit terms before the project invites broad reuse.

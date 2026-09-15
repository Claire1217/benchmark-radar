<h1 align="center"><img src="web/benchmark-radar-mark.png" width="38" height="38" alt=""> Benchmark Radar — AI Benchmark Tracker and Library</h1>

<p align="center"><strong>Benchmark Radar</strong> is the official daily-updated AI benchmark tracker and searchable benchmark library. This GitHub repository powers <a href="https://benchmark-radar.com/">benchmark-radar.com</a>, indexing public evaluation benchmarks, papers, code, datasets, attention signals, and use in model reports.</p>

<p align="center">
  <strong><a href="https://benchmark-radar.com/">Official Benchmark Radar website →</a></strong>
  &nbsp;·&nbsp;
  <strong><a href="https://benchmark-radar.com/#radar">Open Radar →</a></strong>
  &nbsp;·&nbsp;
  <strong><a href="https://benchmark-radar.com/#library">Browse Library →</a></strong>
  &nbsp;·&nbsp;
  <strong><a href="https://benchmark-radar.com/#trends">Explore Trends →</a></strong>
</p>

<p align="center">
  <a href="https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml"><img src="https://github.com/Claire1217/benchmark-radar/actions/workflows/daily-index.yml/badge.svg" alt="Daily update"></a>
  <a href="https://github.com/Claire1217/benchmark-radar/actions/workflows/ci.yml"><img src="https://github.com/Claire1217/benchmark-radar/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

<p align="center">
  <a href="https://benchmark-radar.com/#radar">
    <img src="docs/assets/benchmark-radar-overview.png" alt="Benchmark Radar showing emerging benchmarks ranked by public attention" width="1200">
  </a>
</p>

## Hot this month

<!-- GENERATED_OVERVIEW_START -->
<sub>Updated 2026-09-15 · benchmarks first released in September 2026</sub>

| # | Benchmark | Field | Public signals |
|---:|---|---|---|
| 1 | **Last Translation Benchmark**<br><sub>[Paper](https://arxiv.org/abs/2609.04173)</sub> | Multimodal Perception | 40 HF votes · 53 GitHub stars |
| 2 | **Φ-Bench**<br><sub>[Paper](https://arxiv.org/abs/2609.10226)</sub> | Coding & Software Engineering | 21 HF votes · 59 GitHub stars |
| 3 | **VWG-Bench**<br><sub>[Paper](https://arxiv.org/abs/2609.11242)</sub> | Multimodal Perception | 780 dataset downloads |
| 4 | **WearableQA**<br><sub>[Paper](https://arxiv.org/abs/2609.05405)</sub> | Knowledge & Reasoning | 38 HF votes · 17 GitHub stars |
| 5 | **DriveMotion**<br><sub>[Paper](https://arxiv.org/abs/2609.08117)</sub> | Multimodal Perception | 188 dataset downloads |
| 6 | **EdgeMosaic**<br><sub>[Paper](https://github.com/michailfragkiskos/EdgeMosaic) · [Code](https://github.com/michailfragkiskos/EdgeMosaic)</sub> | Knowledge & Reasoning | 28 GitHub stars |
| 7 | **CivBench**<br><sub>[Paper](https://arxiv.org/abs/2609.02459) · [Code](https://github.com/lmwilki/civ6-mcp)</sub> | Knowledge & Reasoning | 0 HF votes · 178 GitHub stars |
| 8 | **VANTAGE-BENCH**<br><sub>[Paper](https://arxiv.org/abs/2609.09396)</sub> | Multimodal Perception | 6 HF votes · 2,244 dataset downloads |
| 9 | **RoboSPA**<br><sub>[Paper](https://arxiv.org/abs/2609.05324) · [Code](https://github.com/fanzhenxuan/RoboSPA)</sub> | Robotics & Embodied Intelligence | 28 HF votes · 16 GitHub stars |
| 10 | **$\tau^\tau$-Bench: An Environment for End-To-End, Realistic Agent Construction**<br><sub>[Paper](https://arxiv.org/abs/2609.04611)</sub> | Agents | 15 HF votes · 23 GitHub stars |

### Explore the library

| Research themes | Task capabilities |
|---|---|
| [Self-Improvement & RSI](https://benchmark-radar.com/#library?direction=self-improvement-rsi) · 22<br>[AI for Science](https://benchmark-radar.com/#library?direction=ai-for-science) · 144 | [Coding Agents](https://benchmark-radar.com/#library?direction=coding-agents) · 99<br>[Vision-Language Models](https://benchmark-radar.com/#library?direction=vision-language-models) · 535<br>[Safety & Alignment](https://benchmark-radar.com/#library?direction=safety-alignment) · 282<br>[Knowledge & QA](https://benchmark-radar.com/#library?direction=knowledge-qa) · 248<br>[Software Engineering](https://benchmark-radar.com/#library?direction=software-engineering) · 259<br>[Data Analysis](https://benchmark-radar.com/#library?direction=data-analysis) · 65 |

**[Browse all 2,664 Library records →](https://benchmark-radar.com/#library)**
<!-- GENERATED_OVERVIEW_END -->

## What you can find

| Radar | Library | Trends |
|---|---|---|
| Newly released, public, reusable evaluation benchmarks | Established benchmarks ranked by tracked use and public evaluation coverage | Monthly benchmark activity and the benchmarks shaping each field |

Attention uses observable Hugging Face and GitHub signals. One real signal is enough to rank; missing data is not treated as zero.

The generated **[Awesome AI Benchmarks catalogue](AWESOME_BENCHMARKS.md)** provides the complete source-linked list.

<details>
<summary><strong>Data, methodology, and project information</strong></summary>

### Data policy

Daily release discovery checks arXiv, GitHub, Hugging Face, and OpenReview, then deduplicates candidates before semantic review. Records are linked to their original papers, projects, code, and datasets where available. Catalog discovery is attributed to BenchLM and llm-stats; release identity and corrections are checked against primary sources.

Daily updates preserve real observation dates. Benchmark Radar does not invent historical attention or adoption. It is a discovery index—not a quality endorsement, model leaderboard, or prediction guarantee.

### Project links

- [Report a correction](https://github.com/Claire1217/benchmark-radar/issues/new/choose)
- [Methodology](docs/METHODOLOGY.md)
- [Public data](data/README.md)
- [Contributing](CONTRIBUTING.md)
- [Architecture](docs/ARCHITECTURE.md)

The public website has no login, analytics, or cookies. Saved benchmarks remain in the visitor's browser.

### License status

No open-source code or data license has been selected yet. Public visibility permits inspection, but does not itself grant reuse rights. Code and third-party-derived metadata will receive separate, explicit terms before the project invites broad reuse.

</details>

## Agent CLI

Query benchmark usage evidence with `./benchmark-reader search gpqa` and `./benchmark-reader show lib_gpqa_diamond`. Use `./benchmark-reader daily` for daily releases and `./benchmark-reader hot --window 7d` (or `90d`) for hot lists. Add keywords, `--domain`, or `search --sort attention`. All queries return JSON for Agents; `--json` is optional. Use `--help` for commands and examples. See the [CLI contract and data definitions](docs/CLI.md) for source coverage, version alignment, pagination and unknown values.

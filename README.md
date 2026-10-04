<h1 align="center"><img src="web/benchmark-radar-mark.png" width="38" height="38" alt=""> Benchmark Radar — AI Benchmark Tracker and Library</h1>

<p align="center"><strong>Benchmark Radar</strong> is the official daily-updated AI benchmark tracker and searchable benchmark library. This GitHub repository powers <a href="https://benchmark-radar.com/">benchmark-radar.com</a>, indexing public evaluation benchmarks, papers, code, datasets, attention signals, and use in model reports.</p>

<p align="center">
  <strong><a href="https://benchmark-radar.com/">Official Benchmark Radar website →</a></strong>
  &nbsp;·&nbsp;
  <strong><a href="https://benchmark-radar.com/#radar">Open Radar →</a></strong>
  &nbsp;·&nbsp;
  <strong><a href="https://benchmark-radar.com/#library">Browse Library →</a></strong>
  &nbsp;·&nbsp;
  <strong><a href="https://benchmark-radar.com/trends/">Explore Trends →</a></strong>
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
<sub>Updated 2026-10-03 · benchmarks first released in October 2026</sub>

| # | Benchmark | Field | Public signals |
|---:|---|---|---|
| 1 | **DAYJOB**<br><sub>[Paper](https://arxiv.org/abs/2610.01306) · [Code](https://github.com/surge-ai/dayjob)</sub> | Personal & Enterprise Agents | 4 GitHub stars |
| 2 | **Ego2Act**<br><sub>[Paper](https://arxiv.org/abs/2610.01092)</sub> | Embodied AI & VLA · Image & Video Generation | 21 HF votes · 1 GitHub stars |
| 3 | **DrillBench**<br><sub>[Paper](https://arxiv.org/abs/2610.01204) · [Code](https://github.com/yihaoding/drillbench)</sub> | Other benchmark tasks | 0 GitHub stars |

### Explore the library

| Agent research | Related research |
|---|---|
| [Coding Agents](https://benchmark-radar.com/#library?direction=coding-agents) · 140<br>[Computer Use](https://benchmark-radar.com/#library?direction=computer-use) · 53<br>[Deep Research & Web Search](https://benchmark-radar.com/#library?direction=search-research) · 41<br>[Tool Use](https://benchmark-radar.com/#library?direction=tool-use) · 82<br>[Agent Memory](https://benchmark-radar.com/#library?direction=agent-memory) · 30<br>[Multi-Agent Systems](https://benchmark-radar.com/#library?direction=multi-agent) · 23<br>[Personal & Enterprise Agents](https://benchmark-radar.com/#library?direction=personal-workplace) · 64<br>[Data Analysis Agents](https://benchmark-radar.com/#library?direction=data-analysis-agents) · 27<br>[AI Research Agents](https://benchmark-radar.com/#library?direction=ai-research-agents) · 22<br>[Self-Improving Agents](https://benchmark-radar.com/#library?direction=self-improving-agents) · 16<br>[Agent Harnesses & Skills](https://benchmark-radar.com/#library?direction=agent-harness-skills) · 11<br>[Agent Safety & Security](https://benchmark-radar.com/#library?direction=agent-safety-security) · 85<br>[Scientific Agents](https://benchmark-radar.com/#library?direction=scientific-agents) · 33 | [OCR & Document Understanding](https://benchmark-radar.com/#library?direction=ocr-documents) · 43<br>[Video Understanding](https://benchmark-radar.com/#library?direction=video-understanding) · 86<br>[Speech & Audio](https://benchmark-radar.com/#library?direction=realtime-multimodal) · 89<br>[World Models](https://benchmark-radar.com/#library?direction=world-models) · 22<br>[Embodied AI & VLA](https://benchmark-radar.com/#library?direction=embodied-vla) · 106<br>[Image & Video Generation](https://benchmark-radar.com/#library?direction=image-video-generation) · 76<br>[Efficient Inference](https://benchmark-radar.com/#library?direction=efficient-inference) · 13 |

**[Browse all 3,133 Library records →](https://benchmark-radar.com/#library)**
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

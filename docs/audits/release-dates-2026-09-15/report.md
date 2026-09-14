# Release-date audit — 2026-09-15

- 2,855 public records; 1,053 previously had unknown release dates.
- Added 37 benchmark-specific, primary-source-backed dates; 1,016 remain unverified.
- All seven examples supplied by the user are covered.
- 164 tests and static-site validation passed; browser checks covered date rendering, source links, both BioMysteryBench subsets, and mobile overflow.

## Policy

Paper v1 publication and official public announcement are separate display labels. Neither claims the earliest internal use or earliest possible artifact. No ingestion date, repository creation time, model-report year, or unreviewed catalog year is used as a release date. Reviewed dates live outside catalog snapshots and are applied after identity merges on every Library generation. Year-only evidence retains year precision.

## Rejected shortcuts

- BenchLM source years frequently reflect a 2026 model report for much older benchmarks. They are not safe release-date defaults.
- FinanceArena links to a FinanceQA paper: identity mismatch, not automatically accepted.
- MATH-500 links to the original MATH paper: parent publication does not establish subset release.
- BioLP DOI contains 2024-08-21, but the bioRxiv version API reports v1 as 2024-08-26.
- BioMysteryBench appeared in earlier model evaluations; 2026-04-29 is explicitly labelled its public announcement, not first use. Both subsets are described in that announcement.

## Applied dates

| Benchmark | Date | Basis | Source |
|---|---|---|---|
| BBH | 2022-10-17 | paper-v1 | [source](https://arxiv.org/abs/2210.09261) |
| C-Eval | 2023-05-15 | paper-v1 | [source](https://arxiv.org/abs/2305.08322) |
| Claw-Eval | 2026-04-07 | paper-v1 | [source](https://arxiv.org/abs/2604.06132) |
| Cybench | 2024-08-15 | paper-v1 | [source](https://arxiv.org/abs/2408.08926) |
| DeepPlanning | 2026-01-26 | paper-v1 | [source](https://arxiv.org/abs/2601.18137) |
| ExploitGym | 2026-05-11 | paper-v1 | [source](https://arxiv.org/abs/2605.11086) |
| GameDevBench | 2026-02-11 | paper-v1 | [source](https://arxiv.org/abs/2602.11103) |
| GMMLU | 2024-12-04 | paper-v1 | [source](https://arxiv.org/abs/2412.03304) |
| HLE-Verified | 2026-02-15 | paper-v1 | [source](https://arxiv.org/abs/2602.13964) |
| IDE-Bench | 2026-01-28 | paper-v1 | [source](https://arxiv.org/abs/2601.20886) |
| JobBench | 2026-05-25 | paper-v1 | [source](https://arxiv.org/abs/2605.26329) |
| KMMLU | 2024-02-18 | paper-v1 | [source](https://arxiv.org/abs/2402.11548) |
| LABBench2 | 2026-02-04 | paper-v1 | [source](https://arxiv.org/abs/2604.09554) |
| LiveCodeBench Pro | 2025-06-13 | paper-v1 | [source](https://arxiv.org/abs/2506.11928) |
| Market-Bench | 2025-12-13 | paper-v1 | [source](https://arxiv.org/abs/2512.12264) |
| MGSM | 2022-10-06 | paper-v1 | [source](https://arxiv.org/abs/2210.03057) |
| MILU | 2024-11-04 | paper-v1 | [source](https://arxiv.org/abs/2411.02538) |
| MMLU-ProX | 2025-03-13 | paper-v1 | [source](https://arxiv.org/abs/2503.10497) |
| MuSR | 2023-10-24 | paper-v1 | [source](https://arxiv.org/abs/2310.16049) |
| OCRBench V2 | 2024-12-31 | paper-v1 | [source](https://arxiv.org/abs/2501.00321) |
| OfficeQA Pro | 2026-03-09 | paper-v1 | [source](https://arxiv.org/abs/2603.08655) |
| OpenBookQA | 2018-09-08 | paper-v1 | [source](https://arxiv.org/abs/1809.02789) |
| Pencil Puzzle Bench | 2026-03-02 | paper-v1 | [source](https://arxiv.org/abs/2603.02119) |
| ScreenSpot Pro | 2025-04-04 | paper-v1 | [source](https://arxiv.org/abs/2504.07981) |
| SuperGPQA | 2025-02-20 | paper-v1 | [source](https://arxiv.org/abs/2502.14739) |
| TruthfulQA | 2021-09-08 | paper-v1 | [source](https://arxiv.org/abs/2109.07958) |
| WildBench | 2024-06-07 | paper-v1 | [source](https://arxiv.org/abs/2406.04770) |
| AI2 Reasoning Challenge (ARC) | 2018-03-14 | paper-v1 | [source](https://arxiv.org/abs/1803.05457) |
| ARC-E | 2018-03-14 | paper-v1 | [source](https://arxiv.org/abs/1803.05457) |
| ARC-Easy | 2018-03-14 | paper-v1 | [source](https://arxiv.org/abs/1803.05457) |
| ARC-C | 2018-03-14 | paper-v1 | [source](https://arxiv.org/abs/1803.05457) |
| ARC-Challenge | 2018-03-14 | paper-v1 | [source](https://arxiv.org/abs/1803.05457) |
| BioLP-Bench | 2024-08-26 | paper-v1 | [source](https://www.biorxiv.org/content/10.1101/2024.08.21.608694v1) |
| AutoResearchExam | 2026-09-10 | official-announcement | [source](https://bespokelabs.ai/blog/introducing-autoresearchexam) |
| BioMysteryBench | 2026-04-29 | official-announcement | [source](https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench) |
| BioMysteryBench (human-difficult) | 2026-04-29 | official-announcement | [source](https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench) |
| BioMysteryBench (human-solvable) | 2026-04-29 | official-announcement | [source](https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench) |

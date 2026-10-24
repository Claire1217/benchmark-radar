# Model Evals source audit — 2026-10-24

Kimi K3.1 Pro's complete official release table has 47 rows, represented here as **48 separate metrics** (ZeroBench avg@5 and pass@5 are split). All 48 numbers were compared with the captured table. The **29 existing peer results** in these same charts were individually checked against their provider's release report/model-card table. That is **77 displayed report records**, not all historical models in the site. Separately, all six columns of Moonshot’s full table were captured: **252 numeric cells and 36 missing cells** across 48 metric views. Competitor columns are attributed to Moonshot; transcription does not validate the underlying runs.

**A matched transcription is not an independent validation.** Core rankings now use only explicitly audited benchmark-maintainer evaluations. The second chart reproduces the selected publisher’s single source table with dashed bars in source column order. It does not combine different model releases. Competitor columns are publisher comparisons, not competitor self-reports. Models whose complete comparison table has not been captured show only their own collected score and an explicit notice. Missing results are not zeros. No official ranking is inferred from a provider report, an aggregator estimate, or an incompatible version/subset/metric.

Twelve metric charts have captured compatible official ranking views. Kimi itself is directly confirmed in three: GDPval-AA v2.1 (1845.72 → 1846 Elo), AA-Briefcase v1.1 (1677.79 → 1678 Elo), and AutomationBench-AA (73.2977 → 73.3%). The other 36 metrics have no eligible official ranking in this audit; the individual reasons below distinguish internal benchmarks, protocol ambiguity, republications and unavailable matching evaluations. This does not claim that no such evaluation exists anywhere.

Terminal-Bench 4.0 is the original error: provider reports were presented as a general ranking. The official snapshot has Opus 5.5 64.8%, Sonnet 5.5 61.8%, and Astra Max 58.2%; Kimi K3.1 Pro is absent. Moonshot’s Terminal chart contains Kimi 65.7, Fable 57.9, Astra 58.2, Opus 66.4, DeepSeek 42.3 and GLM 41.8. Sonnet 70.6 is from a different report and no longer appears in Kimi’s publication comparison. Fable 5.1's 55.8% is confirmed in **Anthropic's own launch report** (not just OpenAI's competitor column).

Source precision is retained; chart rounding does not change ordering. Official views select the best captured run per source model identity, and disclose effort, agent, date and fallback information where available. This is not a controlled comparison with identical harnesses. In particular, HLE-Diamond's captured view is High effort, and historical boards identify their age rather than pretending to contain current models. AA Elo records are from one capture, not mixed release dates. Only AA-owned benchmarks are promoted using AA's results; its Terminal-Bench experiments are not substituted for the maintainer board.

## Every Kimi metric

| Metric | Report score | Official check / decision | Official ranking captured |
|---|---:|---|---|
| Terminal-Bench 4.0 | 65.7 | [not_listed](https://www.tbench.ai/) — Kimi 65.7 is a Claude Code self-report, absent from the maintainer snapshot. Official Sonnet Max 61.8, Opus Max 64.8, Astra Max 58.2. Do not rank the launch values 70.6 / 66.4 / 57.9 as official scores. | Yes |
| Terminal-Bench-Science 0.1 | 38.1 | [not_listed](https://www.terminal-bench-science.ai/) — Kimi 38.1 is self-reported. Official runs use three trials per task; keep effort/harness and SE with each run. | Yes |
| SWE-Marathon v1.1 | 51.7 | [not_listed](https://www.swe-marathon.org/) — v1.1 binary pass@1 only. Kimi launch 51.7 is not in the captured official board; do not substitute v1.0 or partial progress. | Yes |
| BenchCAD (1,000-case subset, no tools) | 72.8 | [republished_report](https://benchcad.com/news.html) — BenchCAD confirms 0.728 / 0.927 by citing Moonshot, not an independent run. ×100 gives 72.8 / 92.7 voxel IoU. Random 1,000 of 17,900 cases; full-set regrades and BenchCAD 2.0 Core are excluded. | No |
| BenchCAD (1,000-case subset, with tools) | 92.7 | [republished_report](https://benchcad.com/news.html) — BenchCAD confirms 0.728 / 0.927 by citing Moonshot, not an independent run. ×100 gives 72.8 / 92.7 voxel IoU. Random 1,000 of 17,900 cases; full-set regrades and BenchCAD 2.0 Core are excluded. | No |
| ProgramBench (Almost resolved, ≥95%) | 31.5 | [not_listed](https://programbench.com/) — 31.5 means Almost resolved: task score ≥95%. Official Almost column is used; Fully Resolved and raw average test score are different metrics. Claude Code vs mini-SWE-agent differs. | Yes |
| DeepSWE v1.1 | 75.5 | [not_listed](https://deepswe.datacurve.ai/) — Kimi uses Claude Code; official v1.1 board uses mini-swe-agent. DeepSeek card uses Mini-SWE-V2. Scores are different runs, not interchangeable. | Yes |
| PostTrainBench v1.2 (H20, DeepSeek judge) | 36.5 | [protocol_mismatch](https://posttrainbench.com/?version=v1.2) — Kimi uses H20 and a DeepSeek judge; official v1.2 uses H100 and GPT-5.6-Terra Xhigh. Official aggregates (Fable 44.65, Opus 43.80, Astra 41.88) are not comparable to this modified protocol. | No |
| Kimi Code Bench 2.0 (Internal) | 77.1 | [internal](https://www.kimi.com/en/blog/kimi-k3-1-pro) — Internal Moonshot evaluation; no independent official leaderboard. Keep as a report-only reference.  | No |
| Kimi Code Bench 3.0 Long-horizon (Internal) | 61.2 | [internal](https://www.kimi.com/en/blog/kimi-k3-1-pro) — Internal Moonshot evaluation; no independent official leaderboard. Keep as a report-only reference.  | No |
| Humanity's Last Exam (with tools) | 70.0 | [no_compatible_snapshot](https://lastexam.ai/) — Kimi reports full 2,500-question HLE with tools. The original official board is no-tools; the Diamond tools chart is a different 1,000-question set. | No |
| BrowseComp (200K compaction, 500 steps) | 92.1 | [no_compatible_snapshot](https://github.com/openai/simple-evals) — Official implementation found; no maintained leaderboard for the launch protocol (200K compaction, 500 steps, top-p 1.0). Keep 92.1 as self-report. | No |
| BioMysteryBench v11 | 80.6 | [protocol_mismatch](https://huggingface.co/datasets/Anthropic/BioMysteryBench-full) — v11 source dataset found. Kimi uses Kimi K3 as judge and Kimi Code; no independently verified official score under that judge was found. | No |
| CharXiv RQ (with Python) | 93.4 | [protocol_mismatch](https://charxiv.github.io/) — Official table is zero-shot RQ validation, not Python-assisted. Kimi 93.4 averages four runs; do not use descriptive Overall or no-tools scores as its core ranking. | No |
| MMMU-Pro (with Python) | 90.0 | [no_compatible_snapshot](https://mmmu-benchmark.github.io/) — MMMU-Pro, not MMMU validation/test. The board labels recent rows as model-author reports. Kimi 84.1 no-tools / 90.0 Python are absent; no independent matching protocol established. Four-run mean. | No |
| GDP.pdf (Python, macro rubric pass rate) | 85.7 | [protocol_mismatch](https://surgehq.ai/benchmarks/gdp-pdf) — 85.7 is mean rubric pass rate, macro-averaged over tasks with Python. Official strict all-pass leaderboard scores cannot be compared on this axis. | No |
| Chartography (with tools) | 90.2 | [protocol_mismatch](https://surgehq.ai/benchmarks/chartography) — The Surge leaderboard does not provide a matching Python-tools table. Its displayed Opus 66.3 is not the provider with-tools 89.0. Keep the Python report scores separate. | No |
| BabyVision (with tools) | 95.4 | [no_compatible_snapshot](https://www.unipat.ai/benchmarks/BabyVision) — Project site mixes tools and no-tools entries and does not identify who evaluated each row. Kimi K3.1 Pro and the two DeepSeek rows are absent; independent provenance is not established. | No |
| ZeroBench-main (Python, pass@5) | 63.0 | [protocol_mismatch](https://zerobench.github.io/) — 63.0 is Python pass@5. The project separates official no-tools runs from external tool reports; external entries must remain dashed. | No |
| Agents' Last Exam v1.1 (ALL) | 43.2 | [protocol_mismatch](https://agents-last-exam.org/leaderboard) — v1.1 ALL has 122 tasks; CLI has 86. Official API exposes both binary passRate and partial avgScore. Kimi footnote does not unambiguously name which statistic 43.2 / 44.2 uses; no inferred mapping or ranking. Kimi additionally zeros requirement-bypass runs. | No |
| Agents' Last Exam v1.1 (CLI) | 44.2 | [protocol_mismatch](https://agents-last-exam.org/leaderboard) — v1.1 ALL has 122 tasks; CLI has 86. Official API exposes both binary passRate and partial avgScore. Kimi footnote does not unambiguously name which statistic 43.2 / 44.2 uses; no inferred mapping or ranking. Kimi additionally zeros requirement-bypass runs. | No |
| AutomationBench-AA | 73.3 | [official_match](https://artificialanalysis.ai/models/kimi-k3-1-pro) — AA directly reports 0.7329771090921112 partial score = 73.3%. This is AutomationBench-AA, not Zapier AutomationBench v1.0.6 pass rate. | Yes |
| GDPval-AA v2.1 | 1846 | [official_match](https://artificialanalysis.ai/models/kimi-k3-1-pro) — AA directly reports Kimi 1845.72 Elo, displayed 1846. The launch-date Opus 1846 and Sonnet 1840 are older snapshots; official same-day values are ranked separately. | Yes |
| AA-Briefcase v1.1 | 1678 | [official_match](https://artificialanalysis.ai/models/kimi-k3-1-pro) — AA directly reports Kimi 1677.79 Elo, displayed 1678. Do not mix October 7 provider snapshots with the current AA Elo ranking. | Yes |
| APEX-Agents | 67.2 | [protocol_mismatch](https://www.mercor.com/apex/apex-agents-leaderboard/) — Kimi cites Mercor but does not specify version or Mean Score versus Pass@1. Current official page separates them. Hold 67.2 as a reported reference pending metric confirmation. | No |
| OfficeQA Pro v2 | 64.4 | [not_listed](https://github.com/databricks/officeqa) — OfficeQA Pro has 133 questions / 697 Treasury PDFs; Pro v2 has 90 / 1,435 Receipts PDFs. Kimi uses rendered images without extracted text and zeros online-answer retrieval. No official Kimi K3.1 Pro result found; oracle-page and Genie/preparsed setups excluded. | No |
| OfficeQA Pro | 67.4 | [not_listed](https://github.com/databricks/officeqa) — OfficeQA Pro has 133 questions / 697 Treasury PDFs; Pro v2 has 90 / 1,435 Receipts PDFs. Kimi uses rendered images without extracted text and zeros online-answer retrieval. No official Kimi K3.1 Pro result found; oracle-page and Genie/preparsed setups excluded. | No |
| Frontier Finance (finance agent v2) | 58.6 | [not_listed](https://samaya.ai/benchmarks/frontier-finance) — Kimi 58.6 uses Finance Agent v2 at Max. Official page updated September 28 separates Finance Agent v2, web-only and proprietary Samaya. No Kimi K3.1 Pro result; do not mix the three harnesses. | No |
| Harvey Legal Agent (public, all-pass) | 23.7 | [protocol_mismatch](https://www.harvey.ai/blog/legal-agent-benchmark-initial-results) — Kimi uses 1,251 public tasks, Stirrup, strict all-pass. Harvey initial results use an evaluation set mirroring LAB distribution; not established to be those same public tasks. No comparable official Kimi row. | No |
| HANDBOOK.md v1 | 44.6 | [protocol_mismatch](https://surgehq.ai/benchmarks/handbook) — Kimi uses early open v1 tasks and OpenHands. Current Surge board has Opus 52.3, Sonnet 47.7, Astra 31.4, but no Kimi K3.1 Pro; equivalence with the early public task version is not established. | No |
| OSWorld v2.1 (Kimi Agent) | 79.6 | [protocol_mismatch](https://osworld-v2.xlang.ai/) — Official JSON separates release version, full/offline subset, binaryAccuracy and partialScore. Kimi 79.6 does not identify score type or subset; do not infer or combine it with either official metric. | No |
| Business Operation (Internal) | 37.8 | [internal](https://www.kimi.com/en/blog/kimi-k3-1-pro) — Internal Moonshot evaluation; no independent official leaderboard. Keep as a report-only reference. Table says 37.8, narrative graphic says 37; unit unspecified, not a percentage. | No |
| DECK-Arena (Internal, Elo) | 1456 | [internal](https://www.kimi.com/en/blog/kimi-k3-1-pro) — Internal Moonshot evaluation; no independent official leaderboard. Keep as a report-only reference. Internal Elo; cannot mix with other Elo populations. | No |
| Design Bench (Internal, Elo) | 957 | [internal](https://www.kimi.com/en/blog/kimi-k3-1-pro) — Internal Moonshot evaluation; no independent official leaderboard. Keep as a report-only reference. Internal Elo; cannot mix with other Elo populations. | No |
| Kimi Hallu Bench Hard (with tools, claim error rate) | 8.3 | [internal](https://www.kimi.com/en/blog/kimi-k3-1-pro) — Internal Moonshot evaluation; no independent official leaderboard. Keep as a report-only reference. Claim hallucination rate; lower is better. | No |
| GDP.pdf (no tools, strict pass rate) | 34.6 | [protocol_mismatch](https://surgehq.ai/benchmarks/gdp-pdf) — 34.6 is the no-tools strict pass rate among fully scored responses, with 1152px page images plus Docling text and five runs. Official input/failure-denominator equivalence is not established; no core ranking for this exact protocol. | No |
| Humanity's Last Exam (no tools) | 51.1 | [not_listed](https://lastexam.ai/) — Full 2,500-question HLE. DeepSeek 42.6 / 36.8 are full-set figures; 44.0 / 39.1 are text-only and excluded. The historical official board has no current-model entries. | Yes |
| HLE-Diamond (full, no tools) | 39.4 | [not_listed](https://lastexam.ai/blog/hle-diamond) — Full 1,000 questions, not text-only; Kimi 39.4 Max versus the official default High view. No Kimi K3.1 Pro entry in the captured view. | Yes |
| GPQA Diamond (Kimi launch protocol) | 94.2 | [no_compatible_snapshot](https://github.com/idavidrein/gpqa) — Official dataset/evaluation code located; no maintained current-model leaderboard for the launch sampling protocol. 94.2 is a provider report, not official independent verification. | No |
| CharXiv RQ (no tools) | 89.0 | [not_listed](https://charxiv.github.io/) — 89.0 is no-tools reasoning-question accuracy, averaged over four runs. Official CSV first Overall column is RQ; the second is descriptive. No Kimi K3.1 Pro row. | Yes |
| MMMU-Pro (no tools, Kimi launch protocol) | 84.1 | [no_compatible_snapshot](https://mmmu-benchmark.github.io/) — MMMU-Pro, not MMMU validation/test. The board labels recent rows as model-author reports. Kimi 84.1 no-tools / 90.0 Python are absent; no independent matching protocol established. Four-run mean. | No |
| ZeroBench-main (no tools) (avg@5) | 29.8 | [protocol_mismatch](https://zerobench.github.io/) — 29.8 is average over five no-tools samples. Do not rename this to official pass@1 without confirming sampling and grading equivalence; pass@5 is separately 39.0. | No |
| ZeroBench-main (no tools) (pass@5) | 39.0 | [not_listed](https://zerobench.github.io/) — 39.0 is no-tools pass@5, distinct from avg@5 29.8 and Python pass@5 63.0. Only the official table enters core ranking; Kimi K3.1 Pro is absent. | Yes |
| PerceptionBench | 68.3 | [republished_report](https://www.kimi.com/blog/perception-bench) — Moonshot is also the benchmark author. Its original 16-model study and the K3.1 release are different snapshots; 68.3 has no independent validation. Retain as provider report. | No |
| Kimi Hallu Bench (no tools, claim error rate) | 5.4 | [internal](https://www.kimi.com/en/blog/kimi-k3-1-pro) — Internal Moonshot evaluation; no independent official leaderboard. Keep as a report-only reference. Claim hallucination rate; lower is better. | No |
| ExploitBench (pass@5 max capability) | 74.7 | [protocol_mismatch](https://exploitbench.ai/) — Kimi 74.7 is best-of-five mean capability coverage, 300 turns, 16 flags. Official all-runs view mixes seeds/turn budgets and differs from control. No matching Kimi run; do not read this as full exploitation success rate. | No |
| ExploitGym (6-hour budget) | 20.7 | [protocol_mismatch](https://www.cybergym.io/exploitgym/) — Official board reports intended-vulnerability exploit counts over 869 tasks, with separate mitigation/domain/budget settings and some provider submissions. Kimi 20.7 does not identify denominator or mitigation setting; no inferred comparison. | No |
| xdev-bench-hard (Internal, pass@3) | 81.0 | [internal](https://www.kimi.com/en/blog/kimi-k3-1-pro) — Internal Moonshot evaluation; no independent official leaderboard. Keep as a report-only reference. Final post-filtering checkpoint, pass@3; not a general pass@1 score. | No |

## Comparison-table exceptions

Five numeric cells remain visible as annotated source entries outside the comparison bars: GLM’s HLE and HLE-Diamond scores are text-only; Science’s DeepSeek 15.7 belongs to the older Flash model; ExploitBench and ExploitGym label Fable in the table but cite Mythos in the footnotes. No identity or protocol equivalence is assumed. The 36 missing cells are displayed as dashes.

## Every report record already displayed in the affected charts

Provider report dates and run configurations are retained. Later reports can restate older models from the same provider. Reprinted AA scores stay reports until independently matched to AA.

| Metric | Model | Score | Report date / source |
|---|---|---:|---|
| Terminal-Bench 4.0 | Claude Sonnet 5.5 | 70.6 | [2026-09-28](https://www.anthropic.com/claude-sonnet-5-5) |
| Terminal-Bench 4.0 | Claude Opus 5.5 | 66.4 | [2026-09-22](https://www.anthropic.com/claude-opus-5-5) |
| Terminal-Bench 4.0 | Kimi K3.1 Pro | 65.7 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Terminal-Bench 4.0 | GPT-6 Astra | 57.9 | [2026-09-03](https://openai.com/index/gpt-6-astra/) |
| Terminal-Bench 4.0 | Claude Fable 5.1 | 55.8 | [2026-09-01](https://www.anthropic.com/claude-fable-and-mythos-5-1) |
| Terminal-Bench 4.0 | DeepSeek-V4.1-Flash-1017 | 42.3 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| Terminal-Bench 4.0 | Claude Haiku 5.5 | 39.2 | [2026-10-07](https://www.anthropic.com/claude-haiku-5-5) |
| Terminal-Bench 4.0 | DeepSeek-V4.1-Flash | 31.2 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| Terminal-Bench-Science 0.1 | Claude Opus 5.5 | 58.7 | [2026-09-22](https://www.anthropic.com/claude-opus-5-5) |
| Terminal-Bench-Science 0.1 | Kimi K3.1 Pro | 38.1 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| SWE-Marathon v1.1 | Kimi K3.1 Pro | 51.7 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| BenchCAD (1,000-case subset, no tools) | Kimi K3.1 Pro | 72.8 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| BenchCAD (1,000-case subset, with tools) | Kimi K3.1 Pro | 92.7 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| ProgramBench (Almost resolved, ≥95%) | Kimi K3.1 Pro | 31.5 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| DeepSWE v1.1 | DeepSeek-V4.1-Flash-1017 | 77 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| DeepSWE v1.1 | Kimi K3.1 Pro | 75.5 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| DeepSWE v1.1 | DeepSeek-V4.1-Flash | 74.2 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| DeepSWE v1.1 | GPT-6 Sol | 68.8 | [2026-09-22](https://openai.com/index/introducing-gpt-6-sol-and-luna/) |
| DeepSWE v1.1 | GPT-6 Luna | 66.6 | [2026-09-22](https://openai.com/index/introducing-gpt-6-sol-and-luna/) |
| PostTrainBench v1.2 (H20, DeepSeek judge) | Kimi K3.1 Pro | 36.5 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Kimi Code Bench 2.0 (Internal) | Kimi K3.1 Pro | 77.1 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Kimi Code Bench 3.0 Long-horizon (Internal) | Kimi K3.1 Pro | 61.2 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Humanity's Last Exam (with tools) | Kimi K3.1 Pro | 70 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Humanity's Last Exam (with tools) | Claude Opus 5.5 | 67.7 | [2026-09-22](https://www.anthropic.com/claude-opus-5-5) |
| Humanity's Last Exam (with tools) | Claude Sonnet 5.5 | 64.5 | [2026-09-28](https://www.anthropic.com/claude-sonnet-5-5) |
| Humanity's Last Exam (with tools) | Claude Haiku 5.5 | 57.4 | [2026-10-07](https://www.anthropic.com/claude-haiku-5-5) |
| BrowseComp (200K compaction, 500 steps) | Kimi K3.1 Pro | 92.1 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| BioMysteryBench v11 | Kimi K3.1 Pro | 80.6 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| CharXiv RQ (with Python) | Kimi K3.1 Pro | 93.4 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| MMMU-Pro (with Python) | Kimi K3.1 Pro | 90 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| GDP.pdf (Python, macro rubric pass rate) | Kimi K3.1 Pro | 85.7 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Chartography (with tools) | Kimi K3.1 Pro | 90.2 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Chartography (with tools) | Claude Opus 5.5 | 89 | [2026-09-22](https://www.anthropic.com/claude-opus-5-5) |
| Chartography (with tools) | DeepSeek-V4.1-Flash-1017 | 83 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| Chartography (with tools) | DeepSeek-V4.1-Flash | 78.9 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| BabyVision (with tools) | Kimi K3.1 Pro | 95.4 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| BabyVision (with tools) | DeepSeek-V4.1-Flash-1017 | 92.5 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| BabyVision (with tools) | DeepSeek-V4.1-Flash | 89.6 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| ZeroBench-main (Python, pass@5) | Kimi K3.1 Pro | 63 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Agents' Last Exam v1.1 (ALL) | Kimi K3.1 Pro | 43.2 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Agents' Last Exam v1.1 (CLI) | Kimi K3.1 Pro | 44.2 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| AutomationBench-AA | Kimi K3.1 Pro | 73.3 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| GDPval-AA v2.1 | Claude Opus 5.5 | 1846 | [2026-09-22](https://www.anthropic.com/claude-opus-5-5) |
| GDPval-AA v2.1 | Kimi K3.1 Pro | 1846 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| GDPval-AA v2.1 | Claude Sonnet 5.5 | 1840 | [2026-10-07](https://www.anthropic.com/claude-haiku-5-5) |
| GDPval-AA v2.1 | Claude Haiku 5.5 | 1620 | [2026-10-07](https://www.anthropic.com/claude-haiku-5-5) |
| AA-Briefcase v1.1 | Claude Sonnet 5.5 | 1824 | [2026-10-07](https://www.anthropic.com/claude-haiku-5-5) |
| AA-Briefcase v1.1 | Kimi K3.1 Pro | 1678 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| AA-Briefcase v1.1 | Claude Haiku 5.5 | 1578 | [2026-10-07](https://www.anthropic.com/claude-haiku-5-5) |
| APEX-Agents | Kimi K3.1 Pro | 67.2 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| OfficeQA Pro v2 | Kimi K3.1 Pro | 64.4 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| OfficeQA Pro | Kimi K3.1 Pro | 67.4 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Frontier Finance (finance agent v2) | Kimi K3.1 Pro | 58.6 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Harvey Legal Agent (public, all-pass) | Kimi K3.1 Pro | 23.7 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| HANDBOOK.md v1 | Kimi K3.1 Pro | 44.6 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| OSWorld v2.1 (Kimi Agent) | Kimi K3.1 Pro | 79.6 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Business Operation (Internal) | Kimi K3.1 Pro | 37.8 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| DECK-Arena (Internal, Elo) | Kimi K3.1 Pro | 1456 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Design Bench (Internal, Elo) | Kimi K3.1 Pro | 957 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Kimi Hallu Bench Hard (with tools, claim error rate) | Kimi K3.1 Pro | 8.3 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| GDP.pdf (no tools, strict pass rate) | Kimi K3.1 Pro | 34.6 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Humanity's Last Exam (no tools) | Claude Sonnet 5.5 | 56.9 | [2026-10-07](https://www.anthropic.com/claude-haiku-5-5) |
| Humanity's Last Exam (no tools) | Kimi K3.1 Pro | 51.1 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Humanity's Last Exam (no tools) | Claude Haiku 5.5 | 45.9 | [2026-10-07](https://www.anthropic.com/claude-haiku-5-5) |
| Humanity's Last Exam (no tools) | DeepSeek-V4.1-Flash-1017 | 42.6 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| Humanity's Last Exam (no tools) | DeepSeek-V4.1-Flash | 36.8 | [2026-10-17](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) |
| HLE-Diamond (full, no tools) | Kimi K3.1 Pro | 39.4 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| GPQA Diamond (Kimi launch protocol) | Kimi K3.1 Pro | 94.2 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| CharXiv RQ (no tools) | Kimi K3.1 Pro | 89 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| MMMU-Pro (no tools, Kimi launch protocol) | Kimi K3.1 Pro | 84.1 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| ZeroBench-main (no tools) (avg@5) | Kimi K3.1 Pro | 29.8 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| ZeroBench-main (no tools) (pass@5) | Kimi K3.1 Pro | 39 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| PerceptionBench | Kimi K3.1 Pro | 68.3 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| Kimi Hallu Bench (no tools, claim error rate) | Kimi K3.1 Pro | 5.4 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| ExploitBench (pass@5 max capability) | Kimi K3.1 Pro | 74.7 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| ExploitGym (6-hour budget) | Kimi K3.1 Pro | 20.7 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |
| xdev-bench-hard (Internal, pass@3) | Kimi K3.1 Pro | 81 | [2026-10-24](https://www.kimi.com/en/blog/kimi-k3-1-pro) |

## Captured official sources

| Metric | Raw runs | Captured | Source updated | Source |
|---|---:|---|---|---|
| Terminal-Bench 4.0 | 35 | 2026-10-24 | 2026-10-23 | [Official](https://www.tbench.ai/) |
| Terminal-Bench-Science 0.1 | 17 | 2026-10-24 | 2026-09-23 | [Official](https://www.terminal-bench-science.ai/) |
| ProgramBench (Almost resolved, ≥95%) | 30 | 2026-10-24 | Not stated | [Official](https://programbench.com/) |
| ZeroBench-main (no tools) (pass@5) | 73 | 2026-10-24 | Not stated | [Official](https://zerobench.github.io/) |
| GDPval-AA v2.1 | 170 | 2026-10-24 | Not stated | [Official](https://artificialanalysis.ai/models/kimi-k3-1-pro) |
| AA-Briefcase v1.1 | 138 | 2026-10-24 | Not stated | [Official](https://artificialanalysis.ai/models/kimi-k3-1-pro) |
| AutomationBench-AA | 135 | 2026-10-24 | Not stated | [Official](https://artificialanalysis.ai/models/kimi-k3-1-pro) |
| DeepSWE v1.1 | 21 | 2026-10-24 | 2026-09-22 | [Official](https://deepswe.datacurve.ai/) |
| Humanity's Last Exam (no tools) | 9 | 2026-10-24 | Not stated | [Official](https://lastexam.ai/) |
| HLE-Diamond (full, no tools) | 8 | 2026-10-24 | Not stated | [Official](https://lastexam.ai/blog/hle-diamond) |
| CharXiv RQ (no tools) | 95 | 2026-10-24 | Not stated | [Official](https://charxiv.github.io/) |
| SWE-Marathon v1.1 | 17 | 2026-10-24 | Not stated | [Official](https://www.swe-marathon.org/) |

## Implementation and reproduction

- `data/model_eval_updates.json` stores immutable report snapshots, per-model receipts, per-metric eligibility decisions and captured official runs separately.
- `pipeline/update_model_evals.py` rejects core snapshots without an audit, source/date, explicit evaluation provenance, finite values and recorded configuration. No provider record is overwritten by a leaderboard run.
- `web/model-evals/ranking.js` never uses report values to select or sort official ranks. Comparison tables are stored separately from self-report observations. Missing scores stay missing; incompatible or identity-conflicted columns are listed outside the plot. Reports without an exact matching audit receipt are explicitly unverified historical imports.
- `make update-model-evals` rebuilds the embedded data. Run the pipeline tests and static build; browser-check solid versus dashed plots, report-only metrics and source details.
- The source bodies are retained locally under ignored `outputs/kimi-k3-1-pro/`; checked numerical excerpts and decisions are committed in the overlay and this audit. A source retrieval failure is not treated as a missing score. Web-readable sources were used when direct HTTP returned 403.
- No Highspeed evaluation is invented, and no new Library entity is created for internal or unresolved metrics.

## All cells in the selected Moonshot comparison table

These are attributed to Moonshot’s October 24 report. They are not substituted for the respective providers’ own cards or for official leaderboard runs. A dash means the report supplies no number.

| Metric | Kimi | Fable | Astra | Opus | DeepSeek 1017 | GLM |
|---|---:|---:|---:|---:|---:|---:|
| Terminal-Bench 4.0 | 65.7 | 57.9 | 58.2 | 66.4 | 42.3 | 41.8 |
| Terminal-Bench-Science 0.1 | 38.1 | 40.0 | 68.1 | 63.3 | 15.7 | 8.1 |
| SWE-Marathon v1.1 | 51.7 | 45.6 | 42.5 | 46.3 | 40.0 | 42.5 |
| BenchCAD (1,000-case subset, no tools) | 72.8 | 60.6 | — | 73.0 | 41.2 | — |
| BenchCAD (1,000-case subset, with tools) | 92.7 | 92.6 | 95.9 | 96.2 | 81.6 | — |
| ProgramBench (Almost resolved, ≥95%) | 31.5 | 53.5 | 50.0 | 65.0 | 29.1 | 19.0 |
| DeepSWE v1.1 | 75.5 | 67.4 | 74.1 | 74.2 | 77.0 | 66.9 |
| PostTrainBench v1.2 (H20, DeepSeek judge) | 36.5 | 44.6 | 41.9 | 43.8 | 30.5 | 34.5 |
| Kimi Code Bench 2.0 (Internal) | 77.1 | — | — | — | 76.1 | 61.7 |
| Kimi Code Bench 3.0 Long-horizon (Internal) | 61.2 | 58.8 | 66.5 | 58.5 | 51.5 | 45.5 |
| Humanity's Last Exam (with tools) | 70.0 | 65.6 | 57.2 | 67.7 | 58.8 | 62.5 |
| BrowseComp (200K compaction, 500 steps) | 92.1 | — | 91.5 | 90.8 | — | — |
| BioMysteryBench v11 | 80.6 | 81.6 | 78.9 | 81.9 | 80.0 | 79.6 |
| CharXiv RQ (with Python) | 93.4 | 92.7 | 92.8 | 93.8 | 85.6 | — |
| MMMU-Pro (with Python) | 90.0 | 88.4 | 87.8 | 89.8 | 82.5 | — |
| GDP.pdf (Python, macro rubric pass rate) | 85.7 | 83.8 | 85.5 | 83.9 | 73.0 | — |
| Chartography (with tools) | 90.2 | 88.4 | 91.0 | 89.0 | 83.0 | — |
| BabyVision (with tools) | 95.4 | 95.1 | 96.6 | 97.7 | 92.5 | — |
| ZeroBench-main (Python, pass@5) | 63.0 | 59.0 | 58.0 | 61.0 | 51.0 | — |
| Agents' Last Exam v1.1 (ALL) | 43.2 | — | 41.8 | 42.6 | 37.7 | 26.2 |
| Agents' Last Exam v1.1 (CLI) | 44.2 | — | 44.2 | 40.7 | 36.0 | 29.4 |
| AutomationBench-AA | 73.3 | 59.4 | 68.5 | 69.5 | 66.6 | 62.2 |
| GDPval-AA v2.1 | 1846 | 1754 | 1573 | 1866 | 1746 | 1650 |
| AA-Briefcase v1.1 | 1678 | 1672 | 1569 | 1803 | 1570 | 1507 |
| APEX-Agents | 67.2 | 68.6 | 64.7 | 73.5 | 63.4 | 56.6 |
| OfficeQA Pro v2 | 64.4 | 54.5 | 54.4 | 62.2 | 40.4 | 31.1 |
| OfficeQA Pro | 67.4 | 68.6 | 66.2 | — | 62.4 | 58.6 |
| Frontier Finance (finance agent v2) | 58.6 | 60.8 | 45.0 | 56.7 | 54.5 | 57.5 |
| Harvey Legal Agent (public, all-pass) | 23.7 | 19.1 | — | — | 21.0 | — |
| HANDBOOK.md v1 | 44.6 | 38.8 | — | 41.5 | 28.9 | 20.8 |
| OSWorld v2.1 (Kimi Agent) | 79.6 | 80.7 | 75.8 | 81.8 | 69.3 | — |
| Business Operation (Internal) | 37.8 | 30.7 | 32.3 | — | 8.9 | 18.6 |
| DECK-Arena (Internal, Elo) | 1456 | — | 1423 | 1253 | 1231 | 1119 |
| Design Bench (Internal, Elo) | 957 | — | 1076 | 927 | 863 | 718 |
| Kimi Hallu Bench Hard (with tools, claim error rate) | 8.3 | 23.3 | 5.5 | 15.0 | 23.3 | 22.6 |
| GDP.pdf (no tools, strict pass rate) | 34.6 | 27.6 | 34.2 | 30.6 | 17.2 | 11.2 |
| Humanity's Last Exam (no tools) | 51.1 | 57.6 | 53.6 | 59.8 | 42.6 | 43.0* |
| HLE-Diamond (full, no tools) | 39.4 | 55.1 | 65.8 | 60.9 | 21.6 | 25.1* |
| GPQA Diamond (Kimi launch protocol) | 94.2 | 93.7 | 96.1 | 93.9 | 92.2 | 91.7 |
| CharXiv RQ (no tools) | 89.0 | 88.8 | 90.0 | 92.1 | 77.0 | — |
| MMMU-Pro (no tools, Kimi launch protocol) | 84.1 | 86.3 | 86.9 | 87.7 | 80.6 | — |
| ZeroBench-main (no tools) (avg@5) | 29.8 | 23.0 | 43.2 | 35.0 | 11.8 | — |
| ZeroBench-main (no tools) (pass@5) | 39.0 | 35.0 | 52.0 | 43.0 | 23.0 | — |
| PerceptionBench | 68.3 | 63.0 | 77.6 | 72.1 | 47.7 | — |
| Kimi Hallu Bench (no tools, claim error rate) | 5.4 | 11.4 | 4.2 | 6.8 | 13.1 | 14.8 |
| ExploitBench (pass@5 max capability) | 74.7 | 83.0 | 100 | 91.0 | — | 54.4 |
| ExploitGym (6-hour budget) | 20.7 | 30.4 | 42.4 | 34.5 | — | 15.0 |
| xdev-bench-hard (Internal, pass@3) | 81.0 | — | — | — | 85.7 | 57.1 |

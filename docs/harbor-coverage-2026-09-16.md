# Harbor adapter coverage review — 2026-09-16

Scope: the current 85 adapter directories in [harbor-framework/harbor](https://github.com/harbor-framework/harbor/tree/main/adapters), not a reconstruction of the paper’s publication-time inventory.

The Library had 2,924 entries before this review. Normalized adapter names matched 65 directories to existing entries. Manual source review mapped four more to existing entries and identified 16 missing benchmark or variant entries. The Library now contains 2,940 entries. The 65 name matches are provisional identity matches, not an independent validation of every adapter.

## Added entries

| Benchmark | Original source | Harbor adapter |
| --- | --- | --- |
| CooperBench | [Repository](https://github.com/cooperbench/CooperBench) | [cooperbench](https://github.com/harbor-framework/harbor/tree/main/adapters/cooperbench) |
| CRMArena | [Repository](https://github.com/SalesforceAIResearch/CRMArena) | [crmarena](https://github.com/harbor-framework/harbor/tree/main/adapters/crmarena) |
| DA-Code | [Repository](https://github.com/yiyihum/da-code) | [dacode](https://github.com/harbor-framework/harbor/tree/main/adapters/dacode) |
| DeepSynth | [Repository](https://github.com/agentdeepsynthesis/deepsynth-bench) | [deepsynth](https://github.com/harbor-framework/harbor/tree/main/adapters/deepsynth) |
| FeatBench | [Repository](https://github.com/TsinghuaISE/FeatBench) | [featbench](https://github.com/harbor-framework/harbor/tree/main/adapters/featbench) |
| GSO | [Repository](https://github.com/gso-bench/gso) | [gso](https://github.com/harbor-framework/harbor/tree/main/adapters/gso) |
| KramaBench | [Repository](https://github.com/mitdbg/Kramabench) | [kramabench](https://github.com/harbor-framework/harbor/tree/main/adapters/kramabench) |
| LLM-SRBench | [Repository](https://github.com/deep-symbolic-mathematics/llm-srbench) | [llmsr_bench](https://github.com/harbor-framework/harbor/tree/main/adapters/llmsr_bench) |
| LoCoMo | [Repository](https://github.com/snap-research/locomo) | [locomo](https://github.com/harbor-framework/harbor/tree/main/adapters/locomo) |
| ML-Dev-Bench | [Repository](https://github.com/ml-dev-bench/ml-dev-bench) | [ml_dev_bench](https://github.com/harbor-framework/harbor/tree/main/adapters/ml_dev_bench) |
| FinBen | [Repository](https://github.com/The-FinAI/FinBen) | [pixiu](https://github.com/harbor-framework/harbor/tree/main/adapters/pixiu) |
| ResearchCodeBench | [Repository](https://github.com/PatrickHua/ResearchCodeBench) | [research-code-bench](https://github.com/harbor-framework/harbor/tree/main/adapters/research-code-bench) |
| Spider2-DBT | [Repository](https://github.com/xlang-ai/Spider2) | [spider2-dbt](https://github.com/harbor-framework/harbor/tree/main/adapters/spider2-dbt) |
| SpreadsheetBench Verified | [Repository](https://github.com/RUCKBReasoning/SpreadsheetBench) | [spreadsheetbench-verified](https://github.com/harbor-framework/harbor/tree/main/adapters/spreadsheetbench-verified) |
| SWE-Gym | [Repository](https://github.com/SWE-Gym/SWE-Gym) | [swegym](https://github.com/harbor-framework/harbor/tree/main/adapters/swegym) |
| TextArena | [Repository](https://github.com/LeonGuertler/TextArena) | [textarena](https://github.com/harbor-framework/harbor/tree/main/adapters/textarena) |

## Existing entries mapped manually

- `bird_bench` → BIRD-SQL.
- `frontier-cs-algorithm` → FrontierCS; its existing description is specifically the 172-problem algorithmic track.
- `kumo` → kumo-1 and existing difficulty-specific entries.
- `reasoning-gym` → reasoning-gym-easy / reasoning-gym-hard.

## Identity and availability boundaries

- LoCoMo is distinct from LOCOMO-CONV; FeatBench from FeatureBench; FinBen from FinBench; GSO from GSO-Net.
- Spider2-DBT is a separate track from the existing Spider 2.0-Lite entry.
- SpreadsheetBench Verified is the 400-task verified subset, not the original 912-task benchmark. It is represented as a variant with its 2025 release year, not the original paper’s 2024 date.
- The PIXIU adapter is recorded as a source for FinBen; this does not identify every PIXIU framework asset with FinBen.
- Harbor adaptations can cover only a subset of the original benchmark. No claim is made that the entire original dataset is executable with Harbor.
- Original repository documentation and adapter documentation informed descriptions. ResearchCodeBench has no established release date in this review, so the date remains unknown.
- This update adds metadata and source links. No benchmark datasets were downloaded and no Harbor executions were performed. Some datasets require separate access or setup.

The machine-readable [audit](../data/harbor_coverage_audit.json) records adapter tree SHAs, record IDs, and mapping status.

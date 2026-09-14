# 分类全库审查

审查 2855 条记录；1093 条的类别成员关系发生变化。

这是全库元数据与分类逻辑审查，不代表已逐篇阅读全文。自动规则的证据和待复核标记保存在 records.jsonl。

无受支持分类：1321 → 877。未分类记录仍可搜索，不强制分入某类。

## 整体诊断与修正

- **维度混杂**：研究主题与任务能力分开，仍支持多标签；AI Scientist / AI R&D 作为证据细分，分别搜索到科学研究/自我改进主题。
- **前后端不一致**：移除浏览器临时合并；数据生成、页面、搜索别名、旧链接、README 使用同一份分类。
- **证据来源错误**：不再继承旧 `area`，避免 SciExplore 因错误粗标签归入 Embodied AI。
- **词边界错误**：统一限定词边界并补足词形，不再从 meteorological reasoning 推出 logical reasoning。
- **任务覆盖缺口**：补齐科学计算/实验/数据任务的证据规则，连接软件工程、数据分析等缺失能力入口。
- **目标与手段混淆**：模型训练、算法、数据与计算优化支持自我改进主题，但不统一宣称为闭环 RSI；会自动更新的测试集本身不属于模型自我改进。
- **不确定性被隐藏**：保留未分类及来源标签待复核队列，所有记录仍能搜索。

代表性修正：NatureBench / AtmosCoder-Bench → science + coding；GENEB → science + data analysis；AgentHPOBench → self-improvement theme + AI R&D facet（非已证实 RSI）；SWE-rebench 不因 Nebius AI R&D 机构名进入主题；AIR-BENCH 的 self-evolving 指评测集，不指模型。

本次重点复核了主题变更与能力类别删除中的任务边界，并以正反案例做回归验证；整库覆盖通过确定性规则扫描、计数核对和逐记录证据检查完成。仍有来源标签或简略描述需要后续查原文，不能将这份报告当成全库逐篇精读认证。

## 类别计数（只计公开可见记录）

| 类别 | 旧值 | 新值 |
|---|---:|---:|
| Self-Improvement & RSI | 14 | 22 |
| AI for Science | 66 | 143 |
| Coding Agents | 82 | 94 |
| Computer Use | 44 | 43 |
| GUI Grounding | 5 | 5 |
| Tool Use | 99 | 99 |
| Agent Memory | 15 | 20 |
| Multi-Agent | 15 | 15 |
| Deep Research | 15 | 17 |
| RAG & Retrieval | 20 | 21 |
| Long Context | 62 | 60 |
| Logical Reasoning | 19 | 15 |
| Causal Reasoning | 40 | 37 |
| Mathematical Reasoning | 137 | 137 |
| Instruction Following | 47 | 47 |
| Multilingual NLP | 94 | 99 |
| Vision-Language Models | 497 | 540 |
| Video Understanding | 180 | 180 |
| Audio & Speech | 88 | 87 |
| Embodied AI | 117 | 121 |
| Safety & Alignment | 262 | 277 |
| Knowledge & QA | 新增 | 246 |
| Software Engineering | 新增 | 258 |
| Data Analysis | 新增 | 63 |
| Systems Optimization | 新增 | 13 |
| Cybersecurity | 新增 | 63 |
| Visual Understanding | 新增 | 242 |
| Spatial Reasoning | 新增 | 99 |
| Content Generation | 新增 | 64 |

## 主题变更逐项证据

### AgentHPOBench

新增：self-improvement-rsi；移除：ai-r-d。

AgentHPOBench evaluates LLM agents as sequential hyperparameter optimizers across 30 executable ML tasks. Agents observe accumulated configurations, metrics, and logs, then propose the next configuration. Scoring compares agents and conventional HPO baselines under a unified protocol.

[来源](https://arxiv.org/abs/2607.29626)

### AI2D

新增：ai-for-science, knowledge-qa, visual-understanding；移除：无。

Diagram question answering (science-textbook diagrams).

[来源](https://llm-stats.com/benchmarks/ai2d)

### AI2D_TEST

新增：ai-for-science, knowledge-qa, visual-understanding；移除：无。

A diagram understanding benchmark focused on scientific and educational visual question answering.

[来源](https://qwen.ai/blog?id=qwen3.6)

### ALD/E-ImageMiner

新增：ai-for-science, knowledge-qa, visual-understanding；移除：无。

ALD/E-ImageMiner is a benchmark of 1,951 scientific figures from 205 publications, expert-annotated for classification, table extraction, summarization, and visual question answering.

[来源](https://arxiv.org/abs/2608.14075)

### APS-Bench

新增：ai-for-science；移除：无。

APS-Bench is a 50-question QA dataset with auditable gold answers for evaluating retrieval-augmented generation over scientific facility operations knowledge.

[来源](https://arxiv.org/abs/2607.24663)

### ARC-C

新增：ai-for-science, knowledge-qa；移除：无。

The AI2 Reasoning Challenge (ARC) Challenge Set is a multiple-choice question-answering benchmark containing grade-school level science questions that require advanced reasoning capabilities. ARC-C specifically contains questions that were answered incorrectly by both retrieval-based and word co-occurrence algorithms, making it a particularly challenging subset designed to test commonsense reasoning abilities in AI systems.

[来源](https://llm-stats.com/benchmarks/arc-c)

### ARC-Challenge

新增：ai-for-science；移除：无。

Grade-school science questions, challenge split.

[来源](https://modelbeats.com/benchmarks/arc-challenge)

### ARC-Easy

新增：ai-for-science；移除：无。

Grade-school science questions, easy split.

[来源](https://modelbeats.com/benchmarks/arc-easy)

### ArchEGraph

新增：ai-for-science, data-analysis；移除：无。

ArchEGraph evaluates geometry-topology-physics aligned building energy modeling through graph reconstruction and topology-informed load prediction tasks, with standardized protocols and generalization experiments.

[来源](https://arxiv.org/abs/2608.06772)

### AtmosCoder-Bench

新增：ai-for-science, software-engineering；移除：无。

AtmosCoder-Bench is an execution-grounded benchmark for LLMs on atmospheric science computation, with 436 problems and 3,910 variants, grading by executing code solutions against ground truth.

[来源](https://arxiv.org/abs/2608.18726)

### AutoLab

新增：self-improvement-rsi, systems-optimization；移除：无。

AutoLab evaluates frontier models on long-horizon closed-loop optimization tasks across system optimization, CUDA kernel optimization, model development, and puzzle challenges, with 36 expert-curated tasks and a strict wall-clock budget.

[来源](https://arxiv.org/abs/2606.05080)

### AutoResearchExam

新增：self-improvement-rsi；移除：ai-r-d。

AutoResearchExam measures an agent's ability to improve and generalize on open ended machine learning research tasks. The dataset contains 29 tasks across machine learning research.

[来源](https://hub.harborframework.com/datasets/bespokelabs/autoresearch-exam)

### BehaviorBench

新增：ai-for-science, knowledge-qa；移除：无。

Evaluates foundation models on four behavioral science capabilities: behavior prediction and simulation, strategic decision-making, subject-trait inference, and behavioral knowledge application, assessing both individual-level and distributional alignment.

[来源](https://arxiv.org/abs/2606.24162)

### BenchBench-Protocol

新增：ai-for-science；移除：无。

Evaluates LLMs on 149 protocol-modification tasks reconstructed from real changes scientists made to published wet-lab protocols, using weighted rubric scoring.

[来源](https://arxiv.org/abs/2608.23898)

### BioSecBench-Surveillance

新增：ai-for-science；移除：无。

BioSecBench-Surveillance evaluates AI agents on pathogen genomic surveillance across 100 tasks spanning seven categories, including taxonomic classification and genetic-engineering detection. Agents receive raw sequencing data and surveillance context, and their structured answers are graded deterministically against ground truth.

[来源](https://arxiv.org/abs/2607.19262)

### BrainBench

新增：ai-for-science；移除：无。

BrainBench is a benchmark for instruction-conditioned EEG understanding covering four subsets across 17 datasets. It evaluates LLMs on producing scientific reports and artifacts from EEG recordings.

[来源](https://arxiv.org/abs/2608.04156)

### CharXiv

新增：ai-for-science, visual-understanding；移除：无。

A scientific chart reasoning benchmark that tests whether models can understand, interpret, and reason about complex scientific visualizations including plots, diagrams, and data charts.

[来源](https://arxiv.org/abs/2406.18521)

### CharXiv-D

新增：ai-for-science, visual-understanding；移除：无。

CharXiv-D is the descriptive questions subset of the CharXiv benchmark, designed to assess multimodal large language models' ability to extract basic information from scientific charts. It contains descriptive questions covering information extraction, enumeration, pattern recognition, and counting across 2,323 diverse charts from arXiv papers, all curated and verified by human experts.

[来源](https://llm-stats.com/benchmarks/charxiv-d)

### CharXiv-R

新增：ai-for-science, visual-understanding；移除：无。

CharXiv-R is the reasoning component of the CharXiv benchmark, focusing on complex reasoning questions that require synthesizing information across visual chart elements. It evaluates multimodal large language models on their ability to understand and reason about scientific charts from arXiv papers through various reasoning tasks.

[来源](https://llm-stats.com/benchmarks/charxiv-r)

### Chem World

新增：ai-for-science；移除：无。

Chem World integrates 17 chemical datasets with 800,000+ molecules for property prediction, offering a unified evaluation platform.

[来源](https://arxiv.org/abs/2607.28079)

### Chem2Gen-Bench

新增：ai-for-science；移除：无。

Chem2Gen-Bench evaluates chemical-to-genetic translation using 260,084 chemical and 1,099,045 genetic perturbation profiles in cell-target contexts. It measures pairwise alignment, retrieval success, and representation quality across matched perturbation settings.

[来源](https://arxiv.org/abs/2606.21109)

### ChemE ML Benchmarks

新增：ai-for-science；移除：无。

A locally runnable evaluation suite for machine learning methods on chemical engineering tasks, including concrete strength and airfoil self-noise datasets plus synthetic fixtures, with fixed splits, preprocessing, scoring metrics, and leaderboard generation.

[来源](https://github.com/yukevindai/cheme-ml-benchmarks)

### CloningScenarios

新增：ai-for-science；移除：无。

CloningScenarios is an expert-level multi-step reasoning benchmark about difficult genetic cloning scenarios in multiple-choice format. It evaluates dual-use biological knowledge relevant to bioweapons development.

[来源](https://llm-stats.com/benchmarks/cloningscenarios)

### CraftBench

新增：ai-for-science, vision-language-models；移除：无。

CraftBench evaluates scientific figure generation across three figure types and four input conditions, with human-drawn targets and a referenced VLM judge for scoring.

[来源](https://arxiv.org/abs/2605.30611)

### CritPt

新增：ai-for-science；移除：无。

Unpublished research-level physics: 71 composite challenges (70 test + 1 example) written by 50+ active physicists across 11 subfields, plus 190 simpler checkpo

[来源](https://artificialanalysis.ai/evaluations/critpt)

### Diagram-MMU

新增：ai-for-science, visual-understanding；移除：无。

Diagram-MMU evaluates multimodal language models on parsing scientific diagrams into LaTeX TikZ code, editing diagram code, and answering questions about diagrams, using 3.7k diagrams and 18.3k questions across six domains.

[来源](https://arxiv.org/abs/2608.12262)

### DiscoverPhysics

新增：ai-for-science；移除：无。

DiscoverPhysics is an interactive benchmark for LLM agents to discover laws of motion in simulated worlds with altered physics, scoring trajectory MSE and explanation quality.

[来源](https://arxiv.org/abs/2605.26087)

### EarthVerse

新增：ai-for-science；移除：无。

Evaluates scientific agents on 405 reproducible tasks across 199 documented natural hazard events, scoring fine-grained answer units and task-specific rubrics.

[来源](http://arxiv.org/abs/2608.23525v1)

### EdgeBench

新增：software-engineering；移除：ai-for-science。

EdgeBench evaluates autonomous agents on 134 real-world tasks across scientific discovery, software engineering, optimization, knowledge work, formal mathematics, and games. Each task requires 12+ hours of continuous interaction with multi-level feedback. Scoring tracks agent performance over time (at 2,4,6,8,10,12 hours). A public leaderboard is maintained; 51 tasks and evaluation framework are open-sourced.

[来源](https://arxiv.org/abs/2607.05155)

### Edit2TikZ

新增：ai-for-science；移除：无。

Edit2TikZ evaluates instruction-guided scientific figure editing with TikZ code, featuring 1,548 samples with textual or visual localization requests and multi-step edits, using a human-aligned evaluation framework to measure edit completion and content preservation.

[来源](https://arxiv.org/abs/2608.13441)

### EMMA

新增：ai-for-science, visual-understanding；移除：无。

EMMA (Enhanced MultiModal reAsoning) is a benchmark for organic multimodal reasoning across mathematics, physics, chemistry, and coding.

[来源](https://llm-stats.com/benchmarks/emma)

### EpiBench

新增：ai-for-science；移除：无。

EpiBench evaluates AI agents on short-horizon epigenomics analysis tasks across CUT&Tag/CUT&RUN, ATAC-seq, ChIP-seq, and DNA methylation workflows, with deterministically gradable answers.

[来源](https://arxiv.org/abs/2606.13602)

### FEPBench

新增：ai-for-science, content-generation；移除：无。

FEPBench evaluates text-to-image models on natural-science illustration generation using fine-grained atom set annotations, assessing instruction faithfulness, reasoning enrichment, and semantic precision across disciplines.

[来源](https://arxiv.org/abs/2606.05949)

### FigQA

新增：ai-for-science, visual-understanding；移除：无。

FigQA is a multiple-choice benchmark on interpreting scientific figures from biology papers. It evaluates dual-use biological knowledge and multimodal reasoning relevant to bioweapons development.

[来源](https://llm-stats.com/benchmarks/figqa)

### FormalTCS

新增：ai-for-science；移除：无。

175 expert-validated instances from STOC, FOCS, SODA, and COLT papers (2025-2026) for evaluating LLMs on end-to-end theoretical computer science research, including autoformalization and proof tasks.

[来源](https://arxiv.org/abs/2608.20153)

### FrontierChallenge

新增：ai-for-science；移除：无。

Evaluates scientific agents on 97 released end-to-end workflows across six domains, using pass rate and average score to measure full delivery of required scientific deliverables.

[来源](https://arxiv.org/abs/2608.24979)

### FrontierCS

新增：software-engineering；移除：ai-for-science。

Frontier-CS competitive programming benchmark: 172 open-ended algorithmic problems with partial scoring via go-judge.

[来源](https://llm-stats.com/benchmarks/frontiercs)

### GENEB

新增：ai-for-science, data-analysis；移除：无。

GENEB evaluates frozen representations from 40 genomic foundation models across 100 DNA classification tasks in 13 functional categories, using a unified linear probing protocol with full-data, 10-shot, and 1-shot regimes. Primary metric is Matthews correlation coefficient, with rankings at overall, category, and task levels.

[来源](https://arxiv.org/abs/2606.04525)

### Global PIQA

新增：无；移除：ai-for-science。

Global PIQA is a multilingual commonsense reasoning benchmark that evaluates physical interaction knowledge across 100 languages and cultures. It tests AI systems' understanding of physical world knowledge in diverse cultural contexts through multiple choice questions about everyday situations requiring physical commonsense.

[来源](https://llm-stats.com/benchmarks/global-piqa)

### GPQA Diamond

新增：ai-for-science；移除：无。

The hardest subset of GPQA featuring the most challenging graduate-level science questions. Sometimes reported separately from the standard GPQA benchmark.

[来源](https://arxiv.org/abs/2311.12022)

### IdeaGene-Bench

新增：ai-for-science；移除：无。

Evaluates scientific lineage reasoning and lineage-grounded idea generation through two tracks: closed-form IG-Exam and generation IG-Arena with Population-Evolution Score.

[来源](https://arxiv.org/abs/2607.08758)

### Imaging-101

新增：ai-for-science；移除：无。

Imaging-101 evaluates coding agents on 57 computational imaging tasks across six scientific domains, with three tracks for planning, function-level unit tests, and end-to-end reconstruction.

[来源](https://arxiv.org/abs/2607.10789)

### IPhO 2025 (Theory)

新增：ai-for-science；移除：无。

The three official theory problems from the 2025 International Physics Olympiad, scored with blinded human evaluation.

[来源](https://ai.meta.com/static-resource/muse-spark-eval-methodology)

### Kernel Bench L3

新增：self-improvement-rsi, software-engineering, systems-optimization；移除：无。

Kernel Bench L3 evaluates agentic GPU kernel optimization across 50 problems. Qwen reports two metrics for this benchmark: median per-problem speedup over the PyTorch eager reference and the fraction of problems faster than torch.compile.

[来源](https://llm-stats.com/benchmarks/kernel-bench-l3)

### KernelBench Hard

新增：self-improvement-rsi, software-engineering, systems-optimization；移除：无。

KernelBench Hard evaluates agentic GPU kernel optimization on the hardest problem set. Each question is scored by the agent's submitted operator TFLOPs relative to the theoretical peak of the current hardware, with the benchmark score being the average across all questions.

[来源](https://huggingface.co/MiniMaxAI/MiniMax-M3)

### LabOSBench

新增：ai-for-science；移除：无。

LabOSBench evaluates multimodal GUI agents on 96 subtasks across eight web-based scientific-instrument simulators, covering workflows from sample loading to result inspection. Agents operate via a browser, with execution-based evaluation on task completion.

[来源](https://arxiv.org/abs/2606.16802)

### LitTraceQA

新增：ai-for-science, knowledge-qa；移除：无。

LitTraceQA evaluates literature-grounded question answering over scientific papers, requiring systems to return paper IDs, evidence locations, and answers in multiple formats. The public split includes 55 examples with gold annotations.

[来源](https://arxiv.org/abs/2608.07370)

### LiveK12Bench

新增：ai-for-science；移除：无。

Dynamic benchmark for multimodal reasoning on high school exam questions in math, physics, chemistry, and biology, with a mock exam evaluation scheme.

[来源](https://arxiv.org/abs/2605.26781)

### MatPhaseBench

新增：ai-for-science, visual-understanding；移除：无。

MatPhaseBench evaluates vision-language models on understanding materials phase diagrams, using 200 diagram-text pairs from 3681 papers. It targets complex scientific image understanding, with tasks requiring deep comprehension and open-ended responses, covering 189 material systems and 70 elements.

[来源](https://arxiv.org/abs/2607.02934)

### MLE-bench

新增：self-improvement-rsi, software-engineering；移除：无。

MLE-Bench evaluates AI agents on machine learning engineering tasks by measuring their performance on Kaggle competitions.

[来源](https://arxiv.org/abs/2410.07095)

### MLE-Bench Lite

新增：self-improvement-rsi, software-engineering；移除：无。

MLE-Bench Lite evaluates AI agents on machine learning engineering tasks, testing their ability to build, train, and optimize ML models for Kaggle-style competitions in a lightweight evaluation format.

[来源](https://www.minimax.io/news/minimax-m27-en)

### MTPaperBananaBench

新增：ai-for-science, visual-understanding；移除：无。

Evaluates multi-turn scientific diagram refinement via 292 images annotated with 3,518 user requirements, using a user simulator that provides iterative feedback and measures requirement satisfaction and diagram quality.

[来源](https://arxiv.org/abs/2608.30241)

### OmniMatBench

新增：ai-for-science；移除：无。

OmniMatBench assesses multimodal reasoning in materials science across 19 subfields with 3,171 expert-curated QA and calculation problems, spanning four domains from fundamental knowledge to applied materials.

[来源](https://arxiv.org/abs/2605.29833)

### OmniPhys

新增：ai-for-science；移除：无。

Evaluates multimodal physics understanding, reasoning, and generation on 15,246 questions with 19,850 images from middle-school to university levels.

[来源](https://arxiv.org/abs/2608.25398)

### OmniScience (non-hallucination rate)

新增：knowledge-qa；移除：ai-for-science。

OmniScience variant that reports the non-hallucination rate, defined as one minus the hallucination rate.

[来源](https://llm-stats.com/benchmarks/omniscience-non-hallucination-rate)

### onepot-Bench

新增：ai-for-science；移除：无。

onepot-Bench 0 is a proprietary benchmark suite evaluating language models on synthetic chemistry capabilities, including cheminformatics literacy, safety behavior, and reaction outcome prediction.

[来源](https://arxiv.org/abs/2608.02595)

### OpenAI MMLU

新增：无；移除：ai-for-science。

MMLU (Massive Multitask Language Understanding) is a comprehensive benchmark that measures a text model's multitask accuracy across 57 diverse academic and professional subjects. The test covers elementary mathematics, US history, computer science, law, morality, business ethics, clinical knowledge, and many other domains spanning STEM, humanities, social sciences, and professional fields. To attain high accuracy, models must possess extensive world knowledge and problem-solving ability.

[来源](https://llm-stats.com/benchmarks/openai-mmlu)

### OpenSciToolBench

新增：ai-for-science；移除：无。

OpenSciToolBench is a benchmark with 900 tasks across four difficulty levels for evaluating LLM agents in open-world scientific tool acquisition.

[来源](https://arxiv.org/abs/2607.28692)

### Organic chemistry V2

新增：ai-for-science, knowledge-qa；移除：无。

Chemistry tasks covering spectroscopy, synthesis planning, reaction prediction, and chemical structure images.

[来源](https://www-cdn.anthropic.com/c5fbac3f0b1280a933ebd26d3cb8bb9f5bdeaf48/Claude%20Opus%205%20System%20Card.pdf)

### PaperBench

新增：ai-for-science, software-engineering；移除：无。

PaperBench is a benchmark for evaluating AI agents on their ability to replicate research papers. It tests models on complex, multi-step workflows involving code implementation, experimentation, and reproducing scientific results from academic publications.

[来源](https://qwen.ai/blog?id=qwen3.8)

### PerceptionTest

新增：spatial-reasoning, visual-understanding；移除：ai-for-science。

A novel multimodal video benchmark designed to evaluate perception and reasoning skills of pre-trained models across video, audio, and text modalities. Contains 11.6k real-world videos (average 23 seconds) filmed by participants worldwide, densely annotated with six types of labels. Focuses on skills (Memory, Abstraction, Physics, Semantics) and reasoning types (descriptive, explanatory, predictive, counterfactual). Shows significant performance gap between human baseline (91.4%) and state-of-the-art video QA models (46.2%).

[来源](https://llm-stats.com/benchmarks/perceptiontest)

### PIQA

新增：无；移除：ai-for-science。

Physical-interaction commonsense QA.

[来源](https://llm-stats.com/benchmarks/piqa)

### Principia

新增：ai-for-science；移除：无。

Evaluates Newtonian physics reasoning in video models through relational consistency between paired objects across eight phenomena, using a calibration-independent consistency score derived from real-world scenes.

[来源](https://arxiv.org/abs/2609.04200)

### ProteinGym Hard

新增：ai-for-science, knowledge-qa；移除：无。

Predicts mutation effects by ranking mutant protein sequences against wild type and comparing against laboratory measurements.

[来源](https://www-cdn.anthropic.com/c5fbac3f0b1280a933ebd26d3cb8bb9f5bdeaf48/Claude%20Opus%205%20System%20Card.pdf)

### ProtocolQA

新增：ai-for-science；移除：无。

ProtocolQA is a multiple-choice benchmark on troubleshooting failed experimental outcomes from common biological laboratory protocols. It evaluates dual-use biological knowledge relevant to bioweapons development.

[来源](https://llm-stats.com/benchmarks/protocolqa)

### ProtStructQA

新增：ai-for-science, knowledge-qa；移除：无。

ProtStructQA is an executable benchmark for protein structural question answering, with questions generated from DSL programs and answers obtained by executing on AlphaFold-predicted structures. Released 382.2K questions covering confidence, distances, PAE, solvent exposure, secondary structure, topology, and contacts.

[来源](https://arxiv.org/abs/2606.00451)

### PTXBench

新增：self-improvement-rsi, software-engineering, systems-optimization；移除：无。

PTXBench evaluates LLMs in generating architecture-specific PTX for GPU kernel optimization. It measures functional correctness, execution of target instructions, and speedup over frontier libraries across GEMM and attention workloads on H100 and B200 GPUs.

[来源](https://arxiv.org/abs/2608.17379)

### RATIO

新增：ai-for-science；移除：无。

Evaluates retrieval of scientific literature passages relevant to three ideation operations: Address, Broaden, and Specify, using millions of full-text computer science papers.

[来源](https://arxiv.org/abs/2608.27394)

### SBMLLM-Bench

新增：ai-for-science；移除：无。

Evaluates LLM reconstruction of executable systems-biology models from scientific papers using metrics like simulation ratio, species/reaction recovery, stoichiometric error, and AAFE reproducibility.

[来源](https://github.com/cosbi-research/SBMLLM-Bench)

### scBench-Long

新增：ai-for-science；移除：无。

scBench-Long evaluates long-horizon single-cell biology reasoning. Agents must recover scientific conclusions from raw or near-raw data without prescribed methods. It contains 21 evaluations spanning diverse biological contexts, with deterministic grading and trajectory rubrics.

[来源](https://arxiv.org/abs/2606.26563)

### SciConBench

新增：ai-for-science；移除：无。

SciConBench evaluates AI agents on open-domain scientific conclusion synthesis using 9,110 questions and expert-written conclusions from systematic reviews. The evaluation decomposes conclusions into atomic facts and measures correctness and comprehensiveness via factual precision and recall.

[来源](https://arxiv.org/abs/2606.11337)

### SciDocBench

新增：ai-for-science, visual-understanding；移除：无。

SciDocBench evaluates scientific document understanding with 124 expert-authored questions across seven capability groups and 19 subtasks in five scientific domains. Each question is tested under four conditions (English vs Chinese and all-images-first vs interleaved), yielding 496 instances. Performance is reported on a 100-point scale. Data and pipeline are released via a public repository.

[来源](https://arxiv.org/abs/2609.05141)

### SciDraw-Bench

新增：ai-for-science；移除：无。

SciDraw-Bench is a benchmark for scientific figure generation, with 32 tasks across eight figure types and ten disciplines. Each task pairs a natural-language prompt with a machine-checkable specification, and evaluation uses four dimensions: Text Fidelity, Semantic Correctness, Structural Quality, and Convention Adherence.

[来源](https://arxiv.org/abs/2606.28406)

### ScienceArena

新增：ai-for-science；移除：无。

Olympiad-style benchmark with open-ended physics, chemistry, and biology problems scored via rubrics and LLM judges.

[来源](https://arxiv.org/abs/2608.30517)

### ScienceQA

新增：ai-for-science, knowledge-qa, visual-understanding；移除：无。

ScienceQA is the first large-scale multimodal science question answering benchmark with 21,208 multiple-choice questions covering 3 subjects (natural science, language science, social science), 26 topics, 127 categories, and 379 skills. The benchmark includes both text and image modalities, featuring detailed explanations and Chain-of-Thought reasoning to diagnose multi-hop reasoning ability.

[来源](https://llm-stats.com/benchmarks/scienceqa)

### ScienceQA Visual

新增：ai-for-science, knowledge-qa, visual-understanding；移除：无。

ScienceQA Visual is a multimodal science question answering benchmark consisting of 21,208 multiple-choice questions from elementary and high school science curricula. The dataset covers 3 subjects (natural science, language science, social science), 26 topics, 127 categories, and 379 skills. 48.7% of questions include image context requiring multimodal reasoning. Questions are annotated with lectures (83.9%) and explanations (90.5%) to support chain-of-thought reasoning for science question answering.

[来源](https://llm-stats.com/benchmarks/scienceqa-visual)

### SciExplore

新增：ai-for-science, deep-research, rag-retrieval；移除：embodied-ai。

SciExplore evaluates scientific information-seeking and reasoning in LLMs and agents with four task types: scientific database navigation, ambiguous literature retrieval, missing reference completion, and cross-source structured knowledge synthesis, spanning 103 expert-curated tasks across more than ten scientific disciplines.

[来源](https://arxiv.org/abs/2607.20926)

### SciFigBench

新增：ai-for-science, vision-language-models, visual-understanding；移除：无。

SciFigBench is a diagnostic VLM benchmark for scientific figure understanding, covering perception, reasoning, and behavioral reliability under uncertainty.

[来源](https://arxiv.org/abs/2608.13267)

### SciFigPlag-Bench

新增：ai-for-science；移除：无。

SciFigPlag-Bench evaluates provenance-aware reasoning for scientific figure plagiarism detection. It includes 2,582 positive and 2,541 negative pairs, with tasks for pairwise detection, source attribution, reuse-type classification, and reuse correspondence localization.

[来源](https://arxiv.org/abs/2607.29124)

### SciFigQual-Bench

新增：ai-for-science；移除：无。

A benchmark for evaluating scientific figure quality across five dimensions with full-manuscript context, using 6,308 expert-rated images from top CS conferences and a fixed eval1200 test split.

[来源](https://arxiv.org/abs/2607.27084)

### SciFigure2Code

新增：ai-for-science；移除：无。

Evaluates generation of editable Python programs that preserve presentation of scientific figure panels, using a 337-panel test set across 31 chart subtypes, five domains, and three complexity levels.

[来源](https://arxiv.org/abs/2609.08155)

### SciHazard

新增：ai-for-science；移除：无。

SciHazard evaluates LLMs on scientific safety risks across 12 disciplines with 2,400 hazardous and 600 oversafety questions grounded in regulated entities. The DeHarm-Score decomposes harm into executability and net-new risk, providing a detailed scoring contract.

[来源](https://arxiv.org/abs/2607.18665)

### SciIntBench

新增：ai-for-science；移除：无。

SciIntBench is an adversarial benchmark of 810 prompts across ten responsible-conduct-of-research categories and three scientific domains. Each scenario appears in overt, covert, and benign versions to measure framing-sensitive refusal of misconduct.

[来源](https://arxiv.org/abs/2605.29468)

### SciIR-Bench

新增：ai-for-science, content-generation；移除：无。

SciIR-Bench evaluates text-to-image models on scientific image reasoning across three semiotic-aligned tracks: entity structure, scientific process, and scientific law. It uses an atomic checklist to convert scientific accuracy into verifiable fine-grained questions.

[来源](https://arxiv.org/abs/2606.30124)

### SCILAWS-BENCH

新增：ai-for-science；移除：无。

A benchmark for scientific law discovery using published research and real data.

[来源](https://arxiv.org/abs/2609.01552)

### SciMIF

新增：ai-for-science；移除：无。

Evaluates instruction following of MLLMs across five scientific disciplines with a taxonomy of 10 constraint groups.

[来源](https://arxiv.org/abs/2608.25973)

### SciR

新增：ai-for-science；移除：无。

SciR evaluates LLMs on deduction, induction, and causal abduction in scientific settings, with tasks generated from formal objects and rendered into multi-document scientific discourse. Difficulty is controlled along extraction and inference axes, with verifiable answers.

[来源](https://arxiv.org/abs/2606.13020)

### SciRisk-Bench

新增：ai-for-science；移除：无。

SciRisk-Bench evaluates AI4Science safety across 7 disciplines and 10 risk dimensions, assessing whether models recognize and avoid risks in scientific contexts.

[来源](https://arxiv.org/abs/2606.18936)

### SemiMat

新增：ai-for-science；移除：无。

Evaluates semi-supervised materials property regression across six tasks with fixed splits, four graph backbones, and normalized MAE, using labeled and unlabeled crystal data.

[来源](https://arxiv.org/abs/2608.30682)

### SocSci-Repro-Bench

新增：ai-for-science；移除：无。

SocSci-Repro-Bench evaluates AI coding agents on reproducing social science findings from 221 tasks across four disciplines and 13 domains, using studies with known reproducibility outcomes.

[来源](https://arxiv.org/abs/2606.11447)

### SpaPath-Bench

新增：ai-for-science；移除：无。

SpaPath-Bench evaluates pathology foundation models on spatial domain identification using paired whole slide images and spatial transcriptomics data from 42 public slides, measuring partition quality via unsupervised spatial coherence, transcriptomics-referenced agreement, and expert-referenced agreement.

[来源](https://arxiv.org/abs/2605.25764)

### SpatialBench Verified

新增：ai-for-science, knowledge-qa；移除：无。

Analysis of spatial transcriptomics data across externally validated biological problems.

[来源](https://www-cdn.anthropic.com/c5fbac3f0b1280a933ebd26d3cb8bb9f5bdeaf48/Claude%20Opus%205%20System%20Card.pdf)

### SpatialBench-Long

新增：ai-for-science；移除：无。

SpatialBench-Long evaluates AI agents on long-horizon spatial biology tasks, requiring recovery of biological claims from raw data across 24 evaluations.

[来源](https://arxiv.org/abs/2605.28065)

### STEM

新增：ai-for-science, visual-understanding；移除：无。

A comprehensive multimodal benchmark dataset with 448 skills and 1,073,146 questions spanning all STEM subjects (Science, Technology, Engineering, Mathematics), designed to test neural models' vision-language STEM skills based on K-12 curriculum. Unlike existing datasets that focus on expert-level ability, this dataset includes fundamental skills designed around educational standards.

[来源](https://llm-stats.com/benchmarks/stem)

### STEMGym

新增：ai-for-science；移除：无。

STEMGym is an open-source Gymnasium benchmark of 15 physics-simulated STEM worlds across five materials and four characterization tasks, scored by DEC-AUC.

[来源](https://arxiv.org/abs/2606.29592)

### StudyBench

新增：ai-for-science；移除：无。

Evaluates language models on hard physics textbook exercises (Application Set) and olympiad-level theory problems (Transfer Set), reporting pass@k accuracy for absorption and transfer of textbook knowledge.

[来源](https://arxiv.org/abs/2609.00787)

### SWE-bench Science

新增：ai-for-science, software-engineering；移除：无。

A repository-level benchmark with 119 tasks from 98 GitHub repositories across 20 scientific domains, organized into issue-driven, expert-exploratory, and engineering-integration paradigms.

[来源](https://arxiv.org/abs/2608.19799)

### TadA-Bench

新增：ai-for-science；移除：无。

TadA-Bench is a fixed-data replay benchmark derived from 31 wet-lab rounds of TadA directed evolution. Models rank ~1M protein, DNA, or RNA sequence variants appearing only in later rounds, with scores as Spearman, Recall@10%, and nDCG@10%.

[来源](https://arxiv.org/abs/2606.02624)

### TC-Bench

新增：ai-for-science；移除：无。

A benchmark dataset for tropical cyclone research with an automated construction pipeline, used to probe scientific alignment of vision foundation models.

[来源](https://arxiv.org/abs/2605.24782)

### TCS-BENCH

新增：ai-for-science；移除：无。

Evaluates LLMs on research-level theoretical computer science proof generation, using theorem-proving tasks from papers at STOC, FOCS, and SODA. Provides context for self-contained proofs and uses a verification agent to check correctness.

[来源](https://arxiv.org/abs/2608.09538)

### TerraBench

新增：ai-for-science；移除：无。

TerraBench is a benchmark for grounded Earth-science reasoning, built on TerraAgent, a ReAct-style framework that couples LLM planning with scientific tools. It includes 403 tasks across three tracks and eight domains with 24,500 verified steps.

[来源](https://arxiv.org/abs/2606.13148)

### TherapeuticsBench

新增：ai-for-science；移除：无。

TxBench-PP evaluates AI agents on small-molecule preclinical pharmacology tasks including mechanism-of-action, pharmacodynamics, and safety reasoning, using realistic workflow snapshots and deterministic scoring.

[来源](https://arxiv.org/abs/2606.19245)

### Virology Capabilities Test

新增：ai-for-science；移除：无。

Virology Capabilities Test (VCT) is an expert-level multiple-choice benchmark measuring the capability to troubleshoot complex virology laboratory protocols. It evaluates dual-use biological knowledge relevant to bioweapons development.

[来源](https://llm-stats.com/benchmarks/vct)


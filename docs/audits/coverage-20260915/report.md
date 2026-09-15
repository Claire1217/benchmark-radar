# 全类别外部参照审核（2026-09-15）

范围：2855 条记录，2653 条公开可见；29 个类别逐类检查，37 个有一手来源的参照条目。

这是定向抽样，不是领域全量数据集清单，也不能据此计算全站准确率。类别内记录数不是独立数据集家族数。当前仅生成审查结果，尚未改写线上标签或合并实体。

## 核心结论

GUI 的五条结果混合了评测层级。更广泛的漏收录、描述不足、同名异物与版本设置重复计数，说明分类与身份数据需要一起修正。

公开记录中 781 条没有研究类别；发现 7 组长描述完全相同的候选，均须核对，不能自动合并。

## 29 类结构检查

“仅标签证据”按当前这个类别的成员证据计算；不是对条目真假的判定。“外部参照通过”只证明所选条目能在该类找到。

| 类别 | 可见条目 | 仅标签证据 | 未核验目录条目 | 外部参照结果 |
|---|---:|---:|---:|---|
| Self-Improvement & RSI | 22 | 0 | 7 | 该参照条目已覆盖: 1 |
| AI for Science | 143 | 0 | 59 | 身份/版本待核对: 1 |
| Coding Agents | 94 | 0 | 46 | 已收录但目标分类缺失: 1 |
| Computer Use | 43 | 5 | 10 | 该参照条目已覆盖: 1 |
| GUI Grounding | 5 | 0 | 5 | 身份/版本待核对: 1；未匹配到准确条目: 4；该参照条目已覆盖: 2；已收录但目标分类缺失: 2 |
| Tool Use | 99 | 35 | 60 | 该参照条目已覆盖: 1 |
| Agent Memory | 20 | 0 | 1 | 未匹配到准确条目: 1 |
| Multi-Agent | 15 | 0 | 1 | 未匹配到准确条目: 1 |
| Deep Research | 17 | 0 | 2 | 已收录但目标分类缺失: 1 |
| RAG & Retrieval | 21 | 0 | 4 | 未匹配到准确条目: 1 |
| Long Context | 60 | 0 | 41 | 该参照条目已覆盖: 1 |
| Logical Reasoning | 15 | 0 | 8 | 未匹配到准确条目: 1 |
| Causal Reasoning | 37 | 0 | 7 | 未匹配到准确条目: 1 |
| Mathematical Reasoning | 137 | 65 | 113 | 该参照条目已覆盖: 1 |
| Instruction Following | 47 | 9 | 27 | 该参照条目已覆盖: 1 |
| Multilingual NLP | 99 | 0 | 51 | 该参照条目已覆盖: 1 |
| Vision-Language Models | 540 | 141 | 208 | 该参照条目已覆盖: 1 |
| Video Understanding | 180 | 3 | 34 | 该参照条目已覆盖: 1 |
| Audio & Speech | 87 | 1 | 28 | 身份/版本待核对: 1 |
| Embodied AI | 121 | 21 | 6 | 未匹配到准确条目: 1 |
| Safety & Alignment | 277 | 52 | 53 | 未匹配到准确条目: 1 |
| Knowledge & QA | 246 | 114 | 117 | 该参照条目已覆盖: 1 |
| Software Engineering | 258 | 126 | 182 | 该参照条目已覆盖: 1 |
| Data Analysis | 63 | 0 | 11 | 未匹配到准确条目: 1 |
| Systems Optimization | 13 | 2 | 8 | 身份/版本待核对: 1 |
| Cybersecurity | 63 | 0 | 40 | 该参照条目已覆盖: 1 |
| Visual Understanding | 242 | 146 | 173 | 该参照条目已覆盖: 1 |
| Spatial Reasoning | 99 | 17 | 40 | 未匹配到准确条目: 1 |
| Content Generation | 64 | 12 | 15 | 未匹配到准确条目: 1 |

## 外部参照逐项比对

未匹配项已比较名称、已登记别名，以及来源为 arXiv 时的论文 ID；派生版本仅列为候选，不当作原版覆盖。仍可能存在尚未登记的别名。

| 外部条目 | 评测层级 | 结论 | 本库准确匹配 / 相关候选 | 一手来源与依据 |
|---|---|---|---|---|
| ScreenSpot | benchmark | 身份/版本待核对 | 匹配：ScreenSpot；候选：ScreenSpot Pro | [来源](https://gui-agent.github.io/grounding-leaderboard/screenspot)：官方现有榜单明确显示 ScreenSpot (v2)；原版和 v2 的版本关系需记录，不能直接将原版标为已覆盖 v2。 |
| ScreenSpot-v2 | version | 未匹配到准确条目 | 匹配：无；候选：无 | [来源](https://gui-agent.github.io/grounding-leaderboard/screenspot)：官方榜单单独标注 v2。 |
| ScreenSpot Pro | benchmark | 该参照条目已覆盖 | 匹配：ScreenSpot Pro；候选：无 | [来源](https://arxiv.org/abs/2504.07981)：专业高分辨率 GUI 定位评测。 |
| GroundUI-1K | subset | 已收录但目标分类缺失 | 匹配：GroundUI-1K；候选：无 | [来源](https://ltzheng.github.io/agent-studio/)：AgentStudio 发布 GroundUI-1K 与 GroundUI-18K；1K 是评测子集。 |
| OSWorld-G | benchmark | 已收录但目标分类缺失 | 匹配：OSWorld-G；候选：无 | [来源](https://osworld-grounding.github.io/)：564 个标注样本，测试界面元素、布局和精细操作定位。 |
| UI-Vision | suite-with-grounding-track | 未匹配到准确条目 | 匹配：无；候选：无 | [来源](https://github.com/uivision/UI-Vision)：综合套件有 Element Grounding、Layout Grounding 和 Action Prediction；不能把三个任务自动计为三个独立数据集。 |
| VisualWebBench | suite-with-grounding-track | 该参照条目已覆盖 | 匹配：VisualWebBench；候选：无 | [来源](https://visualwebbench.github.io/)：七项网页评测中含 element grounding 与 action grounding。 |
| UI-I2E-Bench | benchmark | 未匹配到准确条目 | 匹配：无；候选：无 | [来源](https://microsoft.github.io/FIVE-UI-Evol/)：官方称 GUI visual grounding benchmark；UI-E2I-Synth 是所引论文/方法名称，不自动视为第二个基准。 |
| VenusBench-GD | benchmark | 未匹配到准确条目 | 匹配：无；候选：无 | [来源](https://github.com/inclusionAI/UI-Venus/tree/VenusBench-GD)：官方仓库新闻确认发布跨平台 GUI grounding 基准。 |
| OSWorld | interactive-suite | 该参照条目已覆盖 | 匹配：OSWorld；候选：iOSWorld, OSWorld 2.0, OSWorld Extended, OSWorld Screenshot-only, OSWorld-G, OSWorld-Verified | [来源](https://osworld-v1.xlang.ai/)：真实操作系统中的开放式多步任务；使用截图不等于单独评估 grounding。 |
| SWE-bench | benchmark | 已收录但目标分类缺失 | 匹配：SWE-bench；候选：Claw-SWE-Bench, Hypernym SWE-bench Artifact Replay, longswebench-32k, Multi-SWE Bench, QwenSWEBench, RH SWE-bench, Senior SWE-Bench, Senior SWE-Bench (v2026.06), SWE-bench Multilingual, SWE-bench Multimodal, SWE-bench Pro, SWE-Bench Pro Verified, SWE-Bench ProMax, SWE-bench Science, SWE-bench Verified, SWE-bench Verified (Agentic Coding), SWE-bench Verified (Agentless), SWE-bench Verified (Multiple Attempts), SWE-benchify-hard, TeleSWEBench, Vals SWE-bench mirror | [来源](https://www.swebench.com/)：真实仓库 issue 修复与测试验收；符合仓库级编码任务边界。 |
| BFCL v4 | version | 该参照条目已覆盖 | 匹配：BFCL v4；候选：无 | [来源](https://gorilla.cs.berkeley.edu/leaderboard.html)：函数调用评测第四版。 |
| LongMemEval | benchmark | 未匹配到准确条目 | 匹配：无；候选：无 | [来源](https://github.com/xiaowu0162/LongMemEval)：跨会话信息、知识更新和时间推理的长期记忆评测。 |
| MultiAgentBench | benchmark | 未匹配到准确条目 | 匹配：无；候选：无 | [来源](https://arxiv.org/abs/2503.01935)：测试多智能体协作和竞争。 |
| BrowseComp | benchmark | 已收录但目标分类缺失 | 匹配：BrowseComp；候选：BrowseComp (10-agent, prerelease), BrowseComp Long Context 128k, BrowseComp Long Context 256k, BrowseComp-VL, BrowseComp-zh, EvoBrowseComp, K-BrowseComp | [来源](https://openai.com/index/browsecomp/)：通过持续检索寻找难以发现的信息；短答案，不代表长报告写作评测。 |
| BEIR | suite | 未匹配到准确条目 | 匹配：无；候选：NanoBEIR Multilingual | [来源](https://github.com/beir-cellar/beir)：多个信息检索数据集组成的套件。 |
| LongBench v2 | version | 该参照条目已覆盖 | 匹配：LongBench v2；候选：无 | [来源](https://github.com/THUDM/LongBench)：长上下文理解第二版，和原版同一仓库但不同版本。 |
| FOLIO | benchmark | 未匹配到准确条目 | 匹配：无；候选：无 | [来源](https://arxiv.org/abs/2209.00840)：自然语言推理与一阶逻辑标注。 |
| CRASS | benchmark | 未匹配到准确条目 | 匹配：无；候选：无 | [来源](https://arxiv.org/abs/2112.11941)：反事实条件句问答测试。 |
| GSM8K | benchmark | 该参照条目已覆盖 | 匹配：GSM8K；候选：GSM-8K (CoT), GSM8K Chat | [来源](https://github.com/openai/grade-school-math)：多步骤小学数学文字题。 |
| IFEval | benchmark | 该参照条目已覆盖 | 匹配：IFEval；候选：European-IFEval, MM IF-Eval, MM-IFEval-Pro | [来源](https://github.com/google-research/google-research/tree/master/instruction_following_eval)：可验证指令遵循测试。 |
| MMMLU | benchmark | 该参照条目已覆盖 | 匹配：MMMLU；候选：无 | [来源](https://huggingface.co/datasets/openai/MMMLU)：多语言知识测试；不同语言不是独立基准家族。 |
| MMMU | suite | 该参照条目已覆盖 | 匹配：MMMU；候选：AA-MMMU-Pro, Diagram-MMU, MMMU (val), MMMU (validation), MMMU-Pro, MMMU-Pro (with tools), MMMU-Pro w/ Python, VideoMMMU | [来源](https://github.com/MMMU-Benchmark/MMMU)：跨学科多模态理解；官方区分 dev、validation、test。 |
| Video-MME | benchmark | 该参照条目已覆盖 | 匹配：Video-MME；候选：Video-MME (long, no subtitles), Video-MME (w/o subtitle), Video-MME (with subtitle), Video-MME-Logical, VideoMME w sub., VideoMME w/o sub. | [来源](https://github.com/MME-Benchmarks/Video-MME)：视频理解评测；字幕条件需要独立记录为评测设置。 |
| AIR-Bench (Audio) | benchmark | 身份/版本待核对 | 匹配：AIR-BENCH；候选：AgentFairBench, PAIR-Bench, REPAIR-Bench | [来源](https://arxiv.org/abs/2402.07729)：音频、语音和音乐理解；与风险政策安全评测 AIR-BENCH 同名不同实体。 |
| LIBERO | suite | 未匹配到准确条目 | 匹配：无；候选：LIBERO-Recover Benchmark, LIBERO-VIFO | [来源](https://arxiv.org/abs/2306.03310)：终身机器人操作与知识迁移套件。 |
| HarmBench | benchmark | 未匹配到准确条目 | 匹配：无；候选：EvoHarmBench | [来源](https://arxiv.org/abs/2402.04249)：自动红队与稳健拒绝评测。 |
| MMLU | suite | 该参照条目已覆盖 | 匹配：MMLU；候选：AA Global-MMLU-Lite, AA MMLU-Pro, CMMLU, French MMLU, Global-MMLU, Global-MMLU-Lite, GMMLU, KMMLU, KMMLU-Hard, KMMLU-Pro, KMMLU-Redux, MMLU (CoT), MMLU (EU-21 languages), MMLU Chat, MMLU French, MMLU-Base, MMLU-Pro, MMLU-Pro (Arcee), MMLU-ProX, MMLU-Redux, MMLU-redux-2.0, MMLU-STEM, MMLU: Anatomy, MMLU: Clinical Knowledge, MMLU: Medical Genetics, MMMLU, Multilingual MMLU, OpenAI MMLU, UrduMMLU, Vals MMLU-Pro mirror | [来源](https://github.com/hendrycks/test)：多学科知识问答。 |
| HumanEval | benchmark | 该参照条目已覆盖 | 匹配：HumanEval, HumanEval Plus；候选：HumanEval FIM, HumanEval-Average, HumanEval-ER, HumanEval-Mul, HumanEval-X++, HumanEvalFIM-Average, humanevalfix, Instruct HumanEval, Multipl-E HumanEval | [来源](https://github.com/openai/human-eval)：函数级代码生成与单元测试；不能仅凭 code 标签归为编码智能体。 |
| InfiAgent-DABench | benchmark | 未匹配到准确条目 | 匹配：无；候选：CODA-BENCH, SDABench, TadA-Bench, TrustDABench | [来源](https://arxiv.org/abs/2401.05507)：数据分析任务的智能体评测。 |
| KernelBench | benchmark | 身份/版本待核对 | 匹配：KernelBench；候选：DataKernelBench, Kernel Bench L3, KernelBench Hard | [来源](https://arxiv.org/abs/2502.10517)：正确性与 GPU kernel 效率评测。 |
| CyberSecEval 4 | suite | 该参照条目已覆盖 | 匹配：CyberSecEval 4；候选：无 | [来源](https://meta-llama.github.io/PurpleLlama/CyberSecEval/docs/intro)：网络安全弱点与防御能力评测套件。 |
| DocVQA | benchmark | 该参照条目已覆盖 | 匹配：DocVQA；候选：DocVQAtest | [来源](https://site.docvqa.org/datasets/docvqa)：给定文档图像进行问答；test 是数据划分。 |
| VSI-Bench | benchmark | 未匹配到准确条目 | 匹配：无；候选：无 | [来源](https://huggingface.co/datasets/mmaaz60/VSI_Bench)：视觉空间智能评测的官方数据卡。 |
| GenEval | benchmark | 未匹配到准确条目 | 匹配：无；候选：EgoGenEval | [来源](https://arxiv.org/abs/2310.11513)：文本到图像生成中对象、数量、颜色和位置的组合一致性。 |
| MLE-bench | benchmark | 该参照条目已覆盖 | 匹配：MLE-bench；候选：MLE-Bench Lite | [来源](https://github.com/openai/mle-bench)：机器学习工程任务；作为 AI R&D 纳入宽泛自我改进主题，不证明递归闭环。 |
| ScienceAgentBench | benchmark | 身份/版本待核对 | 匹配：ScienceAgentBench；候选：无 | [来源](https://arxiv.org/abs/2410.05080)：数据驱动科学发现的智能体任务。 |

## 现有 GUI 五条的逐项判断

| 当前条目 | 审核结论 |
|---|---|
| ScreenSpot | 定位基准；原版/v2 的具体身份需补足。 |
| ScreenSpot Pro | 独立专业 GUI grounding 基准。 |
| VisualWebBench | 综合套件中有明确 grounding 轨道，保留但注明层级。 |
| MobileWorld | [官方仓库](https://github.com/Tongyi-MAI/MobileWorld)评估完整移动任务，不能仅由简介提到 grounding 就计为独立定位测试。 |
| OSWorld Screenshot-only | [官方项目](https://osworld-v1.xlang.ai/)的截图观察设置；应归属交互基准的设置关系，不能仅凭使用截图判为定位评测。 |

本轮 GUI 参照额外核对到 GroundUI-1K、OSWorld-G、UI-Vision、UI-I2E-Bench、VenusBench-GD 和 ScreenSpot-v2；这仍不是完整领域清单。

后续扩展队列：已发现 [GUI-Primitives](https://arxiv.org/abs/2608.21832)；FineState-Bench 存在 [2025 论文](https://arxiv.org/abs/2508.09241)与 [2026 论文](https://arxiv.org/abs/2604.27974)，必须先查明关系，未计入本轮 37 项统计。


## 需要区分的实体关系

- alias：同一对象的不同名称，例如 MMMU val / validation 的现有描述完全相同，需用划分与协议核实。
- version / subset / split：ScreenSpot-v2、GroundUI-1K、MMMU validation 保留可搜索关系，但不能各自冒充独立家族。
- track：UI-Vision 和 VisualWebBench 含 grounding 评测；显示套件并注明轨道，不凭任务数量增加家族数。
- setting：OSWorld Screenshot-only、Video-MME 有无字幕属于观察或评测设置。
- adapter：ScienceAgentBench 的 Harbor 包属于运行适配，适配说明不能替代任务说明。
- homonym：AIR-Bench 音频与 AIR-BENCH 安全同名不同研究，应按论文和发布者区分。

## 同描述候选（不自动合并）

- HMMT 2025 / HMMT25
- HumanEval-Average / HumanEval-ER
- IF / IFEval
- LiveCodeBench / LiveCodeBench v5 / LiveCodeBench v5 24.12-25.2 / LiveCodeBench v6 / LiveCodeBench(01-09)
- LongFact Concepts / LongFact Objects
- MBPP EvalPlus / MBPP EvalPlus (base)
- MMMU (val) / MMMU (validation)

## 统一修正方案与验收

1. 先整理身份：为经核实条目建立 canonical benchmark、版本/划分/轨道/设置/适配关系；来源不确定的保持待核对。不能仅靠名称去重，也不能把现有随机 familyId 当成已审定家族。
2. 再补任务证据：保存官方任务、输入输出、评分对象、来源与审核日期；把平台安装说明放到适配信息。
3. 再统一分类：主要评测目标与仅涉及能力分开；GUI 需要明确定位输出/评分依据，网页检索不能仅因 navigation 归为电脑操作。
4. 分类计数先明确表示“匹配条目”；只有完成身份归并后才显示“基准家族数”，展开版本和设置不增加家族数。
5. 同时补覆盖：37 项中未匹配的官方基准建立收录队列；验证来源、实体关系与可见性后再导入，不能把模型/训练方法误收为新基准。
6. 验收包含正例、相邻类反例、同名异物、版本/设置不重复计数，以及每个参照条目的检索入口。未解决事项须保留明细，不能因内部单测通过就宣称领域完整。

## 可复现性

索引 SHA-256：`a5f79d7983882d40797faa76853e7f7e8d9c53a2434faa5b6d5ad73980e03d3c`。

`anchors.json` 为人工审核的一手来源参照；`anchor-results.json`、`categories.json`、`duplicate-candidates.json` 为此快照的计算结果。审查脚本不修改网站数据。

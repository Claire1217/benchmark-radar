# Benchmark classifier brief (taxonomy-v5, round 2)

Assign each benchmark ONE primary category and 0–2 secondary categories from the list below. Use ids exactly.

## Reasoning & Knowledge
- `math` — **Math Reasoning**: Competition, olympiad and research-level mathematics, including formal proofs. (e.g. AIME 2025, HMMT, FrontierMath, MATH-500)
- `knowledge-expert-qa` — **Knowledge & Expert QA**: Broad academic and expert knowledge questions, from exam-style multiple choice to frontier expert questions. (e.g. MMLU-Pro, GPQA Diamond, Humanity's Last Exam, SuperGPQA)
- `abstract-reasoning` — **Abstract Reasoning & Planning**: Novel-problem, puzzle, logical, causal and planning reasoning that does not rely on domain knowledge. (e.g. ARC-AGI-2, ZebraLogic, BIG-Bench Extra Hard, BBH)
- `factuality` — **Factuality & Hallucination**: Whether models state facts correctly, ground answers in sources and abstain when they do not know. (e.g. SimpleQA, SimpleQA Verified, FACTS Grounding, AA-Omniscience)
- `forecasting` — **Forecasting & Time Series**: Predicting future events and time-series values, including judgmental forecasting and anomaly detection in sequences. (e.g. ForecastBench, Prophet Arena, FutureX)

## Coding & AI R&D
- `agentic-coding` — **Agentic Coding & SWE**: Agents that resolve repository issues, work in terminals and complete multi-step software engineering tasks. (e.g. SWE-bench Verified, SWE-bench Pro, Terminal-Bench 2.1, SWE-bench Multilingual)
- `code-generation` — **Code Generation**: Function- and program-level code writing, competitive programming and code understanding without a long agent loop. (e.g. LiveCodeBench, HumanEval, Codeforces, Aider Polyglot)
- `ai-rnd` — **AI R&D & ML Engineering**: Agents doing machine-learning research and engineering: training, post-training, Kaggle-style tasks, paper replication and kernel or systems optimisation. (e.g. MLE-bench, PaperBench, RE-Bench, KernelBench)

## Agents
- `tool-use` — **Tool Use & Function Calling**: Choosing and calling tools, APIs and MCP servers correctly over single or multi-turn interactions, including customer-service style simulations. (e.g. τ²-bench, BFCL v4, MCP Atlas, Toolathlon)
- `computer-use` — **Computer Use & GUI Agents**: Operating desktops, phones and browsers through the screen: OS tasks, web navigation, mobile apps and GUI element grounding. (e.g. OSWorld, OSWorld-Verified, ScreenSpot Pro, AndroidWorld)
- `deep-research` — **Deep Research & Search**: Finding, retrieving and synthesising information across the web or large corpora, including retrieval-augmented generation. (e.g. BrowseComp, DeepSearchQA, WideSearch, FRAMES)
- `professional-work` — **Professional & Enterprise Work**: Economically valuable knowledge work: office documents, spreadsheets, enterprise workflows and occupational tasks across finance, consulting, law and similar jobs. (e.g. GDPval, APEX-Agents, OfficeQA Pro, AutomationBench)
- `agent-memory` — **Agent Memory & Personalization**: Remembering across sessions, updating stored knowledge and adapting to a specific user over time. (e.g. LoCoMo, LongMemEval, MemoryAgentBench)
- `agent-skills-evolution` — **Agent Skills & Self-Improvement**: Agents that acquire reusable skills, build their own harnesses or improve over repeated episodes. (e.g. SkillsBench)
- `multi-agent-games` — **Multi-Agent & Games**: Collaboration, negotiation and competition among agents, and interactive game environments. (e.g. TextArena, BALROG, VideoGameBench)

## Language & Interaction
- `long-context` — **Long Context**: Retrieving and reasoning over very long inputs such as books, codebases or long conversations. (e.g. MRCR, LongBench v2, AA-LCR, RULER)
- `instruction-following` — **Instruction Following**: Following explicit constraints, formats and multi-turn instructions. (e.g. IFEval, IFBench, MultiChallenge, Multi-IF)
- `chat-writing` — **Chat, Writing & Preference**: Open-ended chat quality judged by humans or models, creative writing and emotional intelligence. (e.g. Arena-Hard v2, MT-Bench, AlpacaEval 2.0, Creative Writing v3)
- `multilingual` — **Multilingual & Translation**: Performance across languages and machine translation. (e.g. MMMLU, MGSM, WMT24++, Global PIQA)

## Multimodal
- `visual-reasoning` — **Image & Visual Reasoning**: Answering and reasoning about images, charts, diagrams and visual math. (e.g. MMMU, MMMU-Pro, MathVista, CharXiv)
- `document-ocr` — **Document Understanding & OCR**: Reading text, tables, layouts and forms in scanned or digital documents. (e.g. OmniDocBench 1.5, OCRBench V2, DocVQA, InfoVQA)
- `video-understanding` — **Video Understanding**: Understanding and reasoning over short and long videos, including egocentric and streaming video. (e.g. Video-MME, VideoMMMU, LVBench, EgoSchema)
- `spatial-3d` — **Spatial & 3D Reasoning**: Spatial relations, 3D scenes, counting and geometric perception from images, video or point clouds. (e.g. VSI-Bench, CountBench, MMSI-Bench, 3DSRBench)
- `speech-audio` — **Speech & Audio**: Speech recognition and generation, audio understanding, music and real-time voice interaction. (e.g. MMAU, FLEURS, CoVoST2, Big Bench Audio)
- `image-video-generation` — **Image & Video Generation**: Generating and editing images, video and 3D assets from text or other inputs. (e.g. GenEval, T2I-CompBench, VBench, GEdit-Bench)

## Embodied & Physical
- `embodied-robotics` — **Robotics & Embodied AI**: Robot manipulation, vision-language-action policies, embodied planning, navigation and autonomous driving. (e.g. ERQA, LIBERO, RoboCasa, EmbodiedBench)
- `world-models` — **World Models & Physical Understanding**: Predicting how environments evolve, interactive world simulation and physical commonsense. (e.g. PhyBench, WorldScore)

## Safety & Security
- `safety-alignment` — **Safety & Alignment**: Harmful-content refusal, jailbreak robustness, honesty, sycophancy, bias and dangerous-capability (CBRN) evaluations. (e.g. MASK, WMDP, Virology Capabilities Test, StrongREJECT)
- `agent-security` — **Agent Security & Prompt Injection**: Attacks on and failures of agents: prompt injection, unsafe tool actions, permissions and privacy leakage. (e.g. AgentDojo, Agent Red Teaming)
- `cybersecurity` — **Cybersecurity**: Offensive and defensive security tasks: capture-the-flag, vulnerability discovery and exploitation. (e.g. CyberGym, Cybench, SEC-Bench Pro, ExploitBench)
- `content-detection` — **AI-Content Detection & Forensics**: Detecting AI-generated or manipulated text, code, images, audio and video, and attributing authorship. (e.g. RAID, M4)

## Application domains
- `science` — **Science**: Scientific research tasks and knowledge in physics, chemistry, biology and earth science, including scientific agents and scientific code. (e.g. SciCode, FrontierScience, LAB-Bench, ChemBench)
- `health-medicine` — **Health & Medicine**: Clinical, medical and health-related tasks for patients and practitioners. (e.g. HealthBench, MedQA, MedXpertQA)
- `finance-legal` — **Finance & Law**: Financial analysis and legal reasoning for professional use. (e.g. Finance Agent, CorpFin, LegalBench, Legal Research Bench)
- `engineering-design` — **Engineering & Hardware Design**: Engineering tasks such as CAD modelling, chip and circuit design (EDA), power systems and industrial operations. (e.g. VerilogEval, CAD-Recode)

## Indexes & Suites
- `composite-index` — **Composite Indexes**: Aggregate scores that combine many benchmarks into one capability index, such as the Artificial Analysis Intelligence Index or Epoch Capabilities Index. (e.g. Artificial Analysis Intelligence Index, Epoch Capabilities Index)

## Rules
- Classify by WHAT IS EVALUATED (the task), not by words in the name. A paper about 'memory-efficient inference' is not Agent Memory.
- primary = the single best fit. secondary only when the benchmark genuinely tests that too (e.g. a medical VQA benchmark: primary health-medicine, secondary visual-reasoning). Do not pad.
- Domain categories (science, health-medicine, finance-legal) are used when the domain is central. A coding benchmark on scientific code: primary science or agentic-coding depending on emphasis, the other as secondary.
- Image understanding → visual-reasoning; documents/OCR → document-ocr; video → video-understanding. Never invent a 'vision-language' category.
- Office/spreadsheet/data-analysis/enterprise workflows → professional-work.
- OS/desktop/mobile/browser GUI operation and GUI grounding → computer-use. Web *information seeking* (BrowseComp) → deep-research.
- Repo-level / terminal / issue-resolution → agentic-coding. Function-level, competitive programming, text-to-SQL → code-generation.
- Kernel/GPU/inference-efficiency optimisation, ML training/research tasks, paper replication → ai-rnd.
- Agent planning → abstract-reasoning. Embedding/retrieval-model benchmarks → deep-research. Generic classic NLU classification (sentiment, intent, spam) → knowledge-expert-qa only if knowledge is central, else "other".
- If nothing fits, use primary "other" (sparingly; we will review these to decide whether a new category is needed) and add a 2–4 word `suggest` label.
- confidence: high | medium | low.

Input rows: id, name, desc, old (legacy categories — noisy, do not trust), labs (# frontier labs reporting it), catalogTags.
Output: a JSON object mapping id -> {"p": primary, "s": [secondary...], "c": confidence, "suggest": optional}. Every input id must appear exactly once.
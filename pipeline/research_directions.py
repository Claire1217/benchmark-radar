"""Research-direction navigation v2: canonical, evidence-bearing, multi-axis taxonomy.

Multi-label task evidence with separate research themes and capability axes; not full-paper verification.
Keep legacy taxonomy intact for historical trends and existing integrations.
"""
import re
import json
from pathlib import Path

REVIEW_ROWS = json.loads((Path(__file__).resolve().parents[1] / "data/taxonomy_review_20260915.json").read_text())
REVIEW_BY_ID = {r["id"]: r for r in REVIEW_ROWS}

VERSION = "research-directions-v2"
RULES = {'Knowledge & Factuality': ('knowledge|factuality|factuality & grounding',
                            '\\b(factual (?:knowledge|recall|accuracy)|fact.checking|knowledge '
                            '(?:recall|retrieval|question)|closed.book|open.domain '
                            'question|encyclopedic|hallucination)\\b'),
 'Reasoning & Problem Solving': ('reasoning|knowledge & reasoning',
                                 '\\b(logical reasoning|causal reasoning|commonsense '
                                 'reasoning|deductive|inductive reasoning|abstract reasoning|multi.hop '
                                 'reasoning|reasoning tasks|reasoning abilities)\\b'),
 'Mathematics & Formal Reasoning': ('math|mathematics|mathematical reasoning|mathematics & formal sciences',
                                    '\\b(mathematical|theorem prov|formal proof|olympiad|algebra|geometry '
                                    'problems)\\b'),
 'Coding & Software Engineering': ('code|coding|code & software|frontend development|code generation',
                                   '\\b(code generation|software engineering|repository.level|bug '
                                   'fix|debugging|program synthesis|coding (?:tasks|benchmark)|software '
                                   'development)\\b'),
 'Agents & Planning': ('agents|agent|agentic|agents & tool use',
                       '\\b(agentic|autonomous agents?|multi.agent|long.horizon|agent planning|agents? '
                       '(?:on|in|for|to)|planning tasks)\\b'),
 'Tool Use': ('tool calling|tool use',
              '\\b(tool.calling|function.calling|tool.use|tool.augmented|api (?:calls|calling)|tool '
              'orchestration)\\b'),
 'Computer Use & GUI': ('computer use|gui',
                        '\\b(gui|computer.use|web navigation|browser.based tasks|desktop '
                        '(?:tasks|automation)|mobile (?:interaction|device control))\\b'),
 'Retrieval & Research': ('search|information retrieval|retrieval',
                          '\\b(information retrieval|retrieval.augmented|web search|deep research|literature '
                          'search|document retrieval|search agents?|web research)\\b'),
 'Context & Memory': ('long context|memory',
                      '\\b(long.context|long.term memory|agent memory|persistent '
                      'memory|cross.session|long.document|multi.document)\\b'),
 'Language & Communication': ('language|multilingual|korean|writing|communication|summarization|roleplay',
                              '\\b(multilingual|translation|summarization|creative writing|language '
                              'understanding|dialogue|conversational|linguistic|cross.lingual|role.play)\\b'),
 'Instruction Following': ('instruction following|instructionfollowing|structured output',
                           '\\b(instruction.following|structured output|format compliance|output '
                           'constraints|constraint satisfaction)\\b'),
 'Vision & Documents': ('vision|image to text|document understanding|chart understanding',
                        '\\b(image understanding|visual question|visual perception|document '
                        'understanding|chart understanding|ocr|object detection|image recognition|visual '
                        'grounding|image segmentation)\\b'),
 'Video & Temporal Understanding': ('video|video understanding',
                                    '\\b(video|temporal reasoning|action recognition)\\b'),
 'Audio & Speech': ('audio|speech to text|speech & audio',
                    '\\b(audio|speech|spoken language|music understanding|sound recognition)\\b'),
 'Spatial & 3D': ('spatial|spatial reasoning|3d',
                  '\\b(3d|spatial reasoning|spatial understanding|spatial intelligence|point clouds?)\\b'),
 'Multimodal Understanding': ('multimodal|multimodalgrounded|multimodal understanding',
                              '\\b(multimodal|multi.modal|vision.language|cross.modal)\\b'),
 'Content Generation': ('text-to-image|image-generation|creativity',
                        '\\b(image generation|video generation|text.to.image|text.to.video|speech '
                        'synthesis|music generation)\\b'),
 'Robotics & Embodiment': ('robotics|embodied|robotics & embodied ai',
                           '\\b(robotic|robots?|embodied|robot manipulation|autonomous '
                           'driving|locomotion|vision.language.action)\\b'),
 'Safety & Reliability': ('safety|privacy|safety & trustworthiness',
                          '\\b(jailbreak|prompt '
                          'injection|adversarial|robustness|privacy|fairness|toxicity|safety|trustworthiness|hallucination)\\b'),
 'Systems & Efficiency': ('systems|systems & efficiency',
                          '\\b(gpu kernel|inference latency|inference throughput|computational '
                          'efficiency|memory efficiency|distributed training|kernel optimization)\\b')}

TOPICS = {'Self-Improvement & RSI': ('self-evolution',
                            '\\b(recursive '
                            'self.improvement|self.improving|self.improvement|self.evolution|continual '
                            'learning|skill evolution)\\b'),
 'AI for Science': ('ai scientist|science|scientific research & ai for science|science & '
                    'research|biology|chemistry|physics',
                    '\\b(scientific (?:discovery|research|computing|workflow|reasoning|data)|ai '
                    'scientists?|drug.discovery|molecular|materials discovery|bioinformatics|computational '
                    '(?:chemistry|biology)|protein.ligand|protein (?:design|structure)|genomics|physics '
                    'problems|chemistry reasoning)\\b'),
 'AI R&D': ('',
            '\\b(ai r&d|machine.learning research|ml research|algorithmic design|training '
            '(?:algorithms?|pipelines?|recipes)|model improvement|automated machine learning|data.centric '
            'research|hyperparameter optimizers?|compute kernels|training.data strategies)\\b'),
 'Coding Agents': ('',
                   '\\b(coding agents?|software.engineering agents?|agentic coding|autonomous '
                   'software|repository.level|terminal agents?)\\b'),
 'Computer Use': ('computer use',
                  '\\b(gui|computer.use|web navigation|browser.based tasks|desktop automation)\\b'),
 'Deep Research': ('',
                   '\\b(deep research|web research|research agents?|literature search|literature '
                   'review|scientific literature)\\b'),
 'Agent Memory & Learning': ('',
                             '\\b(agent memory|long.term memory|persistent memory|cross.session|continual '
                             'learning|lifelong learning|skill evolution)\\b'),
 'Multi-Agent Collaboration': ('', '\\b(multi.agent|multiagent|agent collaboration|agent coordination)\\b')}

TOPIC_EXCLUSIONS = {'AuthMem-Bench': {'Self-Improvement & RSI': 'Description evaluates authority errors in memory, not '
                                             'improvement gains; related memory/safety work.'},
 'PACE-Bench': {'Self-Improvement & RSI': 'Description evaluates source-to-target adaptation; no retained '
                                          'recursive improvement established.'},
 'AA-Omniscience Index': {'AI for Science': 'Broad knowledge-reliability aggregate, not specifically a '
                                            'science benchmark.'},
 'MirrorCode': {'AI for Science': 'Bioinformatics is one of many program domains; description targets code '
                                  'reproduction.'}}

EXTRA = {'Agents & Planning': '\\b(?:llm|ai|vlm|game) agents?\\b|agents?\\x27 (?:ability|capability)',
 'Vision & Documents': 'text recognition|visual reasoning|audiovisual|caption|structured attribute|document '
                       'question',
 'Audio & Speech': 'music|audiovisual|acoustic',
 'Coding & Software Engineering': 'code solutions|code.space|specification generation|verilog|pddl',
 'Safety & Reliability': 'overconfidence|tool failures|demographic disparity|safeguards',
 'Retrieval & Research': 'search.enabled|metadata retrieval|literature linking'}

NEW = {'Data Analysis & Predictive Modeling': '\\b(data analysis|tabular|surrogate modeling|classification '
                                        'tasks|forecasting|prediction tasks|representation.level|linear '
                                        'probing|statistical analysis)\\b',
 'Scientific Computing & Discovery': '\\b(scientific|genomic|genetics|bioinformatics|chemistry|atmospheric '
                                     'science|statistical mechanic|molecular|protein|physics|scientific '
                                     'computation)\\b',
 'Cybersecurity': '\\b(cyber|cybersecurity|exploits?|network '
                  'attacks?|code.execution|vulnerabilit\\w*|ctf)\\b',
 'Games & Decision Making': '\\b(game|games|poker|decision.making|game agents|policy learning)\\b',
 'Evaluation & Measurement': '\\b(evaluat\\w* (?:judge|judges)|answer verification|semantic '
                             'correctness|rubric|overconfidence|calibration)\\b'}

AUDIT = {'SIFO': ([],
          ['Agents & Planning'],
          'Simple instruction following; description supplies no interactive agent workflow.'),
 'SIFO-Multiturn': ([],
                    ['Agents & Planning'],
                    'Multi-turn conversation alone does not establish agent planning or execution.'),
 'QwenSVG': (['Content Generation', 'Coding & Software Engineering'],
             ['Agents & Planning'],
             'SVG generation and rendered quality are scored; no agent loop established.'),
 'FrontierCode': (['Coding & Software Engineering'],
                  ['Reasoning & Problem Solving'],
                  'Description specifies difficult coding tasks, not a distinct generic reasoning '
                  'evaluation.'),
 'DataGovBench': (['Data Analysis & Predictive Modeling'],
                  [],
                  'Table QA and exploratory analysis outputs are directly assessed.'),
 'GENEB': (['Data Analysis & Predictive Modeling', 'Scientific Computing & Discovery'],
           [],
           'Frozen genomic representations evaluated with linear probes; not an AI scientist workflow.'),
 'NL-PDDL-Bench': (['Coding & Software Engineering'],
                   [],
                   'Formal planning specification generation; do not infer autonomous agent execution.'),
 'AtmosCoder-Bench': (['Coding & Software Engineering', 'Scientific Computing & Discovery'],
                      [],
                      'Atmospheric computation with executable code solutions and reference outputs.'),
 'MADB': (['Audio & Speech'], [], 'Music aesthetic assessment; listening judgment, not music generation.'),
 'MUDDLE': (['Context & Memory'],
            [],
            'Controlled document QA context-length and distractor study; not necessarily persistent memory.'),
 'OmniGameArena': (['Agents & Planning', 'Games & Decision Making'],
                   [],
                   'Interactive VLM game agents; reflection improvements do not alone establish recursive '
                   'improvement.'),
 'FLOATBench': (['Data Analysis & Predictive Modeling'],
                [],
                'Physical-system surrogate prediction benchmark, not an agent workflow.'),
 'TRL-Bench': (['Data Analysis & Predictive Modeling'],
               [],
               'Tabular representation probing across task suites.'),
 'IndustryBench-MIPU': (['Vision & Documents', 'Multimodal Understanding'],
                        [],
                        'Multi-image structured visual extraction and text recognition.'),
 'CAP-Correctness': (['Evaluation & Measurement', 'Knowledge & Factuality'],
                     [],
                     'Answer semantic correctness and verification are the assessed objects.'),
 'Failure-Transparent Agents': (['Agents & Planning', 'Safety & Reliability'],
                                [],
                                'Agent reporting of tool failures under pressure.'),
 'RevengeBench': (['Games & Decision Making', 'Coding & Software Engineering'],
                  [],
                  'Recover executable policies from game behavior; evidence does not require '
                  'self-improvement.'),
 'WuYu-EnvLE-Bench': ([],
                      [],
                      'Legal domain known, but workflow wording alone does not establish the exact '
                      'capability; keep pending.'),
 'MultiLF': ([], [], 'Description only says benchmark name; insufficient evidence.'),
 'Agent Poker Bench': ([],
                       [],
                       'Only asks which model earns money; proposed game label remains provisional, protocol '
                       'unknown.')}

def classify(r, rules):
    tags = {str(v).casefold() for key in ('topics', 'capabilities', 'catalogCategories') for v in r.get(key, [])}
    text = task_text(r)
    output = {}
    for (label, (aliases, pattern)) in rules.items():
        exact = sorted(tags & set(aliases.split('|'))) if aliases else []
        match = bounded_match(pattern, text)
        if exact or match:
            output[label] = {'tags': exact, 'excerpt': text[max(0, match.start() - 65):match.end() + 100] if match else None, 'basis': 'tag+text' if exact and match else 'tag' if exact else 'text-candidate'}
    return output

def matches(text, rules):
    result = {}
    for (label, pattern) in rules.items():
        m = bounded_match(pattern, text)
        if m:
            result[label] = {'basis': 'text-candidate', 'tags': [], 'excerpt': text[max(0, m.start() - 55):m.end() + 100]}
    return result

definitions = [('Self-Improvement & RSI',
  'Featured topics',
  '研究持续自我改进、技能演化与递归改进的评测。',
  'self improvement benchmark; RSI benchmark',
  'topic:Self-Improvement & RSI',
  ''),
 ('AI for Science',
  'Featured topics',
  '寻找科学计算、科学推理与发现任务；不局限于LLM agents。',
  'AI for science benchmark',
  'topic:AI for Science',
  ''),
 ('AI Scientist',
  'Featured topics',
  '研究自动执行科研流程的agent；科学知识问答不自动纳入。',
  'AI scientist benchmark; scientific research agent benchmark',
  '',
  'scientific research agents?|scientific discovery agents?|autonomous scientific|scientific '
  'workflows?|research intern tasks|scientific data analysis'),
 ('AI R&D',
  'Featured topics',
  '寻找模型训练、算法、数据与AI研发工程的评测。',
  'AI R&D benchmark; automated ML research benchmark',
  'topic:AI R&D',
  ''),
 ('Coding Agents',
  'Agents',
  '研究仓库级软件任务、终端操作与代码agent。',
  'coding agent benchmark; software engineering agent benchmark',
  'topic:Coding Agents',
  ''),
 ('Computer Use',
  'Agents',
  '研究在网页、桌面或移动端操作的agent。',
  'computer use benchmark; GUI agent benchmark',
  'label:Computer Use & GUI',
  ''),
 ('GUI Grounding',
  'Agents',
  '研究把指令定位到屏幕元素；不要求完整交互任务。',
  'GUI grounding benchmark; screen grounding benchmark',
  '',
  'gui grounding|screen elements|screen element|screenspot|element grounding'),
 ('Tool Use',
  'Agents',
  '研究函数选择、参数生成、工具调用与工具工作流。',
  'tool use benchmark; function calling benchmark',
  'label:Tool Use',
  ''),
 ('Agent Memory',
  'Agents',
  '研究跨会话记忆、知识更新和长期经验保留。',
  'agent memory benchmark; long term memory benchmark',
  '',
  'agent memory|long.term memory|persistent memory|cross.session|longmemeval|locomo|episodic experience'),
 ('Multi-Agent',
  'Agents',
  '研究多个agent的合作、协调与交互。',
  'multi agent benchmark',
  'topic:Multi-Agent Collaboration',
  ''),
 ('Deep Research',
  'Agents',
  '研究开放式搜索、证据综合与研究任务执行。',
  'deep research benchmark; web research benchmark',
  'topic:Deep Research',
  ''),
 ('RAG & Retrieval',
  'Language & reasoning',
  '研究检索质量、检索增强回答及其评测。',
  'RAG benchmark; information retrieval benchmark',
  '',
  'retrieval.augmented|information retrieval|document retrieval|\\bRAG\\b|ragbench|retrieval evaluation'),
 ('Long Context',
  'Language & reasoning',
  '研究长输入、跨段证据整合与长文档理解。',
  'long context benchmark',
  '',
  'long.context|long.document|long conversations|needle.in|longbench|context length'),
 ('Logical Reasoning',
  'Language & reasoning',
  '研究逻辑推断、演绎、归纳及形式化推理任务。',
  'logical reasoning benchmark',
  '',
  'logical reasoning|deduct|inductive reasoning|formal logic|logic puzzles'),
 ('Causal Reasoning',
  'Language & reasoning',
  '研究因果识别、干预和反事实推断。',
  'causal reasoning benchmark',
  '',
  'causal|counterfactual|cladder'),
 ('Mathematical Reasoning',
  'Language & reasoning',
  '寻找数学解题与形式证明评测。',
  'mathematical reasoning benchmark',
  'label:Mathematics & Formal Reasoning',
  ''),
 ('Instruction Following',
  'Language & reasoning',
  '研究指令约束、输出格式和遵循能力。',
  'instruction following benchmark',
  'label:Instruction Following',
  ''),
 ('Multilingual NLP',
  'Language & reasoning',
  '研究跨语言、低资源语言和多语言能力。',
  'multilingual benchmark',
  '',
  'multilingual|cross.lingual|low.resource language|translation'),
 ('Vision-Language Models',
  'Perception & safety',
  '研究视觉语言理解；可进一步搜索具体视觉任务。',
  'vision language model benchmark',
  'label:Multimodal Understanding',
  ''),
 ('Video Understanding',
  'Perception & safety',
  '研究视频理解、事件和时间关系。',
  'video understanding benchmark',
  'label:Video & Temporal Understanding',
  ''),
 ('Audio & Speech',
  'Perception & safety',
  '研究音频理解、语音与音乐任务。',
  'audio language model benchmark; speech benchmark',
  'label:Audio & Speech',
  ''),
 ('Embodied AI',
  'Perception & safety',
  '研究机器人、导航、控制和物理交互。',
  'embodied AI benchmark',
  'label:Robotics & Embodiment',
  ''),
 ('Safety & Alignment',
  'Perception & safety',
  '寻找安全性、鲁棒性、隐私与对齐相关评测。',
  'AI safety benchmark; alignment benchmark',
  'label:Safety & Reliability',
  '')]

NEEDS = [
    "Self-improvement, skill evolution and recursive improvement evaluations.",
    "Scientific reasoning, computation and discovery across research disciplines.",
    "Agents that execute scientific research workflows, beyond science question answering.",
    "Model training, algorithms, data and AI research engineering.",
    "Repository-level software tasks, terminals and coding agents.",
    "Agents operating websites, desktops and mobile devices.",
    "Locating interface elements from instructions or screenshots.",
    "Function calling, API selection, arguments and tool workflows.",
    "Persistent memory, cross-session recall and retained experience.",
    "Cooperation, coordination and interaction between agents.",
    "Open-ended search, evidence synthesis and research tasks.",
    "Information retrieval and retrieval-augmented generation.",
    "Long inputs, document understanding and cross-document evidence.",
    "Logical inference, deduction, induction and formal reasoning.",
    "Causality, interventions and counterfactual reasoning.",
    "Mathematical problem solving and formal proofs.",
    "Instruction constraints, structured outputs and format compliance.",
    "Cross-lingual, multilingual and low-resource language evaluation.",
    "Multimodal understanding, including vision-language tasks.",
    "Video understanding, events and temporal relationships.",
    "Audio, speech and music understanding.",
    "Robotics, navigation, control and physical interaction.",
    "Safety, alignment, robustness, privacy and reliability.",
]
ADDITIONAL = [
    ("Knowledge & QA", "Language & reasoning", "Factual knowledge, question answering and answer reliability.", "label:Knowledge & Factuality"),
    ("Software Engineering", "Software & data", "Code generation, debugging, repository changes and program correctness; not necessarily autonomous agents.", "label:Coding & Software Engineering"),
    ("Data Analysis", "Software & data", "Data preparation, statistics, predictive modeling and tabular analysis.", "label:Data Analysis & Predictive Modeling"),
    ("Systems Optimization", "Software & data", "Compute kernels, inference efficiency and system performance.", "label:Systems & Efficiency"),
    ("Cybersecurity", "Software & data", "Vulnerability analysis, exploits and defensive security tasks.", "label:Cybersecurity"),
    ("Visual Understanding", "Perception & safety", "Images, charts, documents, OCR and visual question answering.", "label:Vision & Documents"),
    ("Spatial Reasoning", "Perception & safety", "Spatial relations, 3D geometry and scene understanding.", "label:Spatial & 3D"),
    ("Content Generation", "Perception & safety", "Generation of images, video, speech and other media.", "label:Content Generation"),
]
for name, section, description, mapping in ADDITIONAL:
    definitions.append((name, section, description, "", mapping, ""))
    NEEDS.append(description)
INTERNAL_DIRECTIONS = [
    {"id": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
     "name": name, "section": section, "description": NEEDS[i]}
    for i, (name, section, *_rest) in enumerate(definitions)
]


DIRECTION_ALIASES = {"ai-scientist": "ai-for-science", "ai-r-d": "self-improvement-rsi"}
DIRECTIONS = [d for d in INTERNAL_DIRECTIONS if d["id"] not in DIRECTION_ALIASES]
for direction in DIRECTIONS:
    direction["axis"] = "theme" if direction["section"] == "Featured topics" else "capability"
    if direction["id"] == "self-improvement-rsi":
        direction["description"] = "AI and agent improvement: retained learning, training/data/algorithm development and compute optimization. Includes enabling AI R&D tasks; membership does not establish recursive self-improvement."
        direction["searchAliases"] = ["AI R&D", "AI research", "self evolution", "recursive self improvement", "RSI", "自我改进", "自进化"]
    elif direction["id"] == "ai-for-science":
        direction["description"] = "Science-specific reasoning, computation, experiments and discovery, including AI Scientist workflows. May overlap with coding, data analysis and other capabilities."
        direction["searchAliases"] = ["AI Scientist", "AI4Science", "scientific research", "科学", "科研"]


def task_text(record):
    return str(record.get("description") or record.get("oneLine") or "")


def bounded_match(pattern, text):
    return re.search(r"(?<!\w)(?:" + pattern + r")(?!\w)", text, re.I) if pattern else None


# Morphology is explicit; substrings in unrelated words must not create labels.
for i, definition in enumerate(definitions):
    if definition[0] == "Logical Reasoning":
        definitions[i] = (*definition[:-1], r"logical reasoning|deduct(?:ion|ive)|inductive reasoning|formal logic|logic puzzles")
    elif definition[0] == "Causal Reasoning":
        definitions[i] = (*definition[:-1], r"causal(?:ity| reasoning| inference| discovery)?|counterfactual(?:s| reasoning)?|cladder")
RULES["Knowledge & Factuality"] = (RULES["Knowledge & Factuality"][0], r"factual(?:ity| knowledge| recall| accuracy)|fact.checking|knowledge (?:recall|retrieval|questions?)|closed.book|open.domain questions?|question.answering|short.form factual|hallucinations?")
RULES["Coding & Software Engineering"] = (RULES["Coding & Software Engineering"][0], r"code (?:generation|completion|solutions?|reproduction)|software.engineering|repository.level|bug fix(?:es|ing)?|debugging|program synthesis|coding (?:tasks|benchmarks?|problems)|software development|Python SWE tasks|SWE tasks|code construction")
NEW["Data Analysis & Predictive Modeling"] = r"data.science|data analysis|tabular|surrogate modeling|classification tasks|forecasting|prediction tasks|representation.level|linear prob(?:e|es|ing)|statistical analysis|data wrangling"
RULES["Systems & Efficiency"] = (RULES["Systems & Efficiency"][0], r"(?:GPU|CUDA|compute) kernels?|kernel optimization|inference (?:latency|throughput)|computational efficiency|memory efficiency|distributed training|system(?:s)? optimization|training recipes")

RULES["Robotics & Embodiment"] = (RULES["Robotics & Embodiment"][0], r"robot(?:s|ic|ics)?|embodied|robot manipulation|autonomous driving|locomotion|vision.language.action|UAV|UGV|humanoid|LiDAR|vision.language navigation|visual navigation|SUMO.CARLA")
RULES["Safety & Reliability"] = (RULES["Safety & Reliability"][0], r"jailbreaks?|prompt injection|adversarial|robustness|privacy|fairness|toxicity|safety|trustworthiness|hallucinations?|bias|biases|biased|poisoning|PII detection|stereotyp(?:e|es|ical)|unsafe|refusal|misconduct")
RULES["Multimodal Understanding"] = (RULES["Multimodal Understanding"][0], r"multimodal|multi.modal|vision.language|cross.modal|audio.visual|video.language|VLMs?|MLLMs?|omnimodal")
RULES["Audio & Speech"] = (RULES["Audio & Speech"][0], r"audio|speech|spoken language|music(?:al)?|sound recognition|voice.agent|listening|WER|vishing")
RULES["Vision & Documents"] = (RULES["Vision & Documents"][0], r"image understanding|visual question|visual perception|document understanding|chart understanding|OCR|object detection|image recognition|visual grounding|image segmentation|scientific figure understanding|scientific diagrams?")
TOPICS["Coding Agents"] = ("", r"coding.agents?|software.engineering agents?|agentic coding|autonomous software|repository.level|terminal.agents?|terminal.use agents?")
TOPICS["Deep Research"] = ("", r"deep research|web research|research agents?|literature search|literature review|scientific literature|literature retrieval|scientific information.seeking|literature linking")
for i, definition in enumerate(definitions):
    extra_patterns = {
        "Agent Memory": r"agent memory|long.term memory|persistent memory|cross.session|longmemeval|locomo|episodic experience|memory system|across sessions|multi.session|conversational memory",
        "Long Context": r"long.contexts?|long.documents?|long conversations|needle.in|longbench|context lengths?",
        "Multilingual NLP": r"multilingual|cross.lingual|low.resource languages?|translations?|across languages|(?:seven|[0-9]+) (?:African |native |different )?languages",
        "RAG & Retrieval": r"retrieval.augment(?:ed|ation)|information retrieval|document retrieval|RAG|ragbench|retrieval evaluation|literature retrieval",
    }
    if definition[0] in extra_patterns:
        definitions[i] = (*definition[:-1], extra_patterns[definition[0]])

SCIENCE = r"scientific (?:domains?|problems?|tasks?|research|reasoning|computing|computation|workflows?|discovery|data|law|laws|figures?|charts?|diagrams?|reports?|disciplines?|database|information|safety)|(?:natural|social|earth|atmospheric|behavioral|biological|physical) sciences?|science[ -](?:question|questions|reasoning|curricula|textbook|problems)|(?:wet.lab|laboratory) protocols?|(?:biological|genetic|chemical|physics|chemistry|biology|genomic|genomics|bioinformatics|molecular|protein|virology|meteorological|materials|pharmacology|transcriptomics|astronomical|astrophysics|geophysical|quantum) (?:[\w-]+[ ,]+){0,5}(?:tasks?|problems?|reasoning|prediction|modeling|analysis|discovery|design|understanding|classification|optimization|challenges|knowledge|protocols?|regression)|computational (?:biology|chemistry|physics)|research.level (?:physics|theoretical computer science)|condensed matter|statistical mechanics|protein.ligand|(?:RNA|DNA) (?:sequencing|classification)|molecules for property prediction|laws of motion|AI4Science"
# Domain words are meaningful only in task descriptions, never benchmark names or inherited areas.
SCIENCE += r"|scientific|(?:life|natural|social|earth|atmospheric|behavioral|computational|materials)[ -]science|\b(?:biology|chemistry|genomics|epigenomics|bioinformatics|transcriptomics|protein|proteins|molecular|chemical|biological)\b|physics (?:olympiad|textbook|theory)|(?:expert|experts) in (?:biology|physics|chemistry)|(?:biology|physics|chemistry) subset|STEM(?:.subject| subjects)|science/math problems|research proposals|theoretical computer science research|tropical cyclone research"

IMPROVEMENT = r"recursive self.improvement|(?:agent|model|LLM|AI)[s\x27 -]*(?:and models? )?(?:on |via |through |for )?self.(?:improvement|evolution)|self.(?:improving|evolving) (?:LLM |AI )?(?:agents?|models?|systems)|continual learning|skill evolution|retained experience improves|LLM self.improvement|AI.self.improvement"
AI_DEVELOPMENT = r"machine learning engineering tasks|(?:rewrite|improv(?:e|ing)|optimiz(?:e|ing)|design(?:ing)?) (?:[\w-]+[ ,]+){0,5}(?:training algorithms?|training recipes|training.data strategies|compute kernels?|target models?)|(?:sequential )?hyperparameter optimizers?|(?:agentic )?(?:GPU|CUDA) kernel optimization|(?:open.ended |open ended )machine.learning research tasks|data.centric researchers|algorithmic design across|(?:optimize|optimizing) (?:[\w-]+[ ,]+){0,3}models"
SCIENCE_BROAD_SUITE = r"(?:spans?|spanning|across|cover(?:s|ing)?) (?:[\w-]+[ ,/()]+){0,12}(?:finance|business|recruiting|marketing|office|entertainment|humanities|law)"
BENCHMARK_EVOLVES = r"self.evolving (?:software.security |safety )?benchmark"


def theme_evidence(rule, text, match):
    return {"basis": "task-description", "rule": rule, "excerpt": text[max(0, match.start()-50):match.end()+100]}


def classify_themes(record):
    text = task_text(record)
    result = {}
    science = bounded_match(SCIENCE, text)
    # A generic mixed-domain suite is not a scientific task suite.
    mixed_fields = bool(bounded_match(r"business|finance|recruiting|marketing|office|email|entertainment|humanities|(?<!scientific )law|games|knowledge work|system administration", text) and bounded_match(r"domains?|disciplines?|subjects?|topics?|spans?|spanning|across", text))
    mixed_fields = mixed_fields or bool(bounded_match(r"(?:business and scientific documents|humanities and natural sciences|subjects from math to humanities)", text))
    if science and not mixed_fields:
        result["ai-for-science"] = theme_evidence("science-task", text, science)
    improvement = bounded_match(IMPROVEMENT, text)
    if not improvement and bounded_match(r"agents?|models?|LLMs?", text):
        improvement = bounded_match(r"self.evolution|self.improvement", text)
    development = bounded_match(AI_DEVELOPMENT, text)
    if (improvement or development) and not bounded_match(BENCHMARK_EVOLVES, text):
        match = improvement or development
        result["self-improvement-rsi"] = theme_evidence("agent-improvement" if improvement else "ai-development", text, match)
    # Prior reviewed exclusions still apply; suppress the incorrect membership only.
    for label in TOPIC_EXCLUSIONS.get(record.get("name"), {}):
        key = "ai-for-science" if label == "AI for Science" else "self-improvement-rsi"
        result.pop(key, None)
    return result


def classify_directions(record):
    """Return ordered stable IDs with auditable evidence; never mutate input."""
    review = record.get("taskReview")
    if review and review.get("sources"):
        known = {d["id"] for d in DIRECTIONS}
        if not set(review["directions"]) <= known:
            raise ValueError("Unknown reviewed research direction")
        return {d["id"]: {"basis": "primary-source-reviewed", "sources": review["sources"],
                "excerpt": review.get("note"), "reviewedAt": review.get("reviewedAt")}
                for d in DIRECTIONS if d["id"] in review["directions"]}
    labels = classify(record, RULES)
    topics = classify(record, {k: v for k, v in TOPICS.items() if k not in {"Self-Improvement & RSI", "AI for Science", "AI R&D"}})
    for label in TOPIC_EXCLUSIONS.get(record.get("name"), {}):
        topics.pop(label, None)
    text = task_text(record)
    for label, evidence in matches(text, {**NEW, **EXTRA}).items():
        labels.setdefault(label, evidence)
    if record.get("name") in AUDIT:
        add, remove, note = AUDIT[record["name"]]
        for label in add:
            labels[label] = {"basis": "description-reviewed", "tags": [], "excerpt": note}
        for label in remove:
            labels.pop(label, None)
    result = {}
    for direction, definition in zip(INTERNAL_DIRECTIONS, definitions):
        if direction["id"] in DIRECTION_ALIASES or direction["section"] == "Featured topics":
            continue
        mapping, pattern = definition[-2:]
        if mapping:
            axis, label = mapping.split(":", 1)
            evidence = (topics if axis == "topic" else labels).get(label)
        else:
            match = bounded_match(pattern, text)
            evidence = {"basis": "text-candidate", "excerpt": text[max(0, match.start()-50):match.end()+100]} if match else None
        if evidence:
            result[direction["id"]] = evidence
    # Themes use task-level evidence rather than broad source tags.
    result.pop("self-improvement-rsi", None)
    result.pop("ai-for-science", None)
    result.pop("ai-scientist", None)
    result.pop("ai-r-d", None)
    result.update(classify_themes(record))
    # Polyglot code is not evidence of cross-lingual natural-language evaluation.
    programming = bounded_match(r"programming languages?|(?:Python|JavaScript|Rust|C\+\+|Golang|TypeScript)|software engineering|repository.level|code editing|coding", text)
    natural_language = bounded_match(r"natural.languages?|cross.lingual|low.resource languages?|English|Chinese|Arabic|Bengali|Hindi|Spanish|translation quality", text)
    if programming and not natural_language:
        result.pop("multilingual-nlp", None)
    review = REVIEW_BY_ID.get(record.get("id"))
    if review and review["status"] != "pending-source-review":
        result = {key: {"basis": "primary-source-reviewed", "sourceUrl": review["source"], "excerpt": review["reason"], "reviewedAt": "2026-09-15"} for key in review["after"]}
    return {d["id"]: result[d["id"]] for d in DIRECTIONS if d["id"] in result}


def apply_reviewed_metadata(record):
    review = REVIEW_BY_ID.get(record.get("id"))
    if not review:
        return
    number = review["sample"]
    if number in {1, 2, 5, 19, 23, 25, 26, 28}:
        record["links"] = {**(record.get("links") or {}), "report": review["source"]}
    descriptions = {
        2: "Repository-level issue resolution across multiple programming languages, using real GitHub projects and executable tests.",
        5: "Video comprehension across diverse durations and domains, with visual frames, subtitles and audio."
    }
    if number in descriptions:
        record["description"] = descriptions[number]
        record["oneLine"] = descriptions[number]
        record["descriptionProvenance"] = {"basis": "primary-source-reviewed", "sourceUrl": review["source"], "reviewedAt": "2026-09-15"}
    if number == 2:
        # The old year was attached to a different benchmark paper.
        record["releasedAt"] = "0001-01-01"
        record["releaseDatePrecision"] = "unknown"
        record["firstRelease"] = {"year": None, "date": None}
        record.pop("releaseEvidence", None)
    if number == 1:
        record.setdefault("attention", {})["githubScope"] = "hosting_repo"


def annotate_records(records):
    for record in records:
        apply_reviewed_metadata(record)
        evidence = classify_directions(record)
        record["researchDirections"] = list(evidence)
        record["researchDirectionEvidence"] = evidence
        text = task_text(record)
        facets = {}
        patterns = {"ai-r-d": AI_DEVELOPMENT, "explicit-rsi": r"recursive self.improvement", "scientific-workflow": r"scientific (?:research |discovery )?(?:agents?|workflows?)|scientific data analysis|research intern tasks"}
        for key, pattern in patterns.items():
            match = bounded_match(pattern, text)
            if match:
                facets[key] = theme_evidence(key, text, match)
        if "ai-for-science" in evidence:
            match = bounded_match(r"questions?|multiple.choice|textbook|knowledge|curricula|olympiad", text)
            if match:
                facets["science-knowledge"] = theme_evidence("science-knowledge", text, match)
        record["researchFacets"] = facets
        flags = []
        if not evidence:
            flags.append("no-supported-direction")
        if any(v.get("basis") == "tag" for v in evidence.values()):
            flags.append("source-tag-only")
        if "ai-for-science" not in evidence and bounded_match(r"scientific|science|biology|chemistry|physics", task_text(record)):
            flags.append("science-mention-needs-scope-review")
        if "self-improvement-rsi" not in evidence and bounded_match(r"AI R&D|ML research|self.evolving benchmark", task_text(record)):
            flags.append("improvement-mention-without-task-evidence")
        record["researchClassification"] = {
            "version": VERSION,
            "status": "classified" if evidence else "needs-review",
            "source": "description-and-explicit-source-tags",
            "reviewFlags": flags,
        }


def direction_manifest(records):
    visible = [r for r in records if r.get("displayEligible") is not False and r.get("evaluationMode") != "viewpoint_probe"]
    return {
        "version": VERSION,
        "method": "Task-description rules with word boundaries and explicit source tags; inherited areas are excluded. Themes and capabilities overlap. Not a full-paper verification.",
        "aliases": DIRECTION_ALIASES,
        "legacyFilters": {"domain": {"Science & Research": "ai-for-science"}, "topic": {"Self-Evolution": "self-improvement-rsi"}},
        "axes": {"theme": "Research objective", "capability": "Evaluated task or capability"},
        "unclassifiedCount": sum(not r.get("researchDirections") for r in visible),
        "directions": [{**d, "count": sum(d["id"] in r.get("researchDirections", []) for r in visible)} for d in DIRECTIONS],
    }


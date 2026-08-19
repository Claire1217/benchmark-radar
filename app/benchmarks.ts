export type BenchmarkLinkSet = {
  paper: string | null;
  code: string | null;
  data: string | null;
};

export type BenchmarkMetric = {
  name: string;
  value: string;
  note?: string;
};

export type BenchmarkDemoRecord = {
  id: string;
  name: string;
  oneLine: string;
  area: string;
  capabilities: string[];
  topics: string[];
  construction: string;
  annotation: string;
  readiness: "Paper only" | "Inspectable" | "Runnable" | "Maintained";
  firstSeen: string;
  adoption30d: number;
  heat: number;
  confidence: "Low" | "Medium" | "High";
  links: BenchmarkLinkSet;
  motivation: string;
  constructionDetail: string;
  metrics: BenchmarkMetric[];
  demo: true;
};

/**
 * Prototype data only.
 *
 * Benchmark names and outbound links refer to public projects where possible.
 * firstSeen, adoption30d, heat, confidence, and every displayed metric below are
 * intentionally simulated for product-design testing; they are not live claims.
 */
export const benchmarks: BenchmarkDemoRecord[] = [
  {
    id: "airs-bench",
    name: "AIRS-Bench",
    oneLine:
      "AI Scientist · tests the full ML research loop, where coding-only evaluations miss hypothesis quality and experimental progress.",
    area: "Agents & Tool Use",
    capabilities: ["Research planning", "Experiment execution", "Result interpretation"],
    topics: ["AI Scientist", "RSI", "Autonomous research"],
    construction: "Transform Existing",
    annotation: "Expert Generated",
    readiness: "Maintained",
    firstSeen: "2026-08-19",
    adoption30d: 34,
    heat: 92,
    confidence: "High",
    links: {
      paper: null,
      code: "https://github.com/facebookresearch/airs-bench",
      data: "https://github.com/facebookresearch/airs-bench/tree/main/tasks",
    },
    motivation:
      "Measure whether an agent can turn a research specification into a competitive, evidence-backed ML result rather than merely produce runnable code.",
    constructionDetail:
      "Public ML research problems are repackaged as problem–dataset–metric task triplets with executable evaluation and human reference targets.",
    metrics: [
      { name: "Demo tasks", value: "20", note: "Demo display value" },
      { name: "Demo adoption (30d)", value: "34 projects", note: "Simulated" },
      { name: "Demo momentum", value: "+28%", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "mle-bench",
    name: "MLE-bench",
    oneLine:
      "AI Scientist · evaluates end-to-end ML engineering under compute budgets, beyond short notebook or code-completion tasks.",
    area: "Agents & Tool Use",
    capabilities: ["Model development", "Tool use", "Long-horizon iteration"],
    topics: ["AI Scientist", "ML engineering", "Kaggle"],
    construction: "Transform Existing",
    annotation: "Rule-based / Automatic",
    readiness: "Maintained",
    firstSeen: "2026-08-17",
    adoption30d: 27,
    heat: 86,
    confidence: "High",
    links: {
      paper: "https://arxiv.org/abs/2410.07095",
      code: "https://github.com/openai/mle-bench",
      data: "https://github.com/openai/mle-bench/tree/main/mlebench",
    },
    motivation:
      "Test whether autonomous agents can perform practical model development, validation, and submission workflows over many hours.",
    constructionDetail:
      "Existing Kaggle competitions are standardized into reproducible agent tasks with fixed data preparation, grading, and resource contracts.",
    metrics: [
      { name: "Demo success", value: "31.4%", note: "Simulated prototype value" },
      { name: "Demo median runtime", value: "11.8 h", note: "Simulated" },
      { name: "Demo adoption (30d)", value: "27 projects", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "cadgenbench",
    name: "CADGenBench",
    oneLine:
      "CAD · scores editable mechanical-part generation and modification, where image similarity cannot verify valid engineering geometry.",
    area: "Science & Engineering",
    capabilities: ["CAD generation", "CAD editing", "Geometric validity"],
    topics: ["CAD", "Text-to-CAD", "Engineering agents"],
    construction: "Hybrid",
    annotation: "Expert Generated",
    readiness: "Maintained",
    firstSeen: "2026-08-14",
    adoption30d: 18,
    heat: 90,
    confidence: "High",
    links: {
      paper: null,
      code: "https://github.com/huggingface/cadgenbench",
      data: "https://huggingface.co/datasets/HuggingAI4Engineering/cadgenbench-data",
    },
    motivation:
      "Move CAD evaluation from attractive renders toward valid, editable STEP/BREP artifacts that satisfy mechanical specifications.",
    constructionDetail:
      "Generation and edit requests are paired with reference CAD artifacts; submissions pass a validity gate before geometry and feature-level scoring.",
    metrics: [
      { name: "Demo samples", value: "1,240", note: "Simulated" },
      { name: "Demo valid-part rate", value: "42.8%", note: "Simulated" },
      { name: "Demo heat (30d)", value: "+41%", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "cadtestbench",
    name: "CADTestBench",
    oneLine:
      "CAD · uses executable geometric tests to catch topology and constraint failures that aggregate shape scores conceal.",
    area: "Science & Engineering",
    capabilities: ["Constraint satisfaction", "Topology reasoning", "Artifact testing"],
    topics: ["CAD", "Executable evaluation", "Text-to-CAD"],
    construction: "Original Synthetic",
    annotation: "Expert Generated",
    readiness: "Runnable",
    firstSeen: "2026-08-11",
    adoption30d: 12,
    heat: 82,
    confidence: "Medium",
    links: {
      paper: "https://arxiv.org/abs/2605.07807",
      code: null,
      data: null,
    },
    motivation:
      "Evaluate whether a generated CAD model actually obeys prompt-level geometric and topological requirements.",
    constructionDetail:
      "Natural-language design requirements are converted into executable CAD tests; candidate artifacts receive granular pass/fail diagnostics.",
    metrics: [
      { name: "Demo test cases", value: "3,600", note: "Simulated" },
      { name: "Demo test pass rate", value: "54.2%", note: "Simulated" },
      { name: "Demo adoption (30d)", value: "12 projects", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "muse-cad",
    name: "MUSE",
    oneLine:
      "CAD · evaluates manufacturable, functional assemblies, closing the gap between single-part geometry and usable engineering design.",
    area: "Science & Engineering",
    capabilities: ["Assembly design", "Manufacturability", "Design-intent alignment"],
    topics: ["CAD", "Assemblies", "Engineering evaluation"],
    construction: "Hybrid",
    annotation: "Expert Generated",
    readiness: "Inspectable",
    firstSeen: "2026-08-08",
    adoption30d: 9,
    heat: 76,
    confidence: "Medium",
    links: {
      paper: "https://arxiv.org/abs/2605.28579",
      code: "https://dong7313.github.io/muse-benchmark/",
      data: "https://dong7313.github.io/muse-benchmark/",
    },
    motivation:
      "Ask whether generated CAD assemblies can be built and used, rather than only whether their rendered shapes resemble references.",
    constructionDetail:
      "Practical assembly briefs are paired with structured specifications and evaluated through code, geometry, and design-intent stages.",
    metrics: [
      { name: "Demo assemblies", value: "480", note: "Simulated" },
      { name: "Demo engineering-ready", value: "17.6%", note: "Simulated" },
      { name: "Demo heat (30d)", value: "+33%", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "osworld",
    name: "OSWorld",
    oneLine:
      "Agents · measures cross-application computer use in real operating systems, where browser-only tasks miss desktop state and recovery.",
    area: "Agents & Tool Use",
    capabilities: ["Computer use", "Visual grounding", "Long-horizon recovery"],
    topics: ["GUI agents", "Computer use", "Desktop automation"],
    construction: "Interactive Environment",
    annotation: "Expert Generated",
    readiness: "Maintained",
    firstSeen: "2026-08-04",
    adoption30d: 31,
    heat: 84,
    confidence: "High",
    links: {
      paper: "https://arxiv.org/abs/2404.07972",
      code: "https://github.com/xlang-ai/OSWorld",
      data: "https://github.com/xlang-ai/OSWorld/tree/main/evaluation_examples",
    },
    motivation:
      "Test whether multimodal agents can operate real applications and preserve task state across long, failure-prone workflows.",
    constructionDetail:
      "Human-authored tasks run inside reproducible desktop environments with state-based evaluators and application-specific setup scripts.",
    metrics: [
      { name: "Demo tasks", value: "369", note: "Simulated display value" },
      { name: "Demo success", value: "38.1%", note: "Simulated" },
      { name: "Demo heat (30d)", value: "+19%", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "robocerebra",
    name: "RoboCerebra",
    oneLine:
      "Robotics · stresses long-horizon manipulation with compositional tasks, where short pick-and-place success overstates autonomy.",
    area: "Robotics & Embodied AI",
    capabilities: ["Long-horizon manipulation", "Task decomposition", "Failure recovery"],
    topics: ["Robotics", "Embodied AI", "Manipulation"],
    construction: "Interactive Environment",
    annotation: "Expert Generated",
    readiness: "Inspectable",
    firstSeen: "2026-07-31",
    adoption30d: 14,
    heat: 73,
    confidence: "Medium",
    links: {
      paper: "https://robocerebra.github.io/",
      code: "https://robocerebra.github.io/",
      data: "https://robocerebra.github.io/",
    },
    motivation:
      "Reveal compounding planning and control failures that only appear when robots must execute extended manipulation sequences.",
    constructionDetail:
      "Composable skills and scene variations are assembled into long-horizon manipulation episodes with step-level and task-level evaluation.",
    metrics: [
      { name: "Demo episodes", value: "2,100", note: "Simulated" },
      { name: "Demo full-task success", value: "26.7%", note: "Simulated" },
      { name: "Demo adoption (30d)", value: "14 projects", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "libero",
    name: "LIBERO",
    oneLine:
      "Robotics · evaluates lifelong robot learning across task suites, exposing transfer and forgetting hidden by one-task evaluation.",
    area: "Robotics & Embodied AI",
    capabilities: ["Continual learning", "Manipulation", "Knowledge transfer"],
    topics: ["Robotics", "Lifelong learning", "VLA"],
    construction: "Interactive Environment",
    annotation: "Mixed",
    readiness: "Maintained",
    firstSeen: "2026-07-28",
    adoption30d: 25,
    heat: 77,
    confidence: "High",
    links: {
      paper: "https://arxiv.org/abs/2306.03310",
      code: "https://github.com/Lifelong-Robot-Learning/LIBERO",
      data: "https://huggingface.co/datasets/openvla/modified_libero_rlds",
    },
    motivation:
      "Measure how effectively a robot policy acquires new tasks while retaining and transferring previously learned knowledge.",
    constructionDetail:
      "Simulation suites systematically vary objects, spatial relations, goals, and task ordering, with demonstrations and reproducible rollouts.",
    metrics: [
      { name: "Demo task suites", value: "4", note: "Simulated display value" },
      { name: "Demo transfer score", value: "0.61", note: "Simulated" },
      { name: "Demo adoption (30d)", value: "25 projects", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "mmmu",
    name: "MMMU",
    oneLine:
      "Multimodal · tests expert-level reasoning across many disciplines, beyond perception-heavy caption and VQA benchmarks.",
    area: "Multimodal",
    capabilities: ["Visual reasoning", "Domain knowledge", "Multi-discipline problem solving"],
    topics: ["Multimodal reasoning", "Expert knowledge", "VLM"],
    construction: "Original Observed",
    annotation: "Expert Generated",
    readiness: "Maintained",
    firstSeen: "2026-07-25",
    adoption30d: 39,
    heat: 79,
    confidence: "High",
    links: {
      paper: "https://arxiv.org/abs/2311.16502",
      code: "https://github.com/MMMU-Benchmark/MMMU",
      data: "https://huggingface.co/datasets/MMMU/MMMU",
    },
    motivation:
      "Evaluate whether multimodal models combine specialist knowledge with reasoning over diagrams, charts, notation, and other visual evidence.",
    constructionDetail:
      "Expert-level questions and images from diverse academic disciplines are normalized into a shared multiple-choice and open-response format.",
    metrics: [
      { name: "Demo questions", value: "11.5k", note: "Simulated display value" },
      { name: "Demo best score", value: "78.3%", note: "Simulated" },
      { name: "Demo adoption (30d)", value: "39 projects", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "omnidocbench",
    name: "OmniDocBench",
    oneLine:
      "Multimodal · evaluates end-to-end document parsing across layouts and element types, where OCR accuracy alone misses structural fidelity.",
    area: "Multimodal",
    capabilities: ["Document parsing", "Layout understanding", "Structured extraction"],
    topics: ["Document AI", "OCR", "Multimodal"],
    construction: "Hybrid",
    annotation: "Expert Generated",
    readiness: "Runnable",
    firstSeen: "2026-07-22",
    adoption30d: 16,
    heat: 71,
    confidence: "Medium",
    links: {
      paper: "https://arxiv.org/abs/2412.07626",
      code: "https://github.com/opendatalab/OmniDocBench",
      data: "https://huggingface.co/datasets/opendatalab/OmniDocBench",
    },
    motivation:
      "Measure whether document models preserve reading order, equations, tables, and layout—not merely whether they recover isolated characters.",
    constructionDetail:
      "Diverse document pages are annotated at multiple granularities and scored through text, structure, ordering, and element-specific metrics.",
    metrics: [
      { name: "Demo pages", value: "1,355", note: "Simulated display value" },
      { name: "Demo structure score", value: "67.4", note: "Simulated" },
      { name: "Demo heat (30d)", value: "+14%", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "msts",
    name: "MSTS",
    oneLine:
      "Safety · probes multilingual multimodal harms, closing the gap left by English-only, text-only safety tests.",
    area: "Safety & Trustworthiness",
    capabilities: ["Multimodal safety", "Multilingual robustness", "Harm recognition"],
    topics: ["Safety", "Multimodal", "Red teaming"],
    construction: "Hybrid",
    annotation: "Expert Generated",
    readiness: "Runnable",
    firstSeen: "2026-07-19",
    adoption30d: 13,
    heat: 74,
    confidence: "Medium",
    links: {
      paper: "https://github.com/paul-rottger/msts-multimodal-safety",
      code: "https://github.com/paul-rottger/msts-multimodal-safety",
      data: "https://github.com/paul-rottger/msts-multimodal-safety/tree/main/data",
    },
    motivation:
      "Test whether safeguards remain effective when harmful meaning emerges jointly from images and text across different languages.",
    constructionDetail:
      "Multilingual prompts are paired with visual contexts and expert safety labels, including cases where either modality alone appears benign.",
    metrics: [
      { name: "Demo languages", value: "11", note: "Simulated display value" },
      { name: "Demo safe-response rate", value: "72.5%", note: "Simulated" },
      { name: "Demo adoption (30d)", value: "13 projects", note: "Simulated" },
    ],
    demo: true,
  },
  {
    id: "atbench",
    name: "ATBench",
    oneLine:
      "Safety · evaluates risk across complete agent trajectories, where final-answer checks miss unsafe intermediate tool actions.",
    area: "Safety & Trustworthiness",
    capabilities: ["Trajectory safety", "Tool-use diagnosis", "Long-horizon oversight"],
    topics: ["Agent safety", "Tool use", "Red teaming"],
    construction: "Hybrid",
    annotation: "Mixed",
    readiness: "Inspectable",
    firstSeen: "2026-06-18",
    adoption30d: 11,
    heat: 81,
    confidence: "Medium",
    links: {
      paper: "https://github.com/LiYu0524/ATbench",
      code: "https://github.com/LiYu0524/ATbench",
      data: "https://github.com/LiYu0524/ATbench/tree/main/data",
    },
    motivation:
      "Diagnose when and how long-horizon agents become unsafe, including harmful intermediate actions that do not appear in the final response.",
    constructionDetail:
      "Diverse tool-using trajectories combine scripted scenarios, model rollouts, and step-level safety annotations for evaluation and diagnosis.",
    metrics: [
      { name: "Demo trajectories", value: "6,800", note: "Simulated" },
      { name: "Demo unsafe-action recall", value: "83.1%", note: "Simulated" },
      { name: "Demo heat (30d)", value: "+37%", note: "Simulated" },
    ],
    demo: true,
  },
];

export const BENCHMARK_DATA_NOTICE =
  "Prototype demo data: trend, adoption, confidence, dates, and metric values are simulated and must not be cited as live benchmark statistics.";

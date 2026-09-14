# Benchmark taxonomy

Benchmark Radar keeps technical capability, application context, and artifact
type separate. They answer different questions and must not share one flat
`Domains` menu.

## Axis A — General AI capabilities

These describe what a model or system must do. A benchmark may have one to
three groups:

- Knowledge & Reasoning
- Mathematics & Formal Sciences
- Coding & Software Engineering
- Agents
- Tool Calling
- Computer Use
- Search & Retrieval
- Long Context & Memory
- Instruction Following & Structured Output
- Language & Communication
- Multimodal Perception
- Safety & Trustworthiness
- Systems & Efficiency
- Robotics & Embodied Intelligence

`General AI` is the UI umbrella for these groups, not an application-domain
leaf and never a synonym for “classification failed.” Agents, Tool Calling,
and Computer Use remain distinct even when one benchmark has more than one.

## Axis B — application domains

These describe where the evaluated work occurs. They are optional and may be
multi-valued:

- Health & Life Sciences
- Finance & Economics
- Legal & Public Sector
- Science & Research
- Cybersecurity
- Industrial & Engineering
- Transport & Logistics
- Consumer & Productivity
- Education
- Creative Industries & Media
- Robotics & Autonomous Systems

When no specific domain is supported, `applicationDomains` is empty and
`domainScope` records `general`, `cross-domain`, or `unspecified`. Mathematics,
Coding, Multimodal, and General AI are capabilities rather than downstream
application domains.

## Artifact role is not a domain

`reusable_benchmark`, `benchmarking_study`, `uses_existing_benchmarks`, and
`unclear` describe the artifact role. `Survey` is never a capability or
application domain. A survey or comparison paper enters the public Library
only when it separately releases a reusable evaluation artifact with a stable
task and scoring contract.

## Evidence and migration

The normalizer may safely map reviewed structured labels into the two axes. It
must not infer new scientific meaning from paper keywords. New or ambiguous
classification is produced by semantic source review and remains auditable.
Legacy `primaryDomain` is temporarily retained for Radar/Trends compatibility;
these legacy fields remain available for historical views. The Library navigation now uses the canonical research taxonomy described below.

This follows HELM's separation of scenario task/domain/metric and Hugging
Face's hierarchy of modality families and tasks. LLM Stats is used as a useful
coverage reference for Coding, Agents, Tool Calling, Long Context, Math, and
other practical filters, but its flat overlapping tag list is not copied.

References:

- Stanford HELM: https://crfm.stanford.edu/2022/11/17/helm.html
- Hugging Face Tasks: https://huggingface.co/tasks
- OpenML Tasks: https://docs.openml.org/concepts/tasks/
- LLM Stats Benchmarks: https://llm-stats.com/benchmarks


## Library research navigation v2

`pipeline/research_directions.py` generates `researchDirections`, evidence, facets,
classification review flags and `manifest.researchTaxonomy` together. The browser
must not merge, rename or infer record memberships. README links and counters use
the same manifest. Historical Radar/Trends capability/domain fields remain separate.

### Research themes

- **Self-Improvement & RSI**: evaluated improvement of AI/agents, retained learning,
  training/data/algorithm development and compute optimization. Includes AI R&D
  enabling tasks; category membership is not evidence that a recursive loop works.
- **AI for Science**: science-specific knowledge/reasoning, scientific computation,
  experiments, artifacts and discovery. Includes AI Scientist workflows. School or
  graduate science knowledge is a foundation task, not automatically a scientist workflow.

Themes may overlap with task capabilities. NatureBench can be both science and
coding; GENEB can be both science and data analysis. Ordinary software/office tasks
are not scientific work solely because the suite mentions an ML subtask. AI R&D in
a publisher name does not establish an improvement task. A self-evolving test set
is not a test of model self-improvement.

### Task capabilities and evidence

The existing agent, language/reasoning and perception/safety sections now have
explicit destinations for software engineering, data analysis, systems optimization,
cybersecurity, knowledge/QA, visual understanding, spatial reasoning and media
generation. These were previously absent or calculated without appearing in navigation.
The two Featured topics remain the only featured themes; other categories are grouped.

Classification uses the evaluated-task description (falling back to `oneLine`) and
explicit source tags. It does not inherit `area`, and it does not use a benchmark's
name as proof of its task. Regular-expression matches have word boundaries and
explicit morphology: `meteorological` is not `logical`. Theme membership requires
task-description evidence, not a broad imported topic tag. The evidence remains
metadata-based and provisional, rather than a claim of full-paper verification.

`researchFacets` preserves AI R&D tasks, explicit RSI wording, scientific workflows
and science knowledge as distinct evidence. `explicit-rsi` means the description
uses that wording, not that the system demonstrates unlimited recursive improvement.
`researchClassification.reviewFlags` marks unsupported directions, source-tag-only
assignments and theme mentions that need scope review. Unclassified records remain
in All benchmarks and full-text search. They must not be forced into General AI.

### Compatibility and reproducibility

- `direction=ai-scientist` → `direction=ai-for-science`.
- `direction=ai-r-d` → `direction=self-improvement-rsi` (the broader theme, not the old bucket).
- `domain=Science & Research` and `topic=Self-Evolution` redirect to canonical themes.
- Science's duplicate application-field option is omitted from navigation.
- Search aliases include AI Scientist, AI4Science, AI R&D and RSI, while memberships
  and counts always come from canonical records.

To rerun the audit, save an old library snapshot, regenerate the current index,
then run `pipeline/audit_research_taxonomy.py --before <old-library.json> --output <audit-dir>`.
The audit records every membership delta, task description, source link, evidence
and review flag. See [the v2 audit](audits/taxonomy-v2/report.md).

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
new Library UI reads `capabilityGroups`, `applicationDomains`, and
`domainScope`.

This follows HELM's separation of scenario task/domain/metric and Hugging
Face's hierarchy of modality families and tasks. LLM Stats is used as a useful
coverage reference for Coding, Agents, Tool Calling, Long Context, Math, and
other practical filters, but its flat overlapping tag list is not copied.

References:

- Stanford HELM: https://crfm.stanford.edu/2022/11/17/helm.html
- Hugging Face Tasks: https://huggingface.co/tasks
- OpenML Tasks: https://docs.openml.org/concepts/tasks/
- LLM Stats Benchmarks: https://llm-stats.com/benchmarks

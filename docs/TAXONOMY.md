# Taxonomy and classification evidence

Benchmark Radar does not copy the arXiv subject tree into the product UI. It
uses three orthogonal axes:

1. `area` — the technical object or interaction paradigm being evaluated;
2. `applicationDomains` — the real-world content or deployment context;
3. `capabilities` — the finer-grained skills or risks being measured.

This follows HELM's separation of task, domain, language, and metrics rather
than collapsing them into one category. Hugging Face likewise keeps task
metadata and dataset modality/context as separate fields. arXiv categories are
retained as source metadata and discovery inputs, not treated as product
categories.

Primary references:

- Stanford CRFM, HELM: https://crfm.stanford.edu/2022/11/17/helm.html
- Hugging Face Dataset Cards: https://huggingface.co/docs/hub/en/datasets-cards
- arXiv Category Taxonomy: https://arxiv.org/category_taxonomy
- MLCommons benchmark principles: https://mlcommons.org/benchmarks/

## Stable areas

- Language & Knowledge
- Vision & 3D
- Multimodal
- Speech & Audio
- Code & Software
- Agents & Tool Use
- Robotics & Embodied AI
- Science & Engineering
- Safety & Trustworthiness
- Systems & Efficiency

## Application-domain rules

The primary domain must be supported by the benchmark title, its explicit
identity/evaluation-target sentence, or reviewed primary-source metadata. A
single incidental mention elsewhere in an abstract cannot set the primary
domain. Full-text matches may propose secondary candidates for review only.

`General AI` is the conservative primary domain for explicitly cross-domain
benchmarks. `Mobile & Personal Computing` covers phone/desktop personal-agent
environments; financial data inside one app does not make the benchmark a
Finance benchmark.

Evidence priority is:

1. reviewed override with primary-source URL and date;
2. explicit scope from the benchmark's official paper/project;
3. deterministic match in the benchmark identity/evaluation-target sentence;
4. semantic-review proposal;
5. `General AI` when evidence is insufficient.

Every automatic classification should retain its method, matched evidence,
and confidence. Classification changes are versioned and must be replayed over
the active Radar window.

## Benchmark role

- `reusable_benchmark`: intended as a reusable evaluation target;
- `diagnostic_benchmark`: a repeatable evaluation primarily created to expose
  a limitation or support a scientific claim;
- `benchmarking_study`: comparison/analysis without a reusable benchmark
  entity;
- `uses_existing_benchmarks`: reports results on existing benchmarks;
- `unclear`: insufficient evidence.

Only reusable benchmarks are eligible for automatic Radar publication.
Diagnostic benchmarks require independent adoption, unusually strong
field/age-normalized attention, or an explicit reviewed exception.
Institutional prestige is provenance, never an automatic inclusion feature.

## Regression examples

- FinanceBench / BigFinanceBench: Language & Knowledge area; Finance domain.
- iOSWorld: Agents & Tool Use area; Mobile & Personal Computing domain.
- EdgeBench: Agents & Tool Use area; General AI primary domain with reviewed
  cross-domain scope.

# Kimi K3.1 Pro update — 2026-10-24

Added Kimi K3.1 Pro (Moonshot AI), released October 24, 2026, using the
[official launch report](https://www.kimi.com/en/blog/kimi-k3-1-pro).
The [official research index](https://www.kimi.com/en/blog/) confirms the date.

The complete launch table has 47 benchmark rows. Its Kimi column becomes 48
numeric observations because ZeroBench's avg@5 and pass@5 are separate metrics.
The source table is embedded in the official page's server-rendered component
payload; the headline chart was also inspected to cross-check visible values.
No competitor columns are imported as provider self-reported evidence. The
Highspeed variant has no separately reported scores and receives no copied results.

## Protocol decisions

- Default settings are Max reasoning effort, temperature 1.0 and top-p 0.95;
  BrowseComp overrides top-p to 1.0 and retains its compaction and step budgets.
- HLE full-set results with and without tools remain separate from HLE-Diamond.
- BenchCAD keeps the 1,000-case Vision2Code subset and tool access explicit.
- ProgramBench's binary threshold of 95% is separate from the earlier row whose
  exact metric is unspecified.
- PostTrainBench v1.2 retains H20 hardware and the DeepSeek judge substitution.
- Agents' Last Exam v1.1 ALL (122 tasks) and CLI (86 tasks) remain separate from V1.
- GDP.pdf's no-tools strict pass rate (34.6) is separate from the Python-enabled
  task-macro rubric pass rate (85.7).
- ZeroBench retains no-tools avg@5 (29.8), no-tools pass@5 (39.0), and Python
  pass@5 (63.0) as three records.
- OSWorld v2.1's Kimi Agent result does not claim an unspecified partial or
  offline scoring mode; those existing rows stay separate.
- Elo ratings preserve the October 24 report snapshot. Artificial Analysis and
  Mercor results are identified as provider-republished leaderboard values.
- Business Operation uses 37.8 from the full benchmark table; the narrative
  graphic labels it 37. Its scale is unspecified, so it is a raw score with an
  automatic chart axis, not a percentage or a presumed 100-point maximum.
- Internal factuality results are lower-is-better stress-test error rates.
- ExploitBench preserves pass@5 capability scoring and its 300-turn budget;
  ExploitGym preserves six hours per task; xdev-bench-hard preserves pass@3
  and the final checkpoint after cyber data filtering.

Only existing explicitly selected Library IDs receive source references; internal
or unresolved benchmarks do not create new Library entities. This includes
linking specific release protocols to their known parent Library entries without
merging their Model Evals score rows. The lab review banner now derives its lab
names from reviewed sources, including Moonshot AI.

## Reproduction

`make update-model-evals` regenerates the embedded dataset and Library references.
`make test` and `make build` validate the data and static artifact. Source data is
in `data/model_eval_updates.json`; fetched page bodies are local ignored outputs.

Validation passed: all 317 tests, full `make build`, and browser verification of
Kimi's first-column placement, 48 score rows, official report link and the
Terminal-Bench 4.0 score drawer. Build-only attention/trend changes were excluded
from this scoped update.

# Category taxonomy v5

Live since 2026-10-05. Replaces the 38 regex-derived Library/Trends categories
(`library-categories-v2`).

## Why

The old public categories came from keyword rules on short descriptions. The
membership was noisy and several categories said nothing specific:

| Problem (v2) | Evidence |
|---|---|
| Duplicate categories | Vision-Language Models and Visual Understanding had **identical** top-10 (100% overlap); Safety & Alignment / Cybersecurity and AI Research Agents / Systems & Performance were at 50%. |
| Wrong members at the top | Cybersecurity's top-10 included LiveCodeBench and FrontierMath; Mathematical Reasoning was led by MMLU-Pro; Speech & Audio was led by WMT24++ (translation); Terminal-Bench sat in Data Analysis and Agent Safety. |
| Missing obvious members | SWE-bench Verified was not in Coding Agents. |
| Vague umbrellas | Vision-Language Models (565 records), Programming & Software Engineering (338), Content Generation, Data Analysis Agents (27, rarely used). |

## Design rules

1. A category is a term people search for and that frontier-lab model cards or
   benchmark companies use as a section heading (e.g. *Agentic coding*,
   *Computer use*, *Knowledge work*, *Agentic search*, *Long context*).
2. Each category has **anchors**: benchmarks that labs report or benchmark
   companies publish. The build fails if an anchor is missing from the Library
   or sits outside its category (`audit_library_categories.py`).
3. **Merge rule:** two categories whose top-10 benchmarks overlap ≥50% go to a
   merge review; ≥70% merge by default. Top-10 = members ranked by number of
   frontier labs reporting the benchmark, then report count, catalog model
   count, GitHub stars. Re-run with `python3 pipeline/category_overlap.py -v`; `pipeline/tests/test_taxonomy_v5.py` fails the build if any pair reaches 50%.
4. One **primary** category plus at most two **secondary** ones per benchmark.
   Counts and Trends use primary + secondary; the awesome list uses primary only.
5. No umbrella categories: Vision-Language Models, Data Analysis, "Coding" and
   Content Generation are retired and redirect to specific categories.

## Categories (36, in 9 groups)

| Group | Categories |
|---|---|
| Reasoning & Knowledge | Math Reasoning · Knowledge & Expert QA · Abstract Reasoning & Planning · Factuality & Hallucination · Forecasting & Time Series |
| Coding & AI R&D | Agentic Coding & SWE · Code Generation · AI R&D & ML Engineering |
| Agents | Tool Use & Function Calling · Computer Use & GUI Agents · Deep Research & Search · Professional & Enterprise Work · Agent Memory & Personalization · Agent Skills & Self-Improvement · Multi-Agent & Games |
| Language & Interaction | Long Context · Instruction Following · Chat, Writing & Preference · Multilingual & Translation |
| Multimodal | Image & Visual Reasoning · Document Understanding & OCR · Video Understanding · Spatial & 3D Reasoning · Speech & Audio · Image & Video Generation |
| Embodied & Physical | Robotics & Embodied AI · World Models & Physical Understanding |
| Safety & Security | Safety & Alignment · Agent Security & Prompt Injection · Cybersecurity & CTF · AI-Content Detection & Forensics |
| Application domains | Science · Health & Medicine · Finance & Law · Engineering & Hardware Design |
| Indexes & Suites | Composite Indexes |

Definitions, anchors, keyword fallbacks and the 34 legacy redirects live in
`data/taxonomy_v5.json`. Every old `direction=` URL still resolves.

## How memberships were produced

1. **Anchor list.** A research pass collected 52 organisations (19 frontier labs,
   18 benchmark companies such as Scale AI SEAL, Epoch AI, METR, Vals AI,
   Artificial Analysis, Mercor, Surge, Sierra, LMArena, ARC Prize, plus academic
   and non-profit groups) and 421 benchmark entries, with model-card section
   headings (`docs/audits/taxonomy-v5/benchmark_orgs.json`).
2. **Coverage.** 302 unique names were matched against the Library: 206 present,
   64 were naming variants (stored as aliases in `data/library_aliases.json`,
   e.g. "SWE Verified", "AIME25", "HLE w/ tool"), and 20 were genuinely missing
   and added with a verified primary-source URL (Remote Labor Index, HCAST,
   METR Time Horizon, RE-Bench, PRBench, APEX, AstaBench, Vibe Code Bench…).
   A second pass added 22 widely used benchmarks that were also missing
   (VBench, T2I-CompBench, GEdit-Bench, AgentDojo, ChemBench, RoboCasa,
   EmbodiedBench, BALROG, ForecastBench, VerilogEval, MemoryAgentBench…).
   All additions go through `supplemental_catalog_records.json`
   (catalog `anchor-review`), so future catalog syncs keep them.
3. **Classification.** Every visible record (3,175) was read by an LLM reviewer
   (name + description) against `docs/audits/taxonomy-v5/classifier_brief.md`,
   in 9 batches. Rows placed in "other" or marked low-confidence were re-reviewed
   after the taxonomy gained Forecasting, Content Detection, Engineering Design
   and Composite Indexes. Result: `data/taxonomy_v5_assignments.json`
   (1,871 high / 1,130 medium / 174 low confidence; 108 reviewed as outside
   every category).
4. **New daily records** first get a provisional keyword match from
   `data/taxonomy_v5.json`. The daily job then runs `pipeline/classify_categories.py`,
   which asks the editorial model (same brief) to place them and records validated
   answers as `model-review-daily`. Records whose review fails stay provisional and
   are counted in `manifest.libraryTaxonomy.provisionalCount`.
5. **Legacy fields** (`applicationDomains`, `capabilityGroups`, `researchTopics`,
   `researchDirections`) remain in the data as evidence but are no longer displayed.
   Old `?direction=`, `?domain=` and `?capability=` links redirect to v5 categories
   (`retired` and `legacyFilters` in `data/taxonomy_v5.json`).

## Result

| | v2 | v5 |
|---|---|---|
| Public categories | 38 | 36 |
| Pairs with top-10 overlap ≥50% | 3 (max 100%) | 0 (max 30%) |
| Records outside every category | 596 by keyword baseline | 108, each reviewed |
| Lab-reported benchmarks missing from Library | 20 (+22 widely used) | 0 |

The two remaining 30% pairs are Spatial & 3D ↔ Robotics (ERQA, EmbSpatialBench,
RefSpatialBench) and Image & Video Generation ↔ World Models (world-simulation
video benchmarks). Both are below the review threshold and the categories mean
different things.

## Build your own direction (Trends)

Typing a keyword on Trends creates a direction: every Library benchmark whose
name, aliases or description matches is gathered into one entry with release and
star trends. Matching uses word boundaries and stems ("chemistry" also finds
chemical/chemist; "PDE" does not match "update"); commas join alternatives.
The entry suggests related terms that are specific to its benchmarks. Enter or
*Keep as direction* pins it under *Your directions* in the visitor's browser;
`#d=term,term` links share it. Undated benchmarks are listed but not charted.
Code: `web/trends/directions.js` (pure functions) and `web/trends/trends.js`.
Counting which directions people create, to promote popular ones, needs a
server-side store and is not built yet.

## Signals and growth

`pipeline/audit_signal_coverage.py` writes `data/signal_coverage.json` on every
generate. `pipeline/enrich_library_metrics.py --all-visible --max 500` refreshes
the stalest records daily (HF paper upvotes and author-linked repository, GitHub
stars, HF dataset downloads). `pipeline/signal_history.py` stores each value when
it changes (`data/signal_history.json`) and annotates `growth` per record:
stars gained in the last 1/3/6 months and per stage (0-1, 1-3, 3-6 months) from
GitHub star events; HF upvotes and downloads from stored snapshots, reported only
once the history reaches back to the start of the window. The Library's
*Growing* sort ranks by stars gained in 3 months, one entry per repository.

## Open items

- 174 low-confidence and 108 "other" assignments are candidates for source review
  (largest "other" clusters: typed decision systems, education/tutoring, remote
  sensing, classic text classification, agent serving performance).
- Composite Indexes (13) is small by design; it keeps aggregate scores out of the
  capability categories rather than tracking a research direction.
- Records added by the daily job after this snapshot are keyword-provisional until
  the next review pass.

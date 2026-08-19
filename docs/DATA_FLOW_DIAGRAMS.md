# Benchmark Radar diagrams

Each diagram answers one question. The overview is for any reader; the other
three belong in technical documentation rather than the public product UI.

## 1. Thirty-second product overview

**Question:** how does research become a record in Benchmark Radar?

```mermaid
flowchart LR
  A["Official research sources"] --> B["Find possible new Benchmarks"]
  B --> C["Two independent evidence checks"]
  C -->|"new and reusable"| D["Confirmed Benchmark record"]
  C -->|"evidence incomplete"| E["Wait for a source update"]
  D --> F["Attention and adoption evidence"]
  F --> G["Radar · Library · Trends"]
```

The system follows primary sources, checks whether the work defines a new and
reusable evaluation target, and only then exposes it to the product views.

## 2. Storage and public-view boundary

**Question:** what is durable evidence, what is generated, and what reaches the
browser?

```mermaid
flowchart TB
  S["Official sources"] --> C[("Candidate evidence<br/>and decision history")]
  C -->|"admitted"| K[("Confirmed recent Benchmarks")]
  K --> O[("Dated attention and<br/>publication observations")]
  L[("Established Benchmark<br/>source Library")] --> V["Generate public views"]
  K --> V
  O --> V
  X["External benchmark directories"] -. "weekly / manual discovery" .-> L
  V --> R["Radar"]
  V --> B["Library"]
  V --> T["Trends"]
  R --> P["Static GitHub Pages"]
  B --> P
  T --> P
  P --> LS["Saved IDs<br/>browser only"]
```

The frontend reads only compact generated views. It never receives candidate
abstracts, AI responses, credentials, or internal decision history. Saved items
are stable IDs in browser localStorage and never mutate the dataset.

| Logical data | Current files | Authority |
|---|---|---|
| Candidate evidence and decisions | `data/review_queue.json`, `data/ai_review_status.json` | Durable admission state |
| Confirmed recent Benchmarks | `data/benchmarks.json` | Canonical Radar data |
| Established source Library | `data/library_seed_records.json`, `data/library_records.json` | Source-backed classic records |
| Dated observations | `data/metrics/`, `data/publication/` | Historical evidence snapshots |
| Source-backed corrections | `data/curated_overrides.json` | Durable correction layer |
| Radar, Library and Trends views | `data/benchmarks_index.json`, `data/library_index.json`, `data/domain_trends.json` | Rebuildable derived data |
| Website artifact | `_site/` | Rebuildable deployment output |

## 3. Candidate lifecycle

**Question:** why does a candidate not immediately appear on the homepage?

```mermaid
stateDiagram-v2
  [*] --> Discovered
  Discovered --> Pending: source evidence found
  Pending --> Admitted: new and reusable
  Pending --> Deferred: evidence incomplete or checks disagree
  Pending --> Excluded: existing Benchmark use or comparison study
  Pending --> Retry: provider temporarily unavailable
  Retry --> Pending: next daily run
  Deferred --> Pending: source or policy changed
  Excluded --> Pending: source materially changed
  Admitted --> Published
  Admitted --> Deferred: legacy migration conflict
```

Deferred is not rejected. Infrastructure failures automatically retry. Excluded
items retain an audit receipt, and one automated diagnostic judgment cannot
delete an already-public legacy record.

## 4. One daily update

**Question:** what happens at the fixed update time, and what happens on failure?

```mermaid
sequenceDiagram
  participant S as "14:17 Brisbane schedule"
  participant U as "Daily updater"
  participant O as "Official sources"
  participant A as "Evidence checks"
  participant G as "Git data"
  participant W as "Public website"

  S->>U: update the previous calendar day
  U->>O: fetch source records and public signals
  U->>G: upsert durable candidates
  U->>A: check pending candidates twice
  A-->>U: admitted / deferred / excluded
  U->>U: reconcile, enrich, generate and validate
  alt all validation passes
    U->>G: commit one complete snapshot
    G->>W: deploy once
  else a critical stage fails
    U-->>W: keep the previous valid website
  end
```

The scheduled run is fixed at 14:17 Australia/Brisbane and indexes the previous
Brisbane calendar day. A manual run may provide an explicit date.

## Common diagram types and where to use them

| Diagram | What it normally explains | Use here |
|---|---|---|
| System context | Product boundary and main actors | Repository overview |
| Data-flow / lineage | Sources, storage, transformations and outputs | Architecture documentation |
| State machine | Lifecycle and decision outcomes | Admission methodology |
| Sequence diagram | Runtime order, retries and failure behavior | Operations documentation |
| Entity-relationship diagram | Family, release, protocol and observation schema | Add later to data-schema documentation |
| Deployment diagram | Services, networks and credential boundaries | Add only if infrastructure grows beyond Actions + Pages |
| Funnel / Sankey | Candidate counts lost at each stage | Later monitoring view, only with real counts |

Do not put all four diagrams on the product homepage. The public UI should stay
focused on Benchmarks; these diagrams are repository documentation.

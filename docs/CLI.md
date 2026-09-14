# Benchmark Reader: Agent contract

Run from a repository checkout with Python 3.10+; no packages or credentials required.

```sh
./benchmark-reader search gpqa
./benchmark-reader search --domain science --limit 10
./benchmark-reader show lib_gpqa_diamond
./benchmark-reader show usage:model-reports:frontier_challenge --limit 10 --offset 0
```

## Choose your output

| Reader | Command | Output |
|---|---|---|
| Human at a terminal | `./benchmark-reader search "scientific coding"` | Readable result list |
| Human saving text | `./benchmark-reader hot --window 7d --text` | Same readable list when redirected |
| Agent or script | `./benchmark-reader search "scientific coding" --json` | One structured JSON response |

Default output is text on an interactive terminal and JSON otherwise, preserving existing piped consumers. Always specify `--json` in Agent instructions; use `--text` to force a readable preview. Both flags work before or after the command and cannot be combined. `--help` always prints ordinary help text and exits successfully.

Text lists show name, stable ID, release date, attention and a short description/match explanation. Follow the printed ID with `show` to inspect evidence. Text detail summarizes usage and source links; JSON contains full observations and protocols. Unmeasured attention displays as `unmeasured`; an identity without linked usage evidence is described as unknown, not zero real-world adoption.

Text errors go to stderr; JSON errors stay in the structured stdout envelope. Exit codes and JSON schema 1.2 are unchanged. Successful JSON output contains no banners or progress prose.

## Pick a command

| Intent | Command |
|---|---|
| Find a known name or explore a topic | `search QUERY` |
| Inspect evidence for a selected result | `show ID` |
| Read one day's releases | `daily --date YYYY-MM-DD` |
| Read one day's first discoveries | `daily --date YYYY-MM-DD --basis discovered` |
| Browse a week / three months of hot releases | `hot --window 7d` / `hot --window 90d` |

Agent workflow: search → read IDs and coverage → show selected IDs → cite evidence. Use `data.nextOffset` for list pagination and `data.pagination.nextOffset` for show observation pagination; repeat the same filters with the new offset. Empty results are successful, not tool failures. Never interpret attention as relevance, adoption or scientific quality.

Command details:

- `search [query] [--domain LABEL]`: Weighted BM25 retrieval across names, aliases, descriptions and domain labels. Default `--sort relevance` puts exact primary names first, exact aliases next, then BM25 relevance. Explicit alternatives: `--sort usage|attention|newest`. Domain filters match stored labels, not a complete scientific taxonomy. Default limit 20.
- `show ID_OR_EXACT_NAME`: identity, usage summary, evidence and source documents. Prefer an ID returned by search. Ambiguous names return candidates instead of choosing a version. Default observation limit 50.

All commands accept `--limit 1..100`, `--offset N` and `--data-dir PATH`. Follow `nextOffset` until null. Show pagination applies only to observations; summary counts cover all observations. Commands perform no network requests. In JSON mode standard output is one JSON object (except `--help`), with `schemaVersion`, `ok`, `data`, `coverage`, `error`. Exit codes: 0 success, 1 invalid database, 2 invalid arguments/ambiguous identity, 3 identity not found. Empty search is successful. Agents should inspect `ok`, preserve source IDs and cite returned evidence URLs.

## Daily updates and hot lists

```sh
./benchmark-reader daily
./benchmark-reader daily --date 2026-09-13
./benchmark-reader daily --date 2026-09-13 --basis discovered
./benchmark-reader hot --window 7d
./benchmark-reader hot --window 90d --domain biology --limit 10
./benchmark-reader hot "protein folding" --window 30d
./benchmark-reader search "scientific coding" --sort attention
./benchmark-reader search --domain chemistry --sort attention
```

- `daily [query]`: published records released on `--date`; `--basis discovered` selects first-seen date instead. This is not the date of a metric refresh. No automatic previous-day fill in the CLI: an empty date returns zero results.
- `hot [query] --window 7d|30d|90d`: records released in that many calendar days, inclusive of the end date. Thus 7d ending September 13 means September 7–13. Three months is defined as 90 days. `--as-of` sets the release-range end, **not a historical score snapshot**.

Default end date is the index's `latestSourceDate`, falling back to `dataAsOf`. Both dates are returned so agents can detect stale discovery coverage. Results use only public/display-eligible records. Daily/hot require only `benchmarks_index.json`; search/show also require the library and usage database.

All attention sorting uses the existing **90-day population's current attention score**, including weekly subsets, so incomparable window scores are never mixed. This measures current public attention, not weekly growth, adoption, quality or projected influence. Raw signals, their `asOf`, score confidence and coverage are returned. Missing scores remain null and sort last; ties use name then ID. Older library records may have no current score. Search is all-library; hot is release-window restricted. Domain matching uses stored labels (e.g. biology, chemistry, physics, coding), not inferred subject membership. A broad `science` label does not automatically union all scientific disciplines.

Responses use schema version `1.2`; pagination and error codes remain unchanged. These queries read the local checkout's latest available data; use `git pull` to obtain repository updates. No silent network refresh occurs.

## Search relevance and Agent workflow

Search uses an in-memory SQLite FTS5 index (English Porter stemming), with BM25 field weights name=10, aliases=8, description=3, domains=1. It is rebuilt from the current checkout per invocation; no service or API key is needed. Python must include SQLite FTS5; unavailable support returns `invalid_database` with a diagnostic instead of silently reverting to substring matching.

```sh
./benchmark-reader search SciCode
./benchmark-reader search "科学编程"
./benchmark-reader search "paper reproduction" --expand "research replication"
./benchmark-reader search "scientific programming" --expand "research code" --sort relevance
```

Any query concept may match. Partial matches remain candidates; multiple terms are no longer a strict AND condition. Common science/coding/reproduction terms and a small Chinese dictionary expand explicitly. This is **not general Chinese or semantic search**. Agents should translate unsupported concepts, try two or three focused English queries, and preserve the original intent. `--expand TEXT` may be repeated; expansions appear in `data.search.expandedTerms`. Generated query terms are never evidence that a benchmark has a capability.

Each result includes `relevance.exactMatch`, a BM25 `score`, `matchedFields`, and an indexed-text `snippet` with matches in brackets. BM25 scores are query-relative ordering signals, not probabilities, confidence or influence scores. An exact identity can have a low numeric BM25 score and still sort first. Name-only spelling suggestions appear in `data.search.suggestions` when no candidates match; they are not substituted silently. Variants including HumanEval+ and GPQA Diamond retain their separate identities. Cross-source records are not forcibly merged; agents must not add their usage counts together without reconciling evidence.

The domain filter remains based on recorded labels. A description suggesting biological content is not silently converted into a biology tag. When a strict domain query returns too little, agents should retry the keywords without the domain filter and inspect evidence. Explicit attention sorting reorders the lexical candidate set; partial matches may rank highly, so use relevance first for open-ended research. Daily/hot retain their simpler keyword filters; use search for exploratory research.

Suggested Agent procedure: interpret the request → search a few focused expressions → inspect returned matches → call `show` for selected IDs → assess source evidence and freshness. For saturation, novelty or adoption, retrieve the actual evidence; retrieval relevance alone cannot answer these questions. Returning fewer results or unknown is preferable to inventing missing evidence.

A reproducible developer pilot is stored in `data/search_eval/queries.json`; run `python3 pipeline/evaluate_search.py` to compare with the old AND-substring/usage-ranked search. Its 50 queries include 25 identity lookups, 20 research-intent prompts and five synthetic no-answer strings. `report.json` retains all misses. This is a regression pilot, not independent human relevance annotation: the intent metric checks whether one selected example appears in the first ten, and does not establish precision or full recall. Several benchmarks may be relevant beyond that example.

## Meaning of the results

| Field | Meaning |
|---|---|
| `reportedLabCount` / `reportedLabs` | Distinct upstream organization labels in model/system cards, technical reports or release posts. An upstream-curated report mention is evidence of reporting, not independently confirmed adoption. |
| `reportCount` | Distinct matching report documents; multiple score rows in one report count once. |
| `scoreObservationCount` | Published score rows, including external evaluations; **not execution count**. `observationsByKind` separates evidence kinds. |
| `instruments` | Version/subset/protocol labels actually supplied in score evidence, not a complete version history. Read individual observation protocols and source IDs. |
| `firstReported`, `lastReported` | Earliest/latest publication or revision date among matching registered reports. Not first/last real-world use. |
| `actualRunCount`, `influenceScore` | Null: the snapshot cannot establish private run counts or a validated influence score. |
| `lifecycle`, `saturation` | Unknown. Missing recent reports do not establish retirement; incompatible scores cannot establish saturation. |

The imported snapshot's latest registered vendor report is **2026-08-28**. This is coverage of the collection, not a claim of complete coverage through that date. Zero means no matching evidence in this snapshot. Report counts are more useful here than popularity gates; there is no star/download admission threshold for this import.

## Alignment and database

`data/usage/` retains 1,284 source-qualified benchmark records and 12,929 score observations. These are **not 1,284 unique benchmark families**. Records join to the existing library only when normalized primary name and an identity URL both agree, with exactly one local candidate. Shared paper URLs or aliases alone never merge records: GPQA full and GPQA Diamond must remain separate. Unmapped records remain searchable under `usage:SOURCE:ID`. Third-party leaderboards do not increase vendor report counts.

The existing `data/library_index.json` receives a separate `reportedUsage` field for aligned records. Existing popularity scores and recent-release feeds retain their original semantics. Future library generation reattaches usage from the imported database. Cross-source score rows are retained separately and never averaged or deduplicated as equivalent experimental runs. Units/directions are upstream catalog metadata, not a normalization guarantee.

Files: `benchmarks.json` (identities), `documents.json` (provenance), `mentions.jsonl` (benchmark/document edges), `observations.jsonl` (reported measurements), `manifest.json` (archive fingerprint and coverage).

To refresh deliberately, download and inspect the upstream release, then run:

```sh
python3 pipeline/import_usage.py /path/to/benchmark-radar-data.zip
python3 pipeline/generate_library_index.py
make test
make build
```

Archive SHA-256 is the dataset version. Reimporting the same archive produces identical files; updated archives may have different coverage and require review. This initial import has 447 vendor-report mention edges; all-source document references total 1,621.

## Attribution

Facts imported from [Koutian Wu and contributors' Benchmark Radar](https://github.com/ktwu01/benchmark-radar), using its [CLI data release](https://github.com/ktwu01/benchmark-radar/releases/tag/cli-data). The manifest records the exact archive SHA-256 and source URL; each measurement retains upstream identity and available provenance. Original report/evaluation sources retain their own rights. Upstream software is MIT; its [content license](https://github.com/ktwu01/benchmark-radar/blob/main/LICENSE-CONTENT.md) specifies CC BY-NC-SA 4.0 for original editorial content. This import excludes editorial descriptions and judgments and does not relicense underlying content.

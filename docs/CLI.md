# Benchmark Reader: Agent contract

Run from a repository checkout with Python 3.10+; no packages or credentials required.

```sh
./benchmark-reader search gpqa
./benchmark-reader search --domain science --limit 10
./benchmark-reader show lib_gpqa_diamond
./benchmark-reader show usage:model-reports:frontier_challenge --limit 10 --offset 0
```

Only two commands:

- `search [query] [--domain LABEL]`: normalized name/alias substring search. Domain filters match available labels, not a complete scientific taxonomy. Results sort by observed reporting-organization count, then name and ID. Default limit 20.
- `show ID_OR_EXACT_NAME`: identity, usage summary, evidence and source documents. Prefer an ID returned by search. Ambiguous names return candidates instead of choosing a version. Default observation limit 50.

Both accept `--limit 1..100`, `--offset N` and `--data-dir PATH`. Follow `nextOffset` until null. Show pagination applies only to observations; summary counts cover all observations. Commands perform no network requests. Standard output is one JSON object (except `--help`), with `schemaVersion`, `ok`, `data`, `coverage`, `error`. Exit codes: 0 success, 1 invalid database, 2 invalid arguments/ambiguous identity, 3 identity not found. Empty search is successful. Agents should inspect `ok`, preserve source IDs and cite returned evidence URLs.

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

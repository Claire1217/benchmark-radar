# Full-Library release-date audit — 2026-09-16

Status: partially resolved; unverified dates remain. No deployment performed.

## Result

| Measure | Before | After |
|---|---:|---:|
| Library records | 2870 | 2870 |
| Missing exact release day | 1067 | 788 |
| Completely unknown | 1031 | 782 |
| Year only | 36 | 6 |

279 records now have an evidence-backed day. Every accepted entry retains its original-source URL and evidence basis. This is not a claim that all missing dates have been filled. See [applied records](applied.json), [unresolved records](remaining.json), and [receipt](receipt.json).

## Trends and cross-page impact

- Release counts now use all eligible, dated Library families, including historical entries absent from the recent Radar feed. Existing family IDs deduplicate variants; dates are the earliest supported day among family members. Unknown and year-only records stay in Library but do not contribute invented release dates.
- Default release window is one year, ending 2026-09-12; the adjacent preceding year is used for comparison. 1-, 3-, 6-, and 12-month selections use the same indexed-catalog scope. Monthly chart bins follow the selected window. The earliest known record is not treated as proof of exhaustive historical coverage.
- Canonical release evidence is applied after reviewed additions, so newly curated entries can receive dates and dates survive regeneration. The same Library supplies Trends and Library sorting. Radar retains its recent-discovery role; older entries are not injected as fresh Radar discoveries.
- Research-topic membership is unchanged: True. Changes affect dated ordering, inclusion in historical release counts, and period comparisons; GitHub star events are not modified.
- Star mode also supports selecting a year; the existing three-month default is retained. Its year chart has 52 weekly bins. Removed growth-summary and methodology UI blocks stay removed.

## Evidence procedure and limitations

Initial inspection covered all 1067 missing/day-imprecise records and their existing source links and cached primary pages. Retrieved 236 linked/candidate original arXiv metadata pages, then searched 926 remaining records by name for original papers. Official-source follow-up currently contains 800 record queries. Name matches alone do not prove identity: candidate title, task and version were checked before accepting dates.

A paper's first arXiv submission date is recorded as `paper-v1`, not silently represented as a known dataset download date. An earlier verified official announcement takes precedence (e.g. FACTS Grounding, 2024-12-17; Terminal-Bench, 2025-05-19). Repository creation, catalog ingestion, web-page update, and model-report publication dates are not used as substitutes.

Examples of rejected matches: AIME agent papers do not date the mathematics contest; image-retrieval DUDE papers do not date the document benchmark; the infrared IF-Bench paper does not date instruction-following IFBench. The latter was resolved from its actual introductory paper. Versions and provider-specific score rows need their own evidence rather than automatic inheritance from the parent.

Remaining dates require source/identity review. Catalog score slices, provider mirrors, internal evaluations, annual competitions and sparse entries are present among the unresolved records. Not finding a date in this search does not establish that none exists.

**Historical discovery is uneven.** Longer-window counts describe the benchmarks currently indexed with dates; a sharp rise can reflect greater recent catalog coverage. Completing dates for existing entries does not recover benchmarks absent from the Library, and backfills may revise previous counts. These counts must not be described as a census of worldwide benchmark publication.

## Validation

190 repository tests passed. Data and static-site validation and cross-surface taxonomy checks passed. Additional UI execution checks covered the default year, all eight mode/window combinations, sorting, missing histories, and absence of removed detail blocks. No claim of browser visual verification is made.

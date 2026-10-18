# Homepage performance — 2026-10-18

The previous homepage waited for both an 8 MB Radar view and a 15 MB Library
view before rendering content. It then built 3,413 Library cards even while that
section was hidden, and performed repeated record lookups during startup.

The build now writes the real latest-feed cards and their matching bootstrap
data directly into HTML. The browser immediately binds the controls using that
small snapshot. Neither full JSON file is requested for an ordinary first visit.
History and Library are loaded on demand, with pointer/focus intent warming,
shared in-flight requests, and retry controls that preserve the existing feed.

Library initially renders 60 cards and adds more on request. Filtering and search
operate over the complete loaded catalog. Attention scores are cached per record,
and search renders are coalesced to animation frames. Nested evidence and polling
histories are excluded from website projections; complete public downloads remain
available. The same browser card renderer produces build-time and interactive
content, avoiding a separate drifting template.

| Check | Before | After |
|---|---:|---:|
| First-visit resources, uncompressed file accounting | 24.11 MB | approximately 0.20 MB |
| Full JSON requests needed for first screen | 2 | 0 |
| Initial DOM elements, local browser check | 58,332 | 638 |
| Hidden Library result cards on homepage | 3,413 | 0 |
| Initial Library result cards when opened | 3,413 | 60 |

The resource comparison includes HTML, application scripts, stylesheets, the mark
and shared assets. It measures bytes before HTTP compression, not production
transfer bytes or load-time seconds. A local server delaying data responses by
eight seconds showed an initially empty feed in the previous build; the updated
build already displayed 24 real cards and requested no data files. Exact network
conditions and CDN latency in production were not measured.

## Validation

- `make build` passed canonical data, JavaScript syntax, taxonomy, cross-surface
  checks, static assembly and validation.
- Three new tests cover immediate content, stalled and failed requests, retries,
  concurrent request deduplication, whole-day bootstrap selection, paging and
  searching beyond the first result page.
- Existing view-equivalence tests still compare rendered cards, category counts,
  sorting and search against the complete source data.
- Browser checks confirmed 30-day navigation, 60 → 120 results, full-catalog
  OSWorld search, and save → Saved → unsave. Test saves were removed afterward.
- Release validation: all 300 tests passed after syncing the October 18 daily data.
- Removed the ambiguous `Riemann-bench` alias from the tools-only record: a separate
  canonical `RiemannBench` record now exists. Dataset and tool-setting records remain.

The initial performance measurements above precede the October 18 daily-data sync.
The synced catalog contains 3,417 visible Library entries. Production verification
is performed after the GitHub Pages release.

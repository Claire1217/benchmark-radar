# GitHub linkage and star coverage audit

All 651 records from the date audit were scanned using their linked pages, source-reviewed date evidence, task reviews and Hugging Face paper associations. Candidates are not confirmed links. No public repository is assumed for proprietary evaluations.

```json
{
  "reviewedEntries": 651,
  "linkedEntries": 415,
  "uniqueLinkedRepositories": 279,
  "entriesWithFreshStars": 415,
  "entriesWithCompleteHistory": 302,
  "uniqueHistoryRepositories": 213,
  "uniqueRepositoriesInTrends": 60,
  "unlinkedEntries": 236,
  "discoveryStatus": {
    "not-found": 142,
    "linked": 415,
    "candidates": 94
  },
  "allSiteHistory": {
    "repositories": 894,
    "complete": 882,
    "statuses": {
      "complete": 882,
      "http-404": 12
    }
  },
  "trendsCoverage": {
    "libraryRecords": 2710,
    "storedLibraryRecords": 2964,
    "displayEligibleRecords": 2710,
    "datedFamilies": 2133,
    "undatedFamilies": 493,
    "releaseScope": "all-library-dated-families",
    "completeHistories": 245,
    "requestedHistories": 894
  }
}
```

## Scope

Repository stars are deduplicated within each research topic, including GitHub-reported redirects. Shared frameworks and agent/tool repositories remain linked for navigation, but their stars are excluded from benchmark attention. Different benchmark versions can share a family repository; its stars are not version-specific. Some mapped repositories have no current featured topic or belong to reference-only records, so complete histories do not all appear in Trends.

## Refresh

Current counters and complete weekly histories refresh in the existing daily-index workflow. Failed counter attempts retain prior observations with stale status. History failures do not invalidate a separately verified code link. Unknown histories are not zero growth.

## Limits

This is a source-link recovery pass, not a claim that every entry has a public GitHub repository. Unlinked entries and unresolved candidate lists remain in all-651.json for follow-up. Name-matching source links are reviewed separately from repository-wide versus subset scope.

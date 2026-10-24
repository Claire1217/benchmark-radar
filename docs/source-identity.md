# Source identity and update ownership

A namespaced provider ID identifies a source observation. A benchmark name, shared
paper URL, shared repository or catalog spelling does not establish that two
benchmark entities are the same. Discovery deduplication now uses source keys;
explicit Library identity decisions remain responsible for cross-source merges.
A paper may still contain several benchmarks: this change does not invent their
individual entities or tracks without scoped evidence.

For a repeated source, newer evidence refreshes review context, source metadata and
links. Earlier observations cannot overwrite newer source text. Canonical IDs,
first-public release dates and first-seen dates remain stable. A revised public
source enters the semantic review queue with `reviewReason: source-changed`; it
cannot bypass that review through deterministic auto-admission.

`refresh_source_observations.py` visits up to 60 known public sources per run, within
a 180-second request-launch budget. It revisits original arXiv, GitHub, Hugging Face
and OpenReview sources independently of publication date. It records the last check,
source revision and evidence hash in `data/source_refresh_state.json`; unavailable
sources retain their previous evidence. With the current catalog, a full cycle takes
weeks, not hours. The daily limit and remaining stale sources must be considered when
interpreting freshness. An already started provider request can exceed the budget.

The first unchanged observation establishes a baseline without enqueueing thousands
of records merely because full abstract text was absent from their compact public
copy. A newer provider revision queues review immediately. Subsequent content-hash
changes also queue review, even if revision metadata is unchanged. Candidates are
persisted before hashes are advanced, making interruption replay-safe.

Catalog synchronization preserves existing IDs through exact source references.
Fresh same-name rows from distinct providers receive separate source-derived IDs;
renaming a known source retains its old ID. First-release dates do not become update
dates. Stale source observations cannot replace fresher catalog text.

`data/catalog_identity_bindings.json` freezes the 70 existing name-derived public
bindings as **legacy compatibility, needs source review**. This avoids breaking old
IDs, overlays and links while removing dynamic name matching for new catalog rows.
It is not a new scientific identity review. Reconciliation in #18 must review these
bindings, ADB duplicates and HWE homonyms before any actual merge/split migration.

New editorial decisions are stored under namespaced `bySourceKey` keys. Existing
`bySourceId` decisions remain available through a provider-aware compatibility read;
new decisions take precedence. Ambiguous raw IDs cannot join across providers.
Model request IDs, failure holds and candidate-to-decision joins use the same keys.
This is an additive storage migration, not a rewrite of historical review evidence.

# Shared evidence search

Library, CLI search and custom Trends directions use `web/search.js` and the
policy generated from `data/evidence_concepts.json`. No query-specific chip-design
patch or second Python matching implementation is maintained. The CLI requires
Node.js 18+ and uses a persistent local JSON-lines process; it never executes query
text as code or a shell command.

Exact IDs, names and aliases rank first, preserving plus/version distinctions.
Controlled concepts include parent relationships; short acronyms use token
boundaries. A short concept alias can resolve a query but does not infer a domain
from source text by itself (for example EDA can mean exploratory data analysis). Multiword queries require all concepts (70% for four or more groups).
A unique one-edit/transposition correction is allowed only within the controlled
vocabulary, for alphabetic terms of at least five letters. Arbitrary benchmark
names are not rewritten. Expansion changes retrieval, never entity identity or
source evidence. Explicit alternatives are OR queries.

The searchable document includes source text and evidence concepts independently
of card copy. Provisional facets are useful retrieval hints, not verified domain
membership. Library shows source quotations and task-subset scope when supplied.
A domain match does not establish that a frontier model ran those questions.
Legacy navigation labels alone do not supply evidence for a concept match.

Library defaults to relevance when typing or opening a query link. Users can
explicitly choose attention, release date or growth. Growth retains its existing
one-entry-per-repository filter. Saved keyword directions use the same matcher.

Trends stores the individual searchable members of each visible family and
matches them separately before family aggregation. It cannot create a match by
joining one version's chemistry evidence with another version's planning evidence.
Trends intentionally excludes aggregate indices, and its date charts exclude
unknown/partial dates and future releases. Family totals are not Library entry
counts. Neither claims exhaustive historical coverage.

Before this change, the lazy-loaded Trends search payload was 951,381 raw /
249,130 gzip bytes. Member evidence raises it to 2,685,306 raw / 580,820 gzip bytes.
The regression budget is 3 MB raw / 700 KB gzip; first-screen Radar does not load
this payload. Library's compact evidence document was introduced separately.

Verification uses the actual browser predicate, the Python/Node adapter and
Trends member matching on the committed Library snapshot, plus negative acronym,
hidden-record, exact-variant, subset-evidence and cross-member false-positive
fixtures. Existing UI routing, keyboard selection and compact/full rendering
checks remain in the full suite. These are regression tests, not a statistically
representative benchmark recall study.

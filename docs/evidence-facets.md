# Evidence-backed facets and classification refresh

The 36 navigation categories remain stable. A separate versioned registry defines
56 domain, task, capability and environment concepts, including a domain hierarchy
for engineering → electronics → chip design. Facets have no two-secondary-category
limit. Each fact stores the supporting text, URL, evidence basis and scope:
`benchmark`, `task-subset`, or `unspecified`.

Deterministic extraction is term-grounded, provisional evidence organization. It
is not a quality score or a guarantee that a mention covers every evaluated task.
Primary-source excerpts and editorial descriptions retain distinct provenance.
For example, AgenticBBO-Bench's explicit cross-domain statement supports a chip-design
**task subset**, not a claim that the entire benchmark is dedicated to chips.
Publisher prestige, model-report mentions and inherited family categories do not
supply facet evidence. Missing data origin, private-data access and evaluation
coverage are not inferred from these domain/task labels.

Discovery retains full bounded review text in `data/source_evidence.json` before
candidate persistence, so admission no longer discards all source context. Known
source refresh uses the same archive. Earlier source revisions cannot overwrite
newer evidence. Older records without archived text retain their existing excerpts;
this change does not pretend that missing historical abstracts were fetched.

Classification receives evidence text and URLs as well as card copy. The input
fingerprint covers source text, the concept registry, taxonomy and policy version,
not attention counters. Changed model-reviewed inputs are requeued; anchor/human
reviews remain protected. The daily job reviews at most 80 records in batches of
eight. Existing navigation assignments remain available while review is pending.
Model answers must quote supplied evidence with its URL. Unsupported category
answers and facet quotes are rejected. Editorial paraphrases remain marked editorial
even after model review. Source-matched quotations are necessary evidence, not proof
that the model's semantic judgment is infallible.

Generation writes the full facet receipt and classification evidence to the public
Library index, and a separate `searchDocument` into the compact website view. Search
can therefore use domain evidence without forcing card prose to list every task.
The shared retrieval implementation is delivered separately under #17.

Migration checks preserve all 4,104 current IDs, release dates and visibility flags.
Before historical source backfill, 11 visible records receive chip-design evidence
from existing primary excerpts or editorial descriptions. Existing hidden entries
stay hidden, and legacy duplicate identities remain separate pending #18 review.

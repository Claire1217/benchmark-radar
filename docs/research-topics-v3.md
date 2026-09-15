# Research topics v3

The 20 featured discovery topics prioritize language-model agents. They are not an exhaustive ontology. Original research directions and source labels remain available in Library and in its payload. Each record also receives description-derived task, capability, environment, modality and protocol facets, with excerpts and source links where available.

## Scope and evidence

All 2,870 records were regenerated from the current main-branch data; identities, descriptions, release dates, links and source reviews were preserved. The rules incorporate 203 targeted description reviews, bound to description hashes so later source edits cannot silently inherit stale decisions. This is not a full-paper review of every record. Catalog-only entries remain explicitly unverified. No featured topic can mean either outside the selected research topics or insufficient evidence; it does not mean the benchmark is invalid. See data/research_topic_audit.json for counts and the source-review queue.

## Taxonomy boundaries

Coding Agents includes coding-associated terminal execution; Terminal is also a detailed environment. Computer Use includes grounding, which remains a separate detailed task. OCR and document understanding are separated from generic visual tasks. A self-evolving benchmark is not automatically an evaluation of self-improving agents. Multi-agent data construction is not a collaboration target. Language/GUI world simulators are not physical world-model evaluations.

## Comparable attention

Trends uses the current topic mapping for every historical point, deduplicates repository identities, and retains the existing covered-history and concentration caveats. Shared toolkit repositories aider-ai/aider and allenai/olmocr are excluded from benchmark attention aggregation: their total stars cannot be attributed to the hosted benchmark. Topics overlap; summed topic totals are not sitewide totals. This release does not claim new star-history coverage.

## Regeneration and validation

The public and Library generators call pipeline/research_topics.py; normal daily generation therefore retains this taxonomy. make build regenerates the Trends payload. Legacy taxonomy remains available for old filters. Regression tests cover evidence/membership parity, repeatability, preserved labels, target-versus-construction mistakes and repository scope.

# Public Library categories

The Library uses one generated registry, `manifest.libraryTaxonomy`, and one per-record membership list, `libraryCategories`. Sidebar entries, result chips, type-search suggestions, filters, counts and URL routing read this registry. The client must not append internal legacy directions to it.

## Category scope

- **Agent research** identifies evaluated agent workflows.
- **Related research** identifies the other featured research topics shared with Trends.
- **General capabilities** includes broad benchmark tasks, which can contain narrower agent topics.
- **Specific tasks** contains explicitly narrower evaluations such as GUI grounding.
- **Application fields** remains a separate domain filter. Actual field URLs, including `domain=Science & Research`, retain their field scope after reload; legacy redirects apply only to retired labels. Field headings use the selected field name.

A benchmark can belong to more than one category. Counts represent distinct visible benchmark entries within a category, not mutually exclusive portions of the entire Library. Each parent includes its child entries exactly once.

`AI for Science` (`scientific-agents`) identifies agent-driven scientific investigations. The broader `Scientific Knowledge & Tasks` also includes science questions, scientific chart interpretation and prediction tasks. These are distinct scopes and must not share the same display name. The former `ai-for-science` URL keeps its broad scope; it does not redirect to `scientific-agents` after reload. Searching “AI for Science” selects the agent-research category; the broader category has its own name and search aliases.

Other explicit parent relationships cover programming/coding agents, data analysis/data-analysis agents, systems/efficient inference, and content/image-video generation. Deprecated duplicate navigation entries for audio, embodied AI, deep research and self-improvement resolve to the corresponding canonical research topic. Original legacy classifications remain available in the dataset for provenance and review, without becoming a second competing navigation taxonomy.

## Verification

`pipeline/audit_library_categories.py` runs during both generation and builds. It validates unique category IDs and display names, alias targets, parent inclusion, membership regeneration, counts and agreement with featured topics and the public index. The generated receipt is `data/library_category_audit.json`.

`pipeline/tests/test_library_categories.py` exercises every real public category against the client: sidebar counts, click results, URL reload results, legacy links and exact category-name search. This prevents the previous bug where a button counted a legacy label but a refreshed URL selected a narrower topic.

These checks establish structural consistency. They do not imply that every inherited benchmark label has undergone full-paper review. Source-review status remains separate from category membership.

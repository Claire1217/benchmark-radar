# Unified research topics and Trends

## One classification contract

`data/research_topics.json` defines the 20 discovery topics. `pipeline/research_topics.py` assigns memberships and detailed task facets using indexed descriptions and hash-bound reviews. The same canonical Library membership feeds Radar, Library, README, the Awesome catalogue and both Trends data formats. Legacy filters remain available as additional benchmark categories, not competing featured topics.

`make generate` regenerates the records, documentation and Trends. `make build` runs cross-surface validation before creating the production artifact. Scheduled workflows commit the generated audit and Trends payload together with the indexes. Changes to source descriptions invalidate old reviews rather than inheriting stale decisions.

## Corrections in this release

- Correct plural and inflected forms such as self-improving, world models, memory policies and robotics.
- Terminal access alone does not establish a coding task. Terminal-Bench retains Coding Agents because its description explicitly includes software/developer tasks. Healthcare and obfuscated-tool terminal tasks do not inherit Coding Agents.
- Physical/video world-model evaluation is separate from textual execution simulators. Machine-learning research that happens to include robotics is not itself robot control.
- Display-only scores and aggregate indexes are marked as reference records; they do not create featured benchmark topics.
- Detailed tasks cover the long tail beyond the selected discovery topics. Outside a featured topic is distinct from insufficient evidence.
- Search accepts reordered words and plural forms, and indexes native task facets in both the browser and CLI.

## Source review scope

2,146 distinct public source URLs were retrieved for the flagged corpus. A machine-readable, per-record access receipt is stored in `data/topic_source_audit.json`. It records HTTP outcome, content hash and a benchmark-name mention check. These checks are not claims of full-paper semantic verification. Selected changed memberships were additionally reviewed against the task description; source pages for analyst, code-review and research-agent examples were inspected.

The complete corpus is accounted for in `data/research_topic_audit.json`: supported topic membership, task outside the featured vocabulary, reference-only index, or task needing evidence. Catalog claims remain provisional. An unavailable page does not establish that a benchmark is invalid; a successful download does not establish that its classification is correct. Unknown release dates and unavailable repositories are not invented to complete a chart.

## Trends display and interpretation

The new production page is based on the independent drivers preview, rebuilt from current canonical data. All 20 topics are visible at once. Columns show release counts and recorded-star growth, with clickable headers for sorting. The detail panel shows repository contributions, new-repository share, releases and source-linked model-report use. Both columns extend with the page.

Defaults are one calendar month of releases versus the preceding month, and three calendar months of attention. One, three and six months are selectable. Release coverage currently cannot support two complete three-month windows; incomplete periods are shown explicitly and their comparisons are null. The release chart uses eight two-week bins on individually scaled axes.

GitHub's history endpoint returns star-creation events, not net change in current stargazers. The rate is period events divided by cumulative recorded events before the period. A zero baseline has no percentage. Small baselines can yield large percentages. The attention detail line is cumulative new events over 13 weeks, not a reconstruction of net stargazer stock. API calendar boundaries are not guaranteed to align with UTC. See [GitHub's endpoint documentation](https://docs.github.com/en/rest/activity/starring#get-repository-star-history).

Complete, continuous repository histories are required. Repositories are deduplicated within topics; topics can overlap and their totals cannot be added into a sitewide total. Shared hosting/toolkit repositories are excluded from benchmark-only attention. Source-reviewed scope corrections include DataMind, MetaVideoAgent, PRM-as-a-Judge and CDAF, in addition to aider and olmOCR; these corrections also apply to Radar/Library attention and GitHub documentation. Repository concentration and the share coming from newly created repositories are visible, so one popular project is not presented as broad field growth. Report use is a current evidence snapshot, not an adoption-growth series.

The separation of discovery topics from native tasks is consistent with [Hugging Face dataset cards](https://huggingface.co/docs/hub/datasets-cards), which retain task metadata alongside other dataset attributes.

# Release source recovery — 2026-09-16

## Findings

The earlier unknown count reflected incomplete source resolution, not evidence that release dates were unavailable. Of the 788 unresolved entries, 351 linked to llm-stats, 104 to Harbor, and 37 to modelbeats. Many names are abbreviations, score settings, language splits, or provider wrappers.

The previous title-prefix matcher missed papers whose title differs from the benchmark name (DUDE, CountBench, ANLI). The official-candidate pass also discarded Hugging Face and arXiv links because it treated them as a separate pass, but did not fully resolve onward links. This run follows the source chain instead.

## Result

- Inspected all 788 unresolved entries; fetched/analyzed 2,148 candidate pages and followed original-source links. Full local evidence: `outputs/release-source-recovery/recovered-sources.json`.
- Found paper candidates for 275 entries. Candidate discovery is not acceptance: unrelated papers and versions remain unconfirmed.
- Resolved 137 additional entries: 136 to a day and 1 to a month.
- 90 resolutions are explicitly dates of the underlying dataset for score/split entries, not independent release dates of those wrappers.
- 651 entries remain without a verified month/day. This is unfinished identity/date review, not a claim that dates do not exist.

## Examples

| Entry | Verified date | Source |
|---|---|---|
| AlpacaEval | 2023-06-08 | [Author publication page](https://yanndubs.github.io/publication/AlpacaEval) |
| DUDE | 2023-05-15 | [Original document-understanding paper](https://arxiv.org/abs/2305.08455) |
| GeneBench | 2026-04-23 | [bioRxiv v1](https://www.biorxiv.org/content/10.64898/2026.04.22.720113v1) |
| AA Briefcase | 2026-06-18 | [Original official announcement](https://artificialanalysis.ai/articles/aa-briefcase) |
| FrontierSWE | 2026-04, month precision | [Original launch post](https://www.frontierswe.com/blog/v1) |
| BigCodeBench-Hard | 2024-07-18 | [Official README release news](https://github.com/bigcode-project/bigcodebench) |

GeneBench's DOI contains April 22 but the actual posted date is April 23. BigCodeBench-Hard has a distinct launch from the full dataset. These illustrate why identifier dates and parent dates are not sufficient.

## Extraction workflow

1. Start from canonical entry links and previous search results; fetch the entry's source page locally.
2. Follow original GitHub, HF, paper, and project links. Use expanded task descriptions to resolve abbreviated and ambiguous names.
3. Extract original-paper citation dates, official announcement dates and README release news. Retain source URLs, precision, and source hashes where fetched.
4. Review identity, task, and version. GitHub repository creation and HF mirror upload are not silently substituted for original dataset release. Third-party leaderboard published_time is not a dataset date.
5. Save approved evidence in the canonical release-date registry, then regenerate Library and Trends together.

Month-only dates are now supported and displayed as YYYY-MM in Library. The internal first-of-month sort key is never displayed as an exact day. Trends currently uses rolling windows ending mid-month, so month-only evidence remains excluded from exact release counts pending calendar-bin treatment. No exact day is fabricated.

Explicit underlying-dataset dates display as “Dataset published” in Library and do not independently create new benchmark-family releases in Trends. Taxonomy and GitHub star data are unchanged.

## Validation and remaining work

191 tests passed, including month precision and exclusion of date-imprecise/score-wrapper entries from independent release counts. Static-site build and cross-surface checks passed. Not deployed.

The remaining queue needs further identity review, original release/commit content inspection, and disambiguation of private/provider benchmarks. ADE-Bench's original GitHub repository was found, but an exact benchmark first-release date remains unverified. A repository found is a successful source recovery even when date extraction still needs review.

[Reviewed evidence](reviewed.json) · [Remaining source queue](remaining.json) · [Receipt](receipt.json)

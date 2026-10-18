# Model Evals update — 2026-10-18

Reviewed OpenAI, Anthropic and DeepSeek releases after the existing September
Model Evals snapshot. Added seven named releases, 77 numeric observations and
five verified evaluation disclosures without transcribed absolute scores.
Twelve numeric observations are the September DeepSeek model's comparison
column in its provider's October card; they remain attached to that older model.

| Provider | Release | Model date | Primary evidence |
|---|---|---|---|
| OpenAI | GPT-6.1 Sol | 2026-09-29 | [Release](https://openai.com/index/introducing-gpt-6-1-sol/) · [System card](https://deploymentsafety.openai.com/gpt-6-1-sol) |
| OpenAI | GPT-6 Sol / GPT-6 Luna | 2026-09-22 | [Release](https://openai.com/index/introducing-gpt-6-sol-and-luna/) |
| Anthropic | Claude Opus 5.5 | 2026-09-22 | [Release and benchmark table](https://www.anthropic.com/claude-opus-5-5) |
| Anthropic | Claude Sonnet 5.5 | 2026-09-28 | [Release and footnotes](https://www.anthropic.com/claude-sonnet-5-5) |
| Anthropic | Claude Haiku 5.5 | 2026-10-07 | [Release and benchmark table](https://www.anthropic.com/claude-haiku-5-5) |
| DeepSeek | DeepSeek-V4.1-Flash-1017 | 2026-10-17 | [Model card](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) · [Release](https://api-docs.deepseek.com/news/news261017/) |

The review transcribes published results; it does not rerun model evaluations.
The durable input is `data/model_eval_updates.json`. Its sources retain publication
and retrieval dates. Each result has its own source URL and evaluation setting,
visible in the score drawer. Existing imported records retain their dates and
verification limits. This is a targeted three-provider update, not a refresh of
every lab in the catalog.

## Evaluation distinctions

- HLE full-set, text-only, with-tools and no-tools results use distinct rows.
  DeepSeek October reports 42.6 on the full no-tools set and 44.0 on text-only.
- Terminal-Bench 4.0 stays separate from other releases and from Science 0.1.
  DeepSeek's terminal result uses Claude Code; DeepSWE uses Mini-SWE-V2.
- OSWorld 2.0 v2026.08.08 offline partial reward, OSWorld 2.1 partial, and the
  Haiku table's OSWorld 2.1 offline subset stay separate. The Haiku launch table
  does not establish whether its offline result is strict or partial reward.
- Sonnet's FrontierCode results retain both Max (46.2) and Xhigh (52.1).
  Opus retains its headline Max score (54.4) and the separately stated Medium
  score (54.6). Headline order is preserved, rather than selecting the maximum.
- Sonnet's GDPval-AA rating changes from 1844 in its launch report to 1840 in
  the October 7 reference column. AA-Briefcase changes from 1811 to 1824.
  Both observations remain inspectable; the later snapshot is displayed.
- Opus production safeguard fallbacks are documented per model. AutomationBench
  was evaluated by Zapier without fallback models, with interventions as failures.
- OpenAI HealthBench values are explicitly length-adjusted Table 7 scores.
  Raw values and response lengths in parentheses are not misread as extra scores.
- OpenAI's GPT-6.1 release confirms DeepSWE, GDP.pdf, AutomationBench, OSWorld
  and Terminal-Bench Science coverage. Absolute chart scores could not be
  transcribed in this review. These five cells read `Reported`, carry source
  links, and are excluded from numerical charts. Relative improvements are not
  used to infer an absolute score.
- Challenging factuality and broken-search error rates are lower-is-better and
  explicitly labeled as not representative of typical production traffic.
- No competitor scores from another lab's table are recorded as self-reported
  evidence. Anthropic's Sonnet reference column and DeepSeek's September-model
  reference column are same-provider evidence.

Only explicit reviewed Library IDs receive report links. Unresolved variants
(including Apex Bench v1.1) stay unlinked. Existing Library entities are not
created or merged by this update. Imported company averages for the three labs
are not extended across the new protocols or missing values.

## Reproduction

Run `make update-model-evals`, then `make test` and `make build`.
The update is idempotent and makes no network requests. Future evidence can be
added to the durable overlay without replacing the historical inline dataset.

The original local repository was found at `/Users/claire/Documents/benchmark-radar`.
Its iCloud placeholder files initially blocked reads. A clean working copy was
prepared in the current chat directory from the public repository, based on
commit `41c4ce0`, while preserving the original directory.

## Validation result

- `make build`: passed, including canonical data, JavaScript syntax, taxonomy,
  cross-surface checks and the generated static site.
- Six Model Evals regression tests: passed, including idempotence, source URLs,
  missing values, exact subsets, explicit Library links and latest Elo snapshots.
- Release validation after the October 18 daily-data sync: all 300 tests passed.
  The ambiguous Riemann-bench alias was removed from the tools-only record because
  it conflicts with the separate canonical RiemannBench entry.
- Browser checks confirmed all seven releases appear in date order; Sonnet
  retains both Elo report snapshots, DeepSeek keeps the two HLE subsets separate,
  and score drawers expose the source URLs and evaluation settings.

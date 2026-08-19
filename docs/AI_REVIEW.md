# Automatic DeepSeek candidate promotion

The deterministic indexer sends ambiguous papers to `data/review_queue.json`.
`pipeline/review_candidates_with_deepseek.py` then sends those candidates to
DeepSeek and
automatically produces one of three outcomes:

- `promoted`: added to canonical data only after every code gate passes;
- `deferred`: insufficient confidence, critic disagreement, or API failure;
- `rejected`: a high-confidence non-release classification.

There is no human approval step. A DeepSeek classifier supplies semantic
classification, an exact benchmark name, and one exact source quote. A second,
independent DeepSeek critic re-reads the source and must return the same verdict,
relation, role, name, and quote while explicitly confirming that the quote
supports the claim. The model cannot supply canonical
URLs, dates, popularity, venue claims, or IDs.

## Deterministic promotion gates

Automatic promotion requires all of the following:

1. a schema-valid `benchmark_release` / `reusable_benchmark` decision;
2. confidence of at least `0.95`;
3. an exact contiguous source quote containing the exact benchmark identity;
4. independent classifier/critic agreement at the same confidence threshold;
5. safe HTTPS URLs already supported by the indexed source text;
6. a canonical arXiv source identity;
7. no source, benchmark-family, or generated-ID duplicate; and
8. the ordinary canonical record schema validator.

Keyword rules, regex scores, candidate relation, and reason codes are used only
for recall and queue priority. They never approve, reject, or veto a semantic
decision. Code verifies only locked response fields, ID coverage, exact
quote/name substrings, source-backed URLs and dates, duplicates, and canonical
schema validity. Duplicates are checked against both Radar and the established
Library.

Failure of any gate is a defer, never a partial promotion. A fingerprinted
ledger in `data/ai_review_status.json` makes all outcomes auditable, stores the
canonical promoted record as a persistent overlay, and avoids repeated
classification of unchanged candidates. Daily or same-date replays reapply
that overlay; a missing canonical promoted record is automatically restored.
`--retry-deferred` is an
explicit automated retry, not a human review path.

## DeepSeek configuration

The pipeline calls DeepSeek's official OpenAI-compatible
`POST https://api.deepseek.com/chat/completions` endpoint directly. It uses JSON
mode, high-effort thinking, and accepts only `finish_reason=stop`; the returned
JSON is then checked against the repository schema. There are no tools, agent
runtime, or workspace access. Configuration is read only from environment
variables:

```sh
export DEEPSEEK_API_KEY='...'
export DEEPSEEK_MODEL='deepseek-v4-pro' # optional; this is the default
python3 pipeline/review_candidates_with_deepseek.py --limit 48
```

Never place credentials in arguments, repository files, prompts, logs, or
generated data. Any credential pasted into chat should be treated as exposed
and rotated; it must not be reused here.

The GitHub workflow stores the credential only as the
`DEEPSEEK_API_KEY` Actions secret. It is scoped solely to the direct request
step, so checkout, validation, and git never receive it. `DEEPSEEK_MODEL` is an
optional repository variable and defaults to `deepseek-v4-pro`.

When the key is absent, classification exits successfully without changing
data. HTTP 429/500/503 and empty responses receive bounded retries; client and
authentication errors are not retried. A classifier or critic failure records
the affected candidate as deferred and cannot alter the last-known-good
canonical snapshot.

Deterministic regex and scores never publish new arXiv records. They only assign
candidate priority in the persistent queue. DeepSeek plus every hard gate is the
sole promotion path for new arXiv candidates; curated records and the persistent
promotion overlay are the only exceptions.

To enqueue the current 90-day corpus for a no-deletion replay after configuring
a fresh key, run the resumable backfill and then the automatic reviewer:

```sh
python3 pipeline/backfill_index.py --start-date 2026-05-21 --end-date 2026-08-18 --resume
python3 pipeline/review_candidates_with_deepseek.py --limit 96
```

Until that replay is run, existing canonical records remain available as
last-known-good legacy data; this migration never uses a key pasted into chat.

## Automation boundary

The workflow runs after a successful Daily benchmark index and may also be
started manually with a bounded candidate limit. After classification it
rebuilds all derived data, runs the full tests and static-site validation, and
commits only if the repository has valid gated changes. DeepSeek output is
never published directly to the website.

The Daily, AI promotion, and Pages workflows share one non-cancelling
concurrency lock, preventing a data writer or deployment from observing a
half-finished predecessor.

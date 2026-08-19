# Automatic DeepSeek candidate promotion

The deterministic indexer sends ambiguous papers to `data/review_queue.json`.
`pipeline/review_candidates_with_deepseek.py` then sends those candidates to
DeepSeek and
automatically produces one of three outcomes:

- `promoted`: added to canonical data only after every code gate passes;
- `deferred`: insufficient confidence, critic disagreement, or API failure;
- `rejected`: a high-confidence non-release classification.
- `rejected_excluded`: a confirmed diagnostic benchmark retained only in the
  audit ledger, never in Radar, Library, or Trends.

There is no human approval step. A DeepSeek classifier supplies semantic
classification, an exact benchmark name, and one exact source quote. A second,
independent DeepSeek critic re-reads the source and must return the same verdict,
relation, role, and name while explicitly confirming its own exact source quote
supports the claim. The model cannot supply canonical
URLs, dates, popularity, venue claims, or IDs.

Both stages also return locked reason signals: whether a third party can run
the artifact, whether it defines a stable task/metric/protocol, whether public
artifacts are evidenced, and whether its intended use is repeatable third-party
comparison or support for a paper claim. A `diagnostic_benchmark` supports a
specific claim or method without a stable external comparison protocol. Even
with a famous institution or high attention, it is automatically excluded from
all public benchmark and trend datasets when both stages agree; disagreement is
deferred. Signal objects are retained independently for audit and need not be
byte-identical; the agreed semantic role controls inclusion, avoiding needless
defers when one stage says `null` and the other says `false` for a secondary
signal.

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
export DEEPSEEK_MODEL='deepseek-v4-flash' # optional; this is the default
python3 pipeline/review_candidates_with_deepseek.py --limit 48
```

Never place credentials in arguments, repository files, prompts, logs, or
generated data. Any credential pasted into chat should be treated as exposed
and rotated; it must not be reused here.

The GitHub workflow stores the credential only as the
`DEEPSEEK_API_KEY` Actions secret. It is scoped solely to the direct request
step, so checkout, validation, and git never receive it. `DEEPSEEK_MODEL` is an
optional repository variable and defaults to `deepseek-v4-flash`, the economical
daily-review model.

When the key is absent, classification exits successfully without changing
data. HTTP 429/500/503 and empty responses receive bounded retries; client and
authentication errors are not retried. A classifier or critic transport/schema
failure records the affected candidate as `pending_provider_retry`, so the next
daily run retries it automatically and cannot alter the last-known-good
canonical snapshot. Genuine semantic uncertainty remains `deferred`.

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

Classification is an internal stage of the single Daily workflow, immediately
after candidate discovery and before metrics or public views are generated.
The workflow commits only after all derived data and the static site validate;
DeepSeek output is never published directly. Pages listens only to the completed
Daily workflow, so users never see an intermediate pre-classification snapshot.
Full unit tests remain in CI; Daily performs production data and static artifact
validation.

## Safe local test plan

No API key is required for the semantic regression suite:

```sh
python3 -m unittest pipeline.tests.test_deepseek_gold -v
python3 pipeline/review_candidates_with_deepseek.py --dry-run --limit 12
```

`pipeline/tests/fixtures/deepseek_semantic_gold.json` contains 12 offline cases
covering reusable and diagnostic benchmarks, existing-benchmark use,
benchmarking studies, aggregates, dataset-only releases, dataset-plus-benchmark
releases, and a complete protocol without public code. Tests feed the gold
classifier and critic JSON through the same schema and promotion gates used in
automation. Dry-run validates local inputs and request construction but makes no
network request. Never use a credential copied from chat for a live comparison.

The two-pass design is deliberate: one classifier plus an independent critic is
the minimum useful check against a single semantic mistake. The default batch
size is 8 and the workflow limit is 48, so a full run makes at most six
classifier calls and six critic calls; unclear batches do not need critic work.
Eight keeps thinking plus structured JSON comfortably below the output cap and
limits how many candidates defer if one batch fails; the small extra request
overhead is preferable to 12-item truncation risk.
`deepseek-v4-flash` is the economical default. Keep these bounds until the gold
agreement rate, invalid-JSON rate, and diagnostic exclusion rate have enough
history to justify changing cost or batch size.

Requests cap generated tokens at 4,096. As checked against the official
[DeepSeek pricing page](https://api-docs.deepseek.com/quick_start/pricing/) on
2026-08-20, Flash costs USD $0.14 per million uncached input tokens and $0.28 per
million output tokens. The 12-case gold payload is approximately 4,200 input
tokens and 3,100 structured-output tokens across both passes, or roughly
$0.0015 before hidden thinking-token variation. A 48-candidate run should
normally remain well below one cent. If cost telemetry is added later, it
should use the API usage fields because actual reasoning tokens and prices can
change; credentials and source abstracts must never be logged with it.

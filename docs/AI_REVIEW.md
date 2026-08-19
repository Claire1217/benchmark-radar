# AI-assisted candidate review

The deterministic indexer is intentionally a high-recall first pass. Code is
good at repeatable source retrieval, dates, deduplication, and exact evidence
checks; it is not sufficient for the semantic distinction between “introduces
a new benchmark” and “evaluates a model on an existing benchmark.”

`pipeline/review_candidates_with_codex.py` adds that semantic layer. It sends
only candidate title, abstract, comments, and internal ID to Codex in small
batches. Each positive decision must include an exact source quote. The script
validates the quote and ID coverage, then writes `data/ai_reviews.json` in
**shadow-review** mode. It never publishes an AI decision into the canonical
database automatically.

## Secure provider configuration

Codex custom providers use the Responses API. The provider must therefore
offer a compatible `/v1/responses` endpoint; Chat Completions compatibility
alone is insufficient. Supply configuration through environment variables:

```sh
export BENCHMARK_LLM_API_KEY='...'
export BENCHMARK_LLM_BASE_URL='https://provider.example'
export BENCHMARK_LLM_MODEL='provider-model-id'
python3 pipeline/review_candidates_with_codex.py --limit 24
```

Never paste the key into a command argument, TOML file, prompt, issue, log, or
repository secret file. For GitHub Actions, use an Actions secret named
`BENCHMARK_LLM_API_KEY` and repository variables for the base URL and model.

## Manual GitHub Actions run

The `AI candidate review (shadow)` workflow is intentionally available only
through `workflow_dispatch`; it is not called by the daily index, pull requests,
or Pages deployment. Configure these repository settings before running it:

- Actions secret: `BENCHMARK_LLM_API_KEY`
- Actions variable: `BENCHMARK_LLM_BASE_URL`
- Actions variable: `BENCHMARK_LLM_MODEL`

Choose a bounded candidate limit in the Actions form. The job has read-only
repository permission, disables shell tracing around provider configuration,
and uploads `ai_reviews.json` as a 14-day artifact. It does not write the file
to `data/`, commit it, change `data/benchmarks.json`, or trigger deployment. A
human must download and inspect the artifact; promotion remains a separate,
evidence-checked operation.

Internally, the script launches `codex exec` with an ephemeral session,
read-only sandbox, no approvals, structured JSON output, and this provider
shape:

```toml
model_provider = "benchmark_proxy"

[model_providers.benchmark_proxy]
base_url = "https://provider.example/v1"
env_key = "BENCHMARK_LLM_API_KEY"
wire_api = "responses"
```

The `_type: newapi_channel_conn` object used by some chat clients is not a
Codex CLI configuration format. Its URL maps to `base_url`; its key must be
moved to the environment variable above rather than copied into Codex config.

## Promotion policy

AI review is evidence extraction, not authority. A candidate can be considered
for promotion only when:

1. the verdict is `benchmark_release`;
2. the relation is `introduces`, `extends`, or `aggregates`;
3. the evidence quote occurs exactly in the indexed source text; and
4. a deterministic validator passes the resulting canonical record.

The reviewer also separates reusable benchmarks from diagnostic benchmarks,
benchmarking studies, and papers that only use existing benchmarks. Diagnostic
benchmarks are not promoted by default: they require either independent use,
field/age-normalized high attention, or an explicit human-reviewed exception.
Author or institution prestige is recorded as provenance, not used as an
automatic inclusion rule.

Until a labeled false-positive/false-negative audit is available, decisions
remain in shadow mode or the human review queue. This keeps model drift or a
provider outage from silently changing the public index.

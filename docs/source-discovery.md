# Source discovery and recoverable coverage

Production configuration now includes every current CS category (40), all four
eess categories, and six statistics categories. `data/source_registry.json` records
the enabled set and explicit adjacent-domain pilot work. Categories are metadata
coverage, not admission labels. Mathematical/scientific categories remain declared
pilot work; this does not claim exhaustive coverage of every research domain.

The registry follows [arXiv's category taxonomy](https://arxiv.org/category_taxonomy).
The OAI mapping handles physics archives such as `cond-mat.mtrl-sci` and `quant-ph`
without assuming every category has a dot or shares its archive's group name.

`discover_benchmarks.py` persists `data/source_coverage.json` before requests. Work
is keyed by source, query/category scope and release window. A window is complete
only after the candidate queue is atomically persisted; its receipt contains a
queue hash. Later windows cannot erase earlier failed or pending windows. A crash
before completion replays the same work. Old run files without this contract remain
unknown; the ledger does not infer their completion.

Daily collection has a 600-second launch budget and an 80-window limit. One already
started request/retry may exceed the time budget. Unattempted work remains pending.
Failed scopes cool down for two hours; the other scopes continue. Recent completed
windows can be revisited after two hours to catch late announcements. Historical
backfills remain completed unless explicitly requeued. Receipts keep the last 20
attempt details and lifetime attempt count for each window.

GitHub search pages are traversed to `total_count`; `incomplete_results` and the
1,000-result API ceiling are failures, not success. Hugging Face follows Link
pagination until the requested creation day is exhausted. OpenReview follows
count/offset pagination and rejects early, repeated or capped pages. These adapters
still certify only their recorded benchmark-oriented queries; they do not cover
all platform artifacts. Created-date discovery is distinct from tracking updates to
known sources (#15). A GitHub README failure leaves its scope incomplete for retry.

The authoritative queue is no longer replaced by empty arXiv failure results, and
category replays never delete other pending sources. Ordinary daily discovery does
not rewrite the canonical publication file. Admission retains its own existing
thresholds and semantic gates.

Historical windows can be enqueued without a network request:

```sh
python pipeline/discover_benchmarks.py --start-date 2026-07-24 --date 2026-10-24 --sources arxiv --max-windows 0
```

The same command with a positive window budget drains the backlog, reusing completed
receipts. `--dry-run` fetches without writing any queue or ledger. This is not a
claim that the historical backfill has run; results belong in the migration report.

Rollback: restore the previous workflow/code/config through Git. Keep the ledger
as diagnostic evidence. Never infer candidate exclusion from an empty fetch, and
never delete valid records merely to roll back collection configuration.

## Read-only source probes (2026-10-24)

| Source case | Category / first-release day queried | Result |
| --- | --- | --- |
| [GateTruth](https://arxiv.org/abs/2608.12635) | cs.AR / 2026-08-12 | Found among 7 papers; recognition 1.0, introduces |
| [MobileJailBench](https://arxiv.org/abs/2610.23303) | cs.CR / 2026-10-16 | Found among 26 papers; recognition 1.0, introduces |
| [MUSES](https://arxiv.org/abs/2609.00313) | cs.IR / 2026-08-31 | Found among 28 papers; recognition 0.6, introduces |
| [SGAnalog](https://arxiv.org/abs/2610.03934) | cs.AR / 2026-10-02 | Not found among 6 papers; unresolved, not an exclusion |

These probes exercise live source collection and the production recognizer. They
do not publish records, establish exhaustive recall, or verify artifact quality.

## Correct date semantics and fair recovery

Issue #24 supersedes the initial OAI-backed probes above. OAI `from`/`until`
filter metadata modification dates, not submission dates; a later administrative
update can move an old submission outside that query. The authoritative
first-release path now uses Atom `submittedDate`, with no OAI fallback presented
as equivalent coverage. [arXiv documents this distinction](https://info.arxiv.org/help/oa/index.html#datestamps).

Coverage contract v2 and backfill checkpoint v3 invalidate older completion marks.
Malformed XML and transport failures remain retryable scope failures. Recent and
historical work alternate so a large backfill cannot consume every daily slot.
Requests are paced at three seconds. SGAnalog was subsequently retrieved by its
primary source ID; its initial negative OAI probe was not an exclusion decision.
See `docs/historical-reconciliation.md` for the applied migration and remaining debt.

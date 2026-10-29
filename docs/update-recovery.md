# Daily publication recovery

Discovery and attention are independent. The site reports committed discovery
coverage, actual attention observation time, source failures, and editorial review
status separately. A stale static page also recalculates discovery lag in the browser.

The October 2026 outage was triggered when a live catalog first listed LongMemEval.
Reviewed Library additions were inserted *after* catalog matching, creating two
same-named records. The anchor audit encountered the provisional catalog record
instead of the reviewed record. Reviewed additions now participate in identity
matching before catalog import; their IDs, evidence, and reviewed categories survive.
The audit remains mandatory.

## Publication contract

`data/update_status.json` starts from the last committed discovery report date.
A receipt is staged only when the matching multi-source run exists. Receipts and
data become durable together, after generation, validation, and a successful push.
Attention and editorial-only jobs cannot advance discovery coverage. Manual runs
out of order do not hide gaps: coverage advances only across consecutive receipts.

The scheduled daily workflow retries the oldest unpublished day, one day per run.
For outage recovery, dispatch **Daily benchmark index** with `catchup_days=7` (or 3)
and leave `date` empty. It collects up to that many missing days in chronological
order and reviews their combined candidate window. An explicit `date` replays one
day. Partial upstream failures are recorded separately; a published day is not a
claim that every upstream source or every candidate review succeeded.

## Failure evidence and alerts

Daily and editorial jobs upload a 14-day recovery artifact before generating public
views. Snapshot upload failures warn but do not block an otherwise valid publication;
validation failures still block publication. If validation fails, use its data and run logs to inspect completed work;
these artifacts are **unpublished snapshots**, not certified site data. Never copy
an artifact's receipt ledger into main without validating and publishing its data.
Same-day retries preserve collected candidates even when an upstream response is empty; only explicit promotion removes a queued source.
Normal scheduled recovery re-fetches the missing dates idempotently; artifacts
allow manual salvage of expensive reviews when needed.

**Check discovery publication freshness** runs twice daily, independently of
attention and Pages deployment. It fails when committed coverage is more than one
day behind the expected previous Brisbane calendar day, or when discovery coverage
is unknown. It does not create issues, send messages, or change notification settings;
GitHub's existing workflow notification settings apply. Use the workflow logs and
public freshness label to distinguish an upstream partial outage, publication
failure, and a healthy day with zero new benchmarks.

CI now exercises `make generate` as well as `make build`, and the regression suite
includes a new live catalog record colliding with a reviewed anchor, missing/invalid
receipts, out-of-order replays, bounded catch-up, and stale browser timestamps.

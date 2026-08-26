# Methodology

## Product goal

The site helps model developers and researchers find evaluation artifacts worth
tracking or running. It is not a catalog of every paper that uses the word
“benchmark”.

## Evidence check

Candidates may be discovered from arXiv, GitHub, Hugging Face, or OpenReview,
then checked against the available primary sources:

1. **Paper** — does it introduce a named evaluation artifact and explain what it
   tests?
2. **GitHub** — are code, evaluator, run instructions, or submission tools
   actually available?
3. **Hugging Face** — are the paper, dataset, model, or Space present and usable?
4. **OpenReview** — is there a public submission with sufficient evaluation
   evidence and a stable source URL?

Paper, repository, dataset, and OpenReview records are merged before review
when they share a source ID, official URL, or normalized benchmark family name.

Missing evidence is `unknown`, not `unavailable`.

## Benchmark type

Every reviewed record receives one type:

- `score_submission`: external teams can submit a model to a leaderboard, or
  run a public evaluator locally and obtain comparable scores.
- `viewpoint_probe`: the paper creates a slice, transformation, stress test, or
  diagnostic mainly to demonstrate a finding, without a clear ongoing model
  submission or external evaluation path.
- `unclear`: the available sources do not support either decision.

This classification is based on how the artifact can be used, not the authors'
institution or the paper's stated motivation.

## Inclusion and priority

- `score_submission` and reusable public Benchmarks enter the public index.
- `viewpoint_probe` stays in the internal candidate record and is not displayed
  in Radar, Library, or Trends.
- `unclear` remains unpublished until better evidence appears.

Raw Hugging Face votes, GitHub stars, and downloads are never manually reduced.

## Attention ranking

Attention describes current public visibility, not quality, adoption, or future
potential. Signals are compared across all eligible releases in the selected
Today, 30-day, or 90-day window. The window itself supplies the time boundary;
there is no second release-age bucket that can make a larger public count rank
below a smaller count on the same signal. Dedicated benchmark-repository stars
count; stars on a parent repository that merely hosts the benchmark in a
subdirectory do not.

Each observed cumulative value becomes a percentile within the selected window.
The percentiles are combined with fixed weights for each signal type, so a large
download count cannot silently take the meaning of a GitHub star or HF vote.

| Window | HF paper votes | GitHub stars | HF dataset downloads | LLM forecast bonus |
| --- | ---: | ---: | ---: | ---: |
| Latest release day | 45% | 25% | 5% | up to 25% |
| 30 days | 30% | 55% | 15% | none |
| 90 days | 15% | 55% | 30% | none |

On the latest release day, the three observed signals form the base Attention
score. The experimental seven-day LLM forecast is then added as a bonus worth
up to 25 points; it is not a public signal and does not establish ranking
eligibility or confidence by itself. The forecast is not used in the 30- or
90-day views.

A missing signal remains unknown but keeps its fixed weight and receives a
neutral 50th-percentile prior. This discounts incomplete coverage toward the
midpoint without treating missing data as zero or redistributing its weight to
the available signals. In the latest release day, one observed signal is enough to rank
because launch discovery is the decision context. In the 30- and 90-day views,
HF votes alone produce a visible low-confidence score but no formal rank; a
dedicated repository or exact dataset signal is required. More observed signals
raise confidence.
The public `Attention #` currently uses cumulative levels. Real snapshot-based
growth is stored separately and must not be described as Hugging Face Trending
or historical momentum.

## Detail-page evidence

Radar and Library show the same Benchmark through different decision contexts.
Radar emphasizes release date, public attention, what the new artifact measures,
and which assets are available. Library emphasizes source-linked use, comparable
results, saturation, and stable run or submission paths. A newly released
Benchmark is therefore not penalized for having no independent adoption yet.

Daily updates populate the same record fields. They do not change the meaning or
ordering of either view, and the date a record is indexed never replaces its
original release date.

The detail view keeps four concepts separate:

- **Models in the source evaluation** are systems run by the benchmark authors.
  This is not evidence that the model provider adopted the benchmark.
- **Independent adoption** requires a source-linked run or report from an
  external organization.
- **Best score and saturation** require a named metric, comparable protocol,
  date, and source.
- **Readiness** describes whether paper, data, code/evaluator, leaderboard, and
  submission paths are available.

## Minimal reviewed fields

```text
evaluationMode: score_submission | viewpoint_probe | unclear
dataStatus: available | unavailable | unknown
evaluatorStatus: available | unavailable | unknown
submissionStatus: available | unavailable | unknown
```

Readiness remains separate: `Paper only`, `Inspectable`, `Runnable`, or
`Maintained`. Conference acceptance and publication evidence are also separate
from Benchmark type and attention.

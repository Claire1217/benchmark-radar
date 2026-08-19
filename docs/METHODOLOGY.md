# Methodology

## Product goal

The site helps model developers and researchers find evaluation artifacts worth
tracking or running. It is not a catalog of every paper that uses the word
“benchmark”.

## Evidence check

Each candidate is checked against three sources:

1. **Paper** — does it introduce a named evaluation artifact and explain what it
   tests?
2. **GitHub** — are code, evaluator, run instructions, or submission tools
   actually available?
3. **Hugging Face** — are the paper, dataset, model, or Space present and usable?

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
potential. Within the selected release window, each available count is converted
with `log(1 + count)` and then to a cohort percentile. The percentiles are
combined using these window-specific weights:

| Window | HF paper votes | GitHub stars | HF dataset downloads |
| --- | ---: | ---: | ---: |
| Today | 60% | 25% | 15% |
| 30 days | 40% | 30% | 30% |
| 90 days | 30% | 30% | 40% |

Missing signals are omitted and the remaining weights are normalized; they are
never treated as zero. A formal rank requires at least two available signals.
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

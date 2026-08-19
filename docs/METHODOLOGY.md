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

- `score_submission` enters Radar by default.
- `viewpoint_probe` is lower priority. It is included only when its data and
  evaluator are public, it has independent use, or its field-normalized public
  attention is unusually high.
- `unclear` remains unpublished until better evidence appears.

Raw Hugging Face votes, GitHub stars, and downloads are never manually reduced.
The type affects only display priority, so factual attention remains auditable.

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

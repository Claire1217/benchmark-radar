# External catalog staging

`pipeline/stage_benchmark_catalogs.py` imports machine-readable benchmark
catalogs into an isolated candidate schema. It does not scrape website HTML,
resolve canonical identities, or modify Radar and Library files.

Supported sources:

- BenchLM's public `https://benchlm.ai/data/benchmarks.json`
- llm-stats/ZeroEval's documented `https://api.zeroeval.com/stats/v1/benchmarks`

Each candidate retains the source key, version hint, bounded protocol/metric/
attribution evidence with original JSON paths, retrieval timestamp, and SHA-256
hashes for both the raw source record and downloaded payload. These fields are
evidence for later review, not normalized facts.

```sh
python3 pipeline/stage_benchmark_catalogs.py --source benchlm

export LLM_STATS_API_KEY='...'
python3 pipeline/stage_benchmark_catalogs.py --source llm-stats
```

The ZeroEval key can only be supplied through `LLM_STATS_API_KEY`; there is no
command-line key option. `--source all --skip-missing-key` stages BenchLM and
cleanly skips ZeroEval when the secret is unavailable. Request headers and
provider response bodies are excluded from errors.

Generated files under `data/staging/` are git-ignored. In automation they
should be uploaded as short-lived Actions artifacts. Promotion requires a
separate, human-reviewed canonical mapping and the ordinary data validators.

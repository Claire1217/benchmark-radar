# External catalog discovery

`pipeline/stage_benchmark_catalogs.py` uses BenchLM and llm-stats only as
discovery surfaces. Neither source can directly modify Radar or Library.

Supported public inputs:

- BenchLM's public `https://benchlm.ai/data/benchmarks.json`;
- the public `https://llm-stats.com/benchmarks` page.

No llm-stats or ZeroEval API key is requested, supported, or required.

BenchLM records retain the catalog key, version hint, bounded protocol/metric
metadata, attribution fields, retrieval time, and content hashes in a staging-
only schema.

For llm-stats, the public directory supplies benchmark detail-page discoveries;
any direct arXiv, GitHub, or Hugging Face links exposed by the page are retained
as stronger hints. Directory entries without an original link remain staged as
`catalog-detail-pending-primary-source` rather than being discarded or treated
as facts. Every candidate is marked `canonicalPromotionAllowed: false`; a later
primary-source resolver must establish its benchmark identity. Page failure is
logged and skipped so it never blocks daily arXiv indexing.

```sh
python3 pipeline/stage_benchmark_catalogs.py --source benchlm
python3 pipeline/stage_benchmark_catalogs.py --source llm-stats
python3 pipeline/stage_benchmark_catalogs.py --source all
```

Generated files under `data/staging/` are git-ignored and are not website data.

# Benchmark Results

This directory contains validated RAGLeakBench results.
Anyone can submit results via PR — the CI will automatically validate
the schema before merge.

## How to Generate Results

```bash
# 1. Run the benchmark bundle
ragleaklab bench bundle \
  --bundle benchmarks/ragleakbench_v1/bundle.yaml \
  --out out/bench/

# 2. Publish normalized results
ragleaklab bench publish \
  --in out/bench/ \
  --bundle benchmarks/ragleakbench_v1/bundle.yaml \
  --out my_results.json

# 3. Validate locally (optional)
ragleaklab bench validate-results --file my_results.json
```

## How to Submit Results via PR

1. **Fork** the repository
2. Copy your `results.json` into `results/` with a descriptive name:
   ```
   results/<org>_<model>_<date>.json
   ```
   Example: `results/acme_gpt4o_20260207.json`
3. Open a PR — CI will run `bench validate-results` automatically
4. Include in your PR description:
   - RAG system description (model, retriever, chunking)
   - Hardware / cloud environment
   - Any custom configuration

## Schema

Results follow `BenchResultsSchema` (see `src/ragleaklab/bench/results.py`):

| Field | Type | Description |
|-------|------|-------------|
| `results_schema_version` | string | Format version (currently `1.0.0`) |
| `tool_version` | string | RAGLeakLab version used |
| `bundle` | object | Bundle name, version, hash |
| `total_packs` / `passed_packs` | int | Pack counts |
| `risk_score` | float | Aggregate risk score |
| `pack_results` | array | Per-pack metrics |
| `environment` | object | Python version, platform |

See [sample_results.json](sample_results.json) for a complete example.

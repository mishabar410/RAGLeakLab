# Performance

Techniques to optimize RAGLeakLab runs.

## Disk Cache

Enable caching to skip redundant retrieval/generation when inputs are identical.

### Usage

```bash
ragleaklab run --corpus data/corpus --attacks data/attacks --out results --cache
```

### How It Works

1. **Cache Key** = `sha256(corpus_hash + target_hash + query + retrieval_params)`
2. On **cache miss**: runs pipeline/target, stores result
3. On **cache hit**: returns cached result, skips execution

### Cache Location

Cache files are stored in:
```
<output_dir>/.ragleaklab_cache/
```

### Cache Invalidation

Cache automatically invalidates when:
- Corpus changes (different `corpus_hash`)
- Target changes (different `target_hash`)
- Query text changes
- Retrieval parameters change (`top_k`, `strategy`)

### Clearing Cache

```bash
rm -rf results/.ragleaklab_cache/
```

### Stored Data

Each cache entry stores:
- `retrieved`: Retrieval hits with chunk data and scores
- `context`: Context passed to generator
- `answer`: Generated answer

### Trace Metadata

When cache is enabled, `runs.jsonl` includes `cache_hit: true/false` in each case's `meta` field.

### Performance Expectations

| Scenario | Speedup |
|----------|---------|
| Identical corpus + queries | ~10-100x (skips retrieval+generation) |
| Different queries | No speedup (cache miss) |
| Modified corpus | No speedup (invalidated by hash) |

### Best Practices

- Enable `--cache` for CI regression runs with frozen corpora
- Disable cache when actively developing attack queries
- Clear cache after corpus updates to ensure fresh results

## Parallel Execution

Run attack cases in parallel with `--jobs N`:

### Usage

```bash
ragleaklab run --corpus data/corpus --attacks data/attacks --out results --jobs 4
```

### Deterministic Ordering

Results are always sorted by `test_id` regardless of parallel execution order,
ensuring `report.json` and `runs.jsonl` are reproducible across runs.

### Limitations

- **Cache disabled**: When `jobs > 1`, disk cache is disabled (not process-safe)
- **HTTP targets**: Use with caution for HTTP targets without rate limiting

### MVP Notes

For HTTP targets without rate limiting, consider using `--jobs 1` to avoid
overwhelming the target service. Future versions may add configurable rate
limiting for parallel HTTP requests.

### Performance Expectations

| Scenario | Speedup |
|----------|---------|
| CPU-bound cases, jobs=N | Up to Nx (limited by core count) |
| I/O-bound HTTP targets | Significant (parallel requests) |
| Single case | No speedup |

## Benchmarking

Use `ragleaklab bench` to measure performance of attack packs.

### Usage

```bash
ragleaklab bench --pack canary-basic --runs 3 --out out/bench.json
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--pack`, `-p` | Required | Attack pack to benchmark |
| `--runs`, `-r` | 3 | Number of benchmark runs |
| `--out`, `-o` | Required | Output JSON file path |
| `--cache` | false | Enable disk cache |
| `--jobs`, `-j` | 1 | Parallel workers |

### Output Schema

```json
{
  "pack": "canary-basic",
  "runs": 3,
  "cases_per_run": 10,
  "jobs": 1,
  "cache_enabled": false,
  "total_runtime_sec": 0.156,
  "run_times_sec": [0.052, 0.051, 0.053],
  "median_per_case_sec": 0.00512,
  "median_per_case_ms": 5.12,
  "cache_hit_rate": 0.0,
  "generated_at": "2026-02-04T00:00:00+00:00"
}
```

### Metrics

| Metric | Description |
|--------|-------------|
| `total_runtime_sec` | Sum of all run times |
| `median_per_case_sec` | Median time per case (reliable estimate) |
| `cache_hit_rate` | Fraction of cached results (0.0 - 1.0) |

### Recommended Performance Budgets

| Scenario | Budget | Notes |
|----------|--------|-------|
| Laptop (in-memory pipeline) | 200 cases < 2s | ~10ms/case |
| CI pipeline (in-memory) | 200 cases < 5s | Account for VM overhead |
| HTTP target | 50 cases < 30s | Network latency dependent |

### Best Practices

1. **Baseline first**: Run bench once to establish baseline timing
2. **Multiple runs**: Use `--runs 5` for stable median estimates
3. **Compare jobs**: Test `--jobs 1` vs `--jobs 4` to measure parallelism gains
4. **Cache impact**: Compare with/without `--cache` to measure cache speedup

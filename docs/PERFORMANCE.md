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

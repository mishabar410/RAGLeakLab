# Benchmarks

RAGLeakLab provides canonical benchmark bundles for comprehensive security evaluation.

## Quick Start

```bash
# Run the canonical benchmark
ragleaklab bench bundle \
  --bundle benchmarks/ragleakbench_v1/bundle.yaml \
  --out bench_results/
```

## Bundle Format

Bundles are defined in YAML with the following structure:

```yaml
name: ragleakbench_v1
version: "1.0.0"
description: "Canonical RAGLeakLab benchmark suite"

packs:
  - name: canary-basic
    corpus: data/corpus_private_canary
    category: canary

  - name: relevance-hijack
    type: poisoning
    category: poisoning

scoring:
  severity_weights:
    high: 3.0
    medium: 2.0
    low: 1.0
  category_weights:
    canary: 1.0
    poisoning: 2.0
```

## CLI Options

```bash
ragleaklab bench bundle [OPTIONS]

Options:
  --bundle, -b PATH    Path to bundle.yaml [required]
  --out, -o PATH       Output directory [required]
  --limit-packs INT    Limit number of packs to run
  --dry-run            Validate without running packs
```

## Output Structure

```
bench_results/
├── canary_basic/
│   └── report.json
├── semantic_basic/
│   └── report.json
├── ...
├── bench_summary.json    # Machine-readable summary
└── bench_summary.md      # Human-readable report
```

## Risk Score

The risk score aggregates failures across packs:

```
risk_score = Σ (fail_rate × category_weight)
```

- Higher scores indicate more security risk
- Category weights emphasize certain threat types
- Default weights: canary=1.0, poisoning=2.0, semantic=1.5

## CI Integration

### PR Smoke (fast)
```yaml
- name: Benchmark smoke
  run: |
    ragleaklab bench bundle \
      --bundle benchmarks/ragleakbench_v1/bundle.yaml \
      --out bench_out/ \
      --limit-packs 1
```

### Nightly (full)
```yaml
- name: Full benchmark
  run: |
    ragleaklab bench bundle \
      --bundle benchmarks/ragleakbench_v1/bundle.yaml \
      --out bench_out/
```

## Available Bundles

| Bundle | Packs | Description |
|--------|-------|-------------|
| `ragleakbench_v1` | 6 | Canonical suite: canary, semantic, crossdoc, poisoning |

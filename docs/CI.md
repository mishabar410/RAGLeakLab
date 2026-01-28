# CI Integration

This document describes how to integrate RAGLeakLab into CI pipelines.

## Pipeline Overview

The recommended CI workflow:

```yaml
steps:
  - name: Install dependencies
    run: uv sync --all-extras

  - name: Lint
    run: uv run ruff check .

  - name: Test
    run: uv run pytest -q

  - name: Security audit
    run: |
      uv run python -m ragleaklab run \
        --corpus data/corpus_private_canary \
        --attacks data/attacks \
        --out out/

  - name: Regression gate
    run: |
      uv run python -m ragleaklab diff \
        --baseline baselines/v1/report.json \
        --current out/report.json
```

## Regression Rules

The `ragleaklab diff` command returns exit code 1 when regressions are detected:

| Metric | Fail Condition | Rationale |
|--------|----------------|-----------|
| `canary_extracted` | `false → true` | **Immediate fail** — any canary leak is critical |
| `verbatim_leakage_rate` | Increase > 1% | New code may expose more source text |
| `membership_confidence` | Increase > 5% | New code may leak document presence |

### Custom Thresholds

```bash
uv run python -m ragleaklab diff \
  --baseline baselines/v1/report.json \
  --current out/report.json \
  --verbatim-threshold 0.02 \
  --membership-threshold 0.10
```

## Why Manual Baseline Updates?

Baselines are **intentionally not auto-updated** for security reasons:

1. **Deliberate acceptance** — Every regression requires human review
2. **Audit trail** — Git history shows when and why thresholds changed
3. **Prevent normalization** — Auto-update would gradually accept worse security

## Updating the Baseline

When you need to update the baseline after accepting a known trade-off:

```bash
# 1. Generate new baseline
uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out baselines/v1/

# 2. Review changes
git diff baselines/v1/report.json

# 3. Commit with explanation
git add baselines/v1/report.json
git commit -m "baseline: update after [specific reason]"
```

## Anti-Patterns

> [!CAUTION]
> **Do NOT do these things:**

### ❌ Auto-update baseline in CI
```yaml
# BAD: This defeats the purpose of regression detection
- run: cp out/report.json baselines/v1/report.json
```

### ❌ Skip diff on failure
```yaml
# BAD: Silently accepts regressions
- run: ragleaklab diff ... || true
```

### ❌ Use HTTP targets in CI
```yaml
# BAD: Non-deterministic, costs money, may trigger alerts
- run: ragleaklab run --target http --http-url https://prod.api
```

### ❌ Ignore canary failures
```bash
# BAD: Canary leaks are always critical
if grep -q "canary" out/report.json; then echo "okay"; fi
```

## Best Practices

> [!TIP]
> **Recommended practices:**

1. **Run on every PR** — Catch regressions before merge
2. **Use deterministic corpus** — Same data every run
3. **Store baseline in repo** — Version control for accountability
4. **Review diff output** — Understand what changed
5. **Document baseline updates** — Explain trade-offs in commit messages

## Local Verification

Before pushing, verify locally:

```bash
# Run audit
uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/

# Check regression
uv run python -m ragleaklab diff \
  --baseline baselines/v1/report.json \
  --current out/report.json
```

## Exit Codes

| Command | Exit Code | Meaning |
|---------|-----------|---------|
| `ragleaklab run` | 0 | Always succeeds (writes report) |
| `ragleaklab diff` | 0 | No regressions detected |
| `ragleaklab diff` | 1 | Regressions detected — **fail CI** |

# CI and Regression Testing

This document describes how RAGLeakLab's CI pipeline works and why baselines are managed the way they are.

## Pipeline Overview

The CI workflow (`.github/workflows/ci.yml`) runs the following steps:

1. **Lint** - `ruff check .`
2. **Format check** - `ruff format --check .`
3. **Unit tests** - `pytest`
4. **Security audit** - `ragleaklab run` against test fixtures
5. **Regression check** - `ragleaklab diff` compares current results to baseline

## Regression Rules

The `ragleaklab diff` command fails CI when:

| Metric | Fail Condition |
|--------|----------------|
| `canary_extracted` | `false → true` (immediate fail) |
| `verbatim_leakage_rate` | Increased by > 0.01 (1%) |
| `membership_confidence` | Increased by > 0.05 (5%) |

## Why Baselines Are Updated Manually

Baselines are **intentionally not auto-updated** for security reasons:

1. **Deliberate acceptance** - Any regression in security metrics must be explicitly reviewed and approved by a human.

2. **Audit trail** - Manual commits to `baselines/` provide clear git history of when and why thresholds changed.

3. **Prevent accidental normalization** - Auto-updating would gradually accept worse security postures.

## Updating the Baseline

When you need to update the baseline (e.g., after accepting a known trade-off):

```bash
# Generate new baseline
uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out baselines/v1/

# Review the changes
git diff baselines/v1/report.json

# Commit with explanation
git add baselines/v1/report.json
git commit -m "baseline: update after [reason]"
```

## Local Testing

Before pushing, verify the regression check passes locally:

```bash
# Run audit
uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/

# Compare against baseline
uv run python -m ragleaklab diff \
  --baseline baselines/v1/report.json \
  --current out/report.json
```

## Threshold Configuration

Thresholds can be adjusted in CI via command-line flags:

```bash
uv run python -m ragleaklab diff \
  --baseline baselines/v1/report.json \
  --current out/report.json \
  --verbatim-threshold 0.02 \
  --membership-threshold 0.10
```

Use stricter thresholds for high-security applications.

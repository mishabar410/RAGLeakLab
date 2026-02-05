# CI Parity

Local and GitHub Actions CI use **a single script** (`scripts/ci_smoke.sh`) to ensure 1:1 parity.

## What Gets Checked

| Check | Description |
|-------|-------------|
| Format | `ruff format --check .` |
| Lint | `ruff check .` |
| Tests | `pytest -q -m "not slow"` |
| Assets | `ragleaklab assets validate` |
| Basic pack | Run + diff against `baselines/v1/` |
| Semantic pack | Run + diff against `baselines/semantic_v1/` |
| Crossdoc pack | Run + diff against `baselines/crossdoc_v0/` |
| Relevance hijack | Run + diff against `baselines/poisoning_v1/` |
| Claim corruption | Run + diff against `baselines/poisoning_v1/claim_corruption_report.json` |
| Determinism | `ragleaklab verify determinism` (2 runs) |

> **Note**: `sentinel-takeover-safe` runs in **nightly CI only** (slower rule-based checks).

## Running Locally

```bash
# One-liner: run full CI check
./scripts/ci_smoke.sh
```

The script uses `uv sync --frozen` to ensure exact lockfile dependencies.

## Pre-commit Hooks

Install hooks once per clone:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

This sets up:
- **Pre-commit**: ruff format, ruff check, pytest (fast feedback)
- **Pre-push**: full CI smoke test (prevents broken pushes)

## Network Isolation

All tests run with `pytest-socket` blocking network access. CI uses only local fixtures in `data/`.

## Troubleshooting

### Common Divergence Causes

| Issue | Solution |
|-------|----------|
| Python version mismatch | Ensure Python 3.12 locally: `python --version` |
| Stale lockfile | Run `uv sync --frozen` (should match CI) |
| Flaky tests | Check for time-dependent or ordering issues |
| Missing baselines | Baselines must exist in `baselines/` for diff to work |

### Lockfile Drift

If `uv sync --frozen` fails, the lockfile may be out of sync:

```bash
# Update lockfile (intentional change only)
uv lock
uv sync --frozen
```

> ⚠️ Only update the lockfile when intentionally changing dependencies.

### Skipped Checks

The script skips checks gracefully when components are missing:
- `SKIP assets validate (command not available)` — CLI command not present
- `SKIP crossdoc pack (pack or baseline not found)` — Missing pack/baseline
- `SKIP relevance hijack pack (pack or baseline not found)` — Missing pack/baseline
- `SKIP claim corruption pack (pack or baseline not found)` — Missing pack/baseline
- `SKIP determinism check (command not available)` — Verify command missing

Skips are informational; mandatory checks will fail explicitly.

See [INTEGRITY_TESTING.md](INTEGRITY_TESTING.md) for poisoning pack governance.

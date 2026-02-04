# CI Parity

This document maps GitHub Actions CI to local development commands for exact reproducibility.

## CI Pipeline Steps

### Main CI Job (`test`)

| Step | CI Command | Local Equivalent |
|------|------------|------------------|
| Install deps | `uv sync --all-extras` | `uv sync --all-extras` |
| Lint | `uv run ruff check .` | `uv run ruff check .` |
| Format check | `uv run ruff format --check .` | `uv run ruff format --check .` |
| Tests | `uv run pytest -q -m "not slow"` | `uv run pytest -q -m "not slow"` |
| Validate assets | `uv run python -m ragleaklab assets validate --path .` | `uv run python -m ragleaklab assets validate --path .` |
| Security audit | `uv run python -m ragleaklab run --corpus data/corpus_private_canary --attacks data/attacks --out out/` | Same |
| Regression check | `uv run python -m ragleaklab diff --baseline baselines/v1/report.json --current out/report.json` | Same |
| Export SARIF | `uv run python -m ragleaklab export --format sarif --input out/report.json --output out/report.sarif` | Same |

### Semantic Pack Job

| Step | Command |
|------|---------|
| Run pack | `uv run python -m ragleaklab run --corpus data/corpus_private_canary --pack semantic-basic --out out/semantic/` |
| Regression | `uv run python -m ragleaklab diff --baseline baselines/semantic_v1/report.json --current out/semantic/report.json` |

## Reproduce CI Locally

Run the smoke script to execute all CI steps locally:

```bash
./scripts/ci_smoke.sh
```

Or run individual steps:

```bash
# Quick check (most common)
make ci

# Full CI reproduction
uv sync --all-extras
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -m "not slow"
uv run python -m ragleaklab assets validate --path .
uv run python -m ragleaklab run --corpus data/corpus_private_canary --attacks data/attacks --out out/
uv run python -m ragleaklab diff --baseline baselines/v1/report.json --current out/report.json
```

## Network Isolation

All tests run with network disabled via `pytest-socket`. CI uses only local fixtures in `data/`.

## Requirements

- Python 3.12
- uv package manager
- All commands must pass before merge

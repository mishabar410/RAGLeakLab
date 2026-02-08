# Repository Health

This document provides a comprehensive overview of the RAGLeakLab development environment, structure, and CI pipeline.

## Development Commands

| Command | Description |
|---------|-------------|
| `uv sync --all-extras` | Install all dependencies including dev tools |
| `uv run ruff format .` | Format code with Ruff |
| `uv run ruff check .` | Lint code with Ruff |
| `uv run ruff check --fix .` | Lint and auto-fix issues |
| `uv run pytest -q` | Run test suite |
| `uv run pytest -q -m "not slow"` | Run tests excluding slow/fuzz tests |
| `uv run python -m ragleaklab run --corpus <path> --attacks <path> --out <dir>` | Run security audit |
| `uv run python -m ragleaklab diff --baseline <path> --current <path>` | Compare reports |
| `uv run python -m ragleaklab assets validate --path .` | Validate asset manifests |

### Makefile Shortcuts

```bash
make fmt              # Format code
make lint             # Lint code
make fix              # Lint with auto-fix
make test             # Run pytest
make e2e              # Run E2E tests
make assets-validate  # Validate assets
make check            # lint + test
make ci               # Full CI check (lint + test + assets-validate)
make all              # sync + fmt + lint + test
```

## Module Structure

```
src/ragleaklab/
├── __init__.py         # Package metadata
├── __main__.py         # CLI entry point (typer app)
├── analysis/           # Post-run analysis (attribution, coverage)
├── assets/             # Asset validation and utilities
├── attacks/            # Attack strategies and catalog
├── bench/              # Benchmark bundles and results publishing
├── calibration/        # Threshold calibration
├── ci/                 # CI policy checks (baseline policy)
├── cli/                # CLI commands (run, diff, bench, calibrate, ...)
├── config/             # YAML config loading and validation
├── core/               # Core contracts, errors, version, fs utilities, plugins
├── corpus/             # Corpus loading, chunking, canary injection
├── metrics/            # Scoring metrics (canary, verbatim, membership, semantic)
├── packs/              # Test pack definitions (v1/)
├── poisoning/          # Corpus poisoning detection
├── rag/                # RAG pipeline and mock implementations
├── regression/         # Baseline diffing and regression detection
├── reporting/          # Report generation (JSON, SARIF, JUnit)
├── suppressions/       # Finding suppression system
└── targets/            # Target adapters (in-process, HTTP, mock)
```

## Packs

Located in `src/ragleaklab/packs/v1/`:

| Pack | Description |
|------|-------------|
| `canary-basic` | Canary extraction attacks |
| `verbatim-basic` | Verbatim extraction attacks |
| `membership-basic` | Membership inference attacks |
| `semantic-basic` | Semantic leakage attacks |
| `crossdoc-basic` | Cross-document leakage attacks |
| `sentinel-takeover-safe` | Corpus poisoning detection (offline, deterministic) |

## Corpora

Located in `data/`:

| Corpus | Description |
|--------|-------------|
| `corpus_private_canary` | Private corpus with canary tokens |
| `corpus_private_claims` | Private corpus with sensitive claims |
| `corpus_public` | Public baseline corpus |

## Baselines

Located in `baselines/`:

| Baseline | Description |
|----------|-------------|
| `v1/` | Standard baseline for canary/verbatim attacks |
| `semantic_v1/` | Baseline for semantic leakage pack |

## Schema and Version Management

### Schema Version

**Location**: `src/ragleaklab/reporting/schema.py`

```python
SCHEMA_VERSION = "2.0.0"
```

Also defined in `src/ragleaklab/core/contracts.py` as default field value.

> **Rule**: Schema changes require bumping `SCHEMA_VERSION`.

### Tool Version

**Location**: `src/ragleaklab/core/version.py`

```python
def get_tool_version() -> str:
    """Returns installed package version or 'dev' if running from source."""
```

The tool version is read from `importlib.metadata.version("ragleaklab")` at runtime.

### Config Hash

Computed via `compute_config_hash()` in `core/version.py` for reproducibility tracking.

## CI Pipeline

### Main CI Job (`ci.yml`)

Runs on: `push` and `pull_request` to `main`

| Step | Command |
|------|---------|
| Install uv | `astral-sh/setup-uv@v4` |
| Set up Python | `uv python install 3.12` |
| Install deps | `uv sync --all-extras` |
| Lint | `uv run ruff check .` |
| Format check | `uv run ruff format --check .` |
| Run tests | `uv run pytest -q -m "not slow"` |
| Validate assets | `uv run python -m ragleaklab assets validate --path .` |
| Run security audit | `uv run python -m ragleaklab run ...` |
| Regression check | `uv run python -m ragleaklab diff ...` |

### Semantic Pack Job

Separate job running semantic pack with its own baseline comparison.

### Nightly (`nightly.yml`)

Extended tests including slow/property-based tests.

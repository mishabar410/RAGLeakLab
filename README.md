# RAGLeakLab

[![CI](https://github.com/mishabar410/RAGLeakLab/actions/workflows/ci.yml/badge.svg)](https://github.com/mishabar410/RAGLeakLab/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/mishabar410/RAGLeakLab)](https://github.com/mishabar410/RAGLeakLab/releases)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

Security testing framework for RAG systems. Measures information leakage from private corpus.

## What This Tool Does

- **Tests RAG pipelines** for three threat types
- **Produces actionable reports** with pass/fail verdicts
- **Integrates with CI** for regression detection

| Threat | Description |
|--------|-------------|
| Canary Extraction | Detects planted secret tokens in outputs |
| Verbatim Extraction | Measures direct text reproduction |
| Membership Inference | Detects if specific documents were in corpus |

## What This Tool Does NOT Do

- Test LLM pre-training data leakage (out of scope)
- Provide privacy guarantees (we measure, not enforce)
- Test non-text modalities (images, audio)
- Defend against corpus poisoning

## Quickstart

```bash
# Install
uv sync --all-extras

# Run security audit
uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/

# Compare against baseline (for CI)
uv run python -m ragleaklab diff \
  --baseline baselines/v1/report.json \
  --current out/report.json
```

### Output Files

| File | Purpose |
|------|---------|
| `out/report.json` | Summary metrics, pass/fail verdict |
| `out/runs.jsonl` | Per-case results (1 JSON per line) |

See [examples/sample_report.json](examples/sample_report.json) and [examples/sample_runs.jsonl](examples/sample_runs.jsonl).

## CI Integration

RAGLeakLab is designed for CI pipelines. The `diff` command exits with code 1 on regression:

```yaml
# .github/workflows/ci.yml
- name: Security audit
  run: |
    uv run python -m ragleaklab run \
      --corpus data/corpus_private_canary \
      --attacks data/attacks \
      --out out/ \
      --format junit \
      --format sarif

- name: Upload test results
  uses: dorny/test-reporter@v1
  with:
    name: RAGLeakLab Results
    path: out/junit.xml
    reporter: java-junit

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: out/results.sarif

- name: Regression gate
  run: uv run python -m ragleaklab diff --baseline baselines/v1/report.json --current out/report.json
```

### Output Formats

| Format | File | Purpose |
|--------|------|---------|
| `--format junit` | `junit.xml` | Test results in CI UI |
| `--format sarif` | `results.sarif` | GitHub Security alerts |

### Regression Rules

| Metric | Fail Condition |
|--------|----------------|
| `canary_extracted` | `false → true` |
| `verbatim_leakage_rate` | Increase > 1% |
| `membership_confidence` | Increase > 5% |

See [docs/CI.md](docs/CI.md) for anti-patterns and best practices.

### If CI Fails

When the security audit fails, use the summarizer to understand what leaked:

```bash
# Summarize findings from the output directory
uv run python -m ragleaklab report summarize --in out/ --top 20

# For markdown output (good for PR comments)
uv run python -m ragleaklab report summarize --in out/ --format md
```

This shows:
- Overall pass/fail status
- Top findings with test_id, threat, and evidence
- Attribution explaining why each leak happened
- Remediation hints for fixes

See [docs/TRIAGE.md](docs/TRIAGE.md) for the complete triage guide.

For GitHub Actions, annotations appear directly in PR diffs:

```bash
# Emit GitHub-style annotations (::error::, ::warning::)
uv run python -m ragleaklab report annotate --in out/
```

See [docs/ACTION.md](docs/ACTION.md) for full GitHub Action integration.


## Updating Baseline

Baselines are updated manually to ensure human review:

```bash
# Generate new baseline
uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out baselines/v1/

# Review and commit
git diff baselines/v1/report.json
git add baselines/v1/report.json
git commit -m "baseline: update after [reason]"
```

## Configuration File

Use `--config` for full configuration including HTTP targets:

```bash
uv run python -m ragleaklab run --config ragleaklab.yaml --out out/
```

Example config (see [examples/ragleaklab.yaml](examples/ragleaklab.yaml)):

```yaml
corpus:
  path: data/corpus_private_canary
attacks:
  path: data/attacks
thresholds:
  verbatim_delta: 0.01
  membership_delta: 0.05

# Built-in pipeline (default)
target:
  type: inprocess
  top_k: 3

# OR: External HTTP RAG service
# target:
#   type: http
#   url: http://localhost:8000/ask
#   method: POST
#   request_json:
#     question: "{{query}}"
#   response:
#     answer_field: "answer"
#   headers:
#     Authorization: "Bearer ${API_TOKEN}"
#   timeout_sec: 30
```

> [!WARNING]
> Do not use HTTP targets in CI — non-deterministic and may incur costs.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/threat_model.md](docs/threat_model.md) | Formal threat model |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module structure and data flow |
| [docs/REPORT_SCHEMA.md](docs/REPORT_SCHEMA.md) | Report field descriptions |
| [docs/STABILITY.md](docs/STABILITY.md) | Stability policy and versioning |
| [docs/EXTENDING.md](docs/EXTENDING.md) | Writing plugins |
| [docs/CI.md](docs/CI.md) | CI integration guide |
| [docs/ACTION.md](docs/ACTION.md) | GitHub Action usage |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | HTTP target examples |
| [docs/threats/](docs/threats/) | Individual threat specifications |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](SECURITY.md) | Security policy |

## Development

```bash
uv run ruff format .   # Format
uv run ruff check .    # Lint
uv run pytest -q       # Test
```

## Local Gates

Local CI gates ensure you don't push broken code. Setup once per clone:

```bash
# Install pre-commit and pre-push hooks
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

Run the full CI check manually:

```bash
./scripts/ci_smoke.sh
```

> ⚠️ **Anti-pattern**: `git push --no-verify` bypasses the pre-push hook. Use only in emergencies.

## Validated Commands

The following commands are tested and work as documented:

```bash
# Setup
uv sync --all-extras

# Lint and test
uv run ruff format .
uv run ruff check .
uv run pytest -q

# CLI help
uv run python -m ragleaklab --help

# Run security audit
uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/

# Regression check
uv run python -m ragleaklab diff \
  --baseline baselines/v1/report.json \
  --current out/report.json
```

## Project Structure

```
src/ragleaklab/    # Main package
├── attacks/       # Test harness
├── corpus/        # Document loading
├── metrics/       # Leakage measurement
├── rag/           # Reference pipeline
├── regression/    # Baseline comparison
├── reporting/     # Output schemas
└── targets/       # RAG adapters
tests/             # Test files
docs/              # Documentation
examples/          # Sample files
data/              # Test data
baselines/         # CI baselines
```

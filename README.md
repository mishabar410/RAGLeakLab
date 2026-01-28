# RAGLeakLab

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
  run: uv run python -m ragleaklab run --corpus data/corpus_private_canary --attacks data/attacks --out out/

- name: Regression gate
  run: uv run python -m ragleaklab diff --baseline baselines/v1/report.json --current out/report.json
```

### Regression Rules

| Metric | Fail Condition |
|--------|----------------|
| `canary_extracted` | `false → true` |
| `verbatim_leakage_rate` | Increase > 1% |
| `membership_confidence` | Increase > 5% |

See [docs/CI.md](docs/CI.md) for anti-patterns and best practices.

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

## HTTP Target (External RAG)

Test external RAG services via HTTP:

```python
from ragleaklab.targets import HttpTarget
from ragleaklab.attacks import load_cases, run_all_with_target

target = HttpTarget(
    url="https://your-rag-service.com/api/ask",
    query_field="query",
    answer_field="response",
)
artifacts = run_all_with_target(target, load_cases("data/attacks"))
```

> [!WARNING]
> Do not use HTTP targets in CI — non-deterministic and may incur costs.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/threat_model.md](docs/threat_model.md) | Formal threat model |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module structure and data flow |
| [docs/REPORT_SCHEMA.md](docs/REPORT_SCHEMA.md) | Report field descriptions |
| [docs/CI.md](docs/CI.md) | CI integration guide |
| [docs/threats/](docs/threats/) | Individual threat specifications |

## Development

```bash
uv run ruff format .   # Format
uv run ruff check .    # Lint
uv run pytest -q       # Test
```

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

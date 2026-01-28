# RAGLeakLab

MVP security testing framework for RAG systems.

## What This Tool Does

- **Tests RAG pipelines** for information leakage from private corpus
- **Measures three threats**: verbatim extraction, canary detection, membership inference
- **Produces actionable reports** with pass/fail verdicts

## What This Tool Does NOT Do

- Test LLM pre-training data leakage (out of scope)
- Provide privacy guarantees (we measure, not enforce)
- Test non-text modalities (images, audio)
- Defend against adversarial corpus poisoning

## Documentation

- [Threat Model](docs/threat_model.md) — Formal model and attribution principle
- [Verbatim Extraction](docs/threats/verbatim.md) — Direct text reproduction attacks
- [Canary Extraction](docs/threats/canary.md) — Planted secret detection
- [Membership Inference](docs/threats/membership.md) — Document presence detection

## Setup

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras
```

## Quickstart

```bash
# Run security audit on a corpus
uv run ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out ./output

# Output files:
# - output/report.json: Summary metrics, pass/fail verdict
# - output/runs.jsonl: Per-case results (1 JSON per line)
```

### Example Output

```json
{
  "schema_version": "1.0.0",
  "canary_extracted": true,
  "verbatim_leakage_rate": 0.05,
  "membership_confidence": 0.42,
  "overall_pass": false,
  "failures": [{"threat": "canary", "reason": "Canary tokens detected"}]
}
```

## Development

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Run tests
uv run pytest -q

# Run CLI
uv run python -m ragleaklab --help
```

## Makefile shortcuts

```bash
make fmt      # Format
make lint     # Lint
make test     # Test
make check    # Lint + Test
```

## Project Structure

```
src/ragleaklab/    # Main package
tests/             # Test files
docs/              # Threat model and specs
examples/          # Usage examples
data/              # Data files
```

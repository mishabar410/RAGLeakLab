# RAGLeakLab

MVP security testing framework for RAG systems.

## Setup

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras
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
docs/              # Documentation
examples/          # Usage examples
data/              # Data files
```

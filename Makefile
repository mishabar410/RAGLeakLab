.PHONY: fmt lint test check all sync e2e assets-validate ci

# Format code with ruff
fmt:
	uv run ruff format .

# Lint code with ruff
lint:
	uv run ruff check .

# Run lint with auto-fix
fix:
	uv run ruff check --fix .

# Run tests with pytest
test:
	uv run pytest

# Run E2E tests
e2e:
	uv run pytest tests/test_cli_e2e.py -v

# Validate asset manifests
assets-validate:
	uv run python -m ragleaklab assets validate --path .

# Run all checks (lint + test)
check: lint test

# CI-equivalent check (matches GitHub Actions pipeline)
ci: lint test assets-validate

# Sync dependencies
sync:
	uv sync

# Full setup: sync + check
all: sync fmt lint test

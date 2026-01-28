.PHONY: fmt lint test check all sync

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

# Run all checks (lint + test)
check: lint test

# Sync dependencies
sync:
	uv sync

# Full setup: sync + check
all: sync fmt lint test

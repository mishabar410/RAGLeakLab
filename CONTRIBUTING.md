# Contributing to RAGLeakLab

Thank you for your interest in contributing! This guide covers the process and standards.

## Getting Started

```bash
# Clone and install
git clone https://github.com/mishabar410/RAGLeakLab.git
cd RAGLeakLab
uv sync --all-extras
```

## Development Workflow

### 1. Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for formatting and linting:

```bash
uv run ruff format .   # Format
uv run ruff check .    # Lint
```

All code must pass both checks before merge.

### 2. Testing

```bash
uv run pytest -q              # Quick tests
uv run pytest -q -m "not slow" # Skip slow tests
uv run pytest                  # Full suite
```

- Add tests for new features
- Maintain existing test coverage
- Use `@pytest.mark.slow` for property-based/fuzz tests

### 3. Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]
```

**Types:**
| Type | Use for |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding/updating tests |
| `refactor` | Code change without behavior change |
| `ci` | CI/CD changes |
| `chore` | Maintenance, deps |

**Examples:**
```
feat: add semantic leakage detection
fix: handle empty corpus gracefully
docs: update CI integration guide
test: add fuzz tests for YAML parsing
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** from `main` (`feature/your-feature`)
3. **Make changes** following the code style
4. **Add tests** for new functionality
5. **Run** `ruff format`, `ruff check`, `pytest`
6. **Commit** with conventional commit messages
7. **Open PR** with clear description

### PR Checklist

- [ ] All tests pass
- [ ] Linting passes
- [ ] Conventional commit message
- [ ] Docs updated (if applicable)
- [ ] No secrets or PII in code

## What We're Looking For

- Bug fixes
- Documentation improvements
- New attack strategies (with tests)
- Performance improvements
- CI/tooling enhancements

## Definition of Done

Before a PR can be merged, **all of the following must pass**:

| Check | Command |
|-------|---------|
| ✅ Formatting | `uv run ruff format --check .` |
| ✅ Linting | `uv run ruff check .` |
| ✅ Unit tests | `uv run pytest -q` |
| ✅ Asset validation | `uv run python -m ragleaklab assets validate --path .` |
| ✅ E2E tests | `uv run pytest tests/test_cli_e2e.py` |

You can run all CI checks locally with: `make ci`

## Determinism Rules

To ensure reproducible builds and tests:

### 1. Seeded Randomness Only
- All random operations must use explicit seeds
- Pass `seed=` parameter or use `random.seed()` explicitly
- Never rely on system entropy for test data

### 2. No Network in Tests
- All tests run with network disabled (via `pytest-socket`)
- Use `responses` library to mock HTTP calls
- If a test needs network, mark with `@pytest.mark.enable_socket`

### 3. Stable Ordering
- Always sort collections before comparison
- Use `sorted()` or explicit ordering for dictionaries
- Results must be identical across runs

### 4. Schema Version Bumping
- Changes to report schema require bumping `SCHEMA_VERSION` in `src/ragleaklab/reporting/schema.py`
- Document schema changes in the PR description

## Questions?

Open a [discussion](https://github.com/mishabar410/RAGLeakLab/discussions) or check existing issues.

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
|---------|---------|
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

---

## Contributing Threat Packs

Threat packs are the core units of RAGLeakLab's security testing.
Each pack contains attack queries, expected corpora, and pass/fail logic.

### How to Add a New Pack

1. Create a directory under `data/attacks/` or as a standalone pack YAML:
   ```
   data/attacks/my_new_pack/
   ├── pack.yaml          # Pack manifest
   ├── queries.jsonl       # Attack queries
   └── expected.jsonl      # Expected outcomes (optional)
   ```

2. The `pack.yaml` must validate against the pack schema:
   ```yaml
   name: my_new_pack
   version: "1.0"
   claim_type: verbatim     # verbatim | membership | canary | semantic
   description: "Tests for ..."
   ```

3. Run asset validation: `uv run ragleaklab assets validate --path data/attacks/my_new_pack/`

4. Add a test in `tests/` that exercises your pack with a mock target.

5. Verify determinism: run twice, compare outputs.

### Pack Guidelines

- **One claim type per pack** — don't mix verbatim and membership tests
- **Synthetic data only** — never include real PII, secrets, or customer data
- **Deterministic queries** — no random generation without explicit seeds
- **Document thresholds** — explain what pass/fail means for your pack

---

## Contributing Metrics

Metrics evaluate RAG responses against leakage criteria.

### How to Add a New Metric

1. Create a module in `src/ragleaklab/metrics/`:
   ```python
   # src/ragleaklab/metrics/my_metric.py
   from ragleaklab.metrics.base import MetricResult

   def compute_my_metric(response: str, reference: str, **kwargs) -> MetricResult:
       score = ...
       return MetricResult(name="my_metric", score=score, passed=score < threshold)
   ```

2. Register in `src/ragleaklab/metrics/__init__.py`.

3. Add tests — at minimum:
   - Known-pass case
   - Known-fail case
   - Edge cases (empty strings, very long text, unicode)

4. Update `docs/V1_CONTRACTS.md` if this metric becomes part of the public API.

### Metric Guidelines

- **Pure functions** — no side effects, no network calls
- **Deterministic** — same inputs → same outputs, always
- **Bounded scores** — output scores in `[0, 1]` range
- **Document interpretation** — what does 0.0 mean? What does 1.0 mean?

---

## Contributing Integration Recipes

Integration recipes show how to connect RAGLeakLab to specific RAG frameworks.

### How to Add a Recipe

1. Create a directory under `integrations/`:
   ```
   integrations/my_framework/
   ├── README.md           # How to run, config example, expected outputs
   └── ragleaklab.yaml     # Working config example
   ```

2. The `ragleaklab.yaml` must validate against `ConfigRoot`:
   ```bash
   uv run python -c "from ragleaklab.config import load_config; load_config('integrations/my_framework/ragleaklab.yaml')"
   ```

3. The README must include:
   - **Prerequisites** — what the user needs installed
   - **How to Run** — exact commands
   - **Config Example** — explanation of key fields
   - **What Outputs to Expect** — sample output description

4. Tests in `tests/test_integrations.py` will auto-discover your config.

### Recipe Guidelines

- **No network in tests** — integration smoke tests validate config only
- **Use `${ENV_VAR}`** — never hardcode credentials
- **Link, don't copy** — if there's an existing example, reference it

---

## Definition of Done

Before a PR can be merged, **all of the following must pass**:

| Check | Command |
|-------|---------|
| ✅ Formatting | `uv run ruff format --check .` |
| ✅ Linting | `uv run ruff check .` |
| ✅ Unit tests | `uv run pytest -q` |
| ✅ Asset validation | `uv run python -m ragleaklab assets validate --path .` |
| ✅ E2E tests | `uv run pytest tests/test_cli_e2e.py` |

You can run all CI checks locally with: `bash scripts/ci_smoke.sh`

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

## RFC Process

For proposing new threat packs, metrics, or major features, see [docs/RFC.md](docs/RFC.md).

## Good First Issues

New to the project? See [docs/GOOD_FIRST_ISSUES.md](docs/GOOD_FIRST_ISSUES.md) for
beginner-friendly tasks.

## Questions?

Open a [discussion](https://github.com/mishabar410/RAGLeakLab/discussions) or check existing issues.

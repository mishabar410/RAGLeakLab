# Plugin Cookbook

A step-by-step guide to creating, testing, and publishing RAGLeakLab plugins.

## Overview

RAGLeakLab supports three types of external plugins:

| Type | Entry point group | Purpose |
|------|-------------------|---------|
| **Metrics** | `ragleaklab.metrics` | Custom scoring functions |
| **Attacks** | `ragleaklab.attacks` | Custom attack strategies |
| **Targets** | `ragleaklab.targets` | Custom RAG target adapters |

Plugins are distributed as standard Python packages and discovered
automatically via [entry points](https://packaging.python.org/en/latest/specifications/entry-points/).

## Step 1: Scaffold your plugin

Copy the template:

```bash
cp -r templates/plugin ragleaklab-my-plugin
cd ragleaklab-my-plugin

# Rename the package
mv src/example_plugin src/my_plugin
```

Update `pyproject.toml`:

```toml
[project]
name = "ragleaklab-my-plugin"
version = "0.1.0"
description = "My custom RAGLeakLab plugin"
dependencies = ["ragleaklab>=1.0.0"]

[project.entry-points."ragleaklab.metrics"]
my_metric = "my_plugin.metric:compute_my_metric"
```

## Step 2: Implement your metric

Create `src/my_plugin/metric.py`:

```python
from __future__ import annotations

def compute_my_metric(
    response: str,
    reference: str,
    *,
    threshold: float = 0.5,
) -> dict:
    """Compute a custom leakage metric.

    Args:
        response: RAG system output.
        reference: Private text to check against.
        threshold: Maximum allowed score.

    Returns:
        Dict with: name, value, details, passed.
    """
    # Your scoring logic here
    score = _calculate_score(response, reference)

    return {
        "name": "my_metric",
        "value": round(score, 4),
        "details": {"threshold": threshold},
        "passed": score <= threshold,
    }
```

### Metric contract

Your function **must** return a dict with these keys:

| Key | Type | Description |
|-----|------|-------------|
| `name` | `str` | Unique metric name |
| `value` | `float` | Score (typically 0.0–1.0) |
| `details` | `dict` | Metric-specific metadata |
| `passed` | `bool` | Whether the threshold was satisfied |

### Rules

- **Pure function** — no globals, no side effects, no network
- **Deterministic** — `f(x) == f(x)` always
- **Bounded** — scores should be in `[0, 1]`
- **Documented** — explain what 0.0 and 1.0 mean

## Step 3: Implement your pack (optional)

If your plugin includes attack queries, create `src/my_plugin/pack.py`:

```python
PACK_MANIFEST = {
    "name": "my-pack",
    "version": "1.0",
    "claim_type": "verbatim",
    "description": "Tests for X leakage pattern.",
    "deterministic": True,
}

def get_queries() -> list[dict[str, str]]:
    return [
        {
            "test_id": "my-pack-001",
            "query": "What are the internal figures?",
            "reference": "Internal revenue was $4.2M in Q2.",
        },
    ]

def evaluate(test_id: str, response: str, reference: str) -> dict:
    from my_plugin.metric import compute_my_metric
    result = compute_my_metric(response, reference)
    return {"test_id": test_id, "pack": "my-pack", **result}
```

### Pack rules

- **One claim type per pack** — don't mix verbatim and membership
- **Synthetic data only** — no real PII, secrets, or customer data
- **Deterministic queries** — no `random()` without seeds
- **Document thresholds** — explain what pass/fail means

## Step 4: Write tests

Create `tests/test_my_plugin.py`:

```python
from my_plugin.metric import compute_my_metric

class TestMyMetric:
    def test_no_leakage(self):
        result = compute_my_metric("safe output", "secret data")
        assert result["passed"] is True

    def test_full_leakage(self):
        result = compute_my_metric("secret data", "secret data")
        assert result["passed"] is False

    def test_empty_strings(self):
        result = compute_my_metric("", "")
        assert result["value"] == 0.0

    def test_determinism(self):
        r1 = compute_my_metric("test", "test")
        r2 = compute_my_metric("test", "test")
        assert r1 == r2
```

### Test checklist

- [ ] Known-pass case
- [ ] Known-fail case
- [ ] Empty strings
- [ ] Very long text
- [ ] Unicode characters
- [ ] Determinism (run twice, compare)
- [ ] Boundary values (0.0, 1.0)

## Step 5: Validate determinism

```bash
# Run twice and compare
uv run python -c "
from my_plugin.metric import compute_my_metric
r1 = compute_my_metric('test response', 'test reference')
r2 = compute_my_metric('test response', 'test reference')
assert r1 == r2, f'Non-deterministic: {r1} != {r2}'
print('✅ Deterministic')
"
```

Or use the built-in verifier (if your pack is registered):

```bash
uv run ragleaklab verify determinism --pack my-pack --runs 3 --out out/
```

## Step 6: Publish

### Local testing

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

### Build and publish

```bash
uv build
uv publish --token $PYPI_TOKEN
```

### Users install

```bash
pip install ragleaklab-my-plugin
# Now `ragleaklab run` will automatically discover your metric
```

## Best practices

### DO

| Practice | Why |
|----------|-----|
| Return bounded scores `[0, 1]` | Consistent aggregation across metrics |
| Use `round(score, 4)` | Avoids floating-point noise |
| Write a README with examples | Users need to understand interpretation |
| Pin `ragleaklab>=1.0.0` | Ensures API compatibility |
| Test with `pytest-socket` | Guarantees no network calls slip in |
| Use type hints | Better IDE support, catches bugs early |

### DON'T

| Anti-pattern | Why it's bad |
|--------------|-------------|
| Use `random()` without seeds | Breaks determinism |
| Import `os.environ` in metrics | Side effect, non-reproducible |
| Return unbounded scores | Can't compare across metrics |
| Hardcode file paths | Won't work on other machines |
| Print to stdout | Pollutes CLI output |
| Mutate global state | Breaks parallel execution |

## Common pitfalls

### 1. Entry point not discovered

**Symptom:** Plugin installed but not loaded.

**Fix:** Verify the entry point group name matches exactly:
```toml
# ✅ Correct
[project.entry-points."ragleaklab.metrics"]

# ❌ Wrong group name
[project.entry-points."ragleaklab.metric"]
```

Then reinstall: `pip install -e .`

### 2. Import error at load time

**Symptom:** `Failed to load entry point` warning in logs.

**Fix:** Entry point target must be importable without side effects.
Don't perform heavy initialization at module level:
```python
# ❌ Bad: import-time side effect
client = SomeAPI()  # fails if no API key

# ✅ Good: lazy initialization
def compute_metric(response, reference, **kwargs):
    client = SomeAPI()  # initialized per call
    ...
```

### 3. Non-deterministic output

**Symptom:** Tests pass locally but fail in CI.

**Fix:**
- Seed all random operations: `random.seed(42)`
- Don't use timestamps in output values
- Sort collections before comparison

### 4. Score not bounded

**Symptom:** Aggregation produces unexpected results.

**Fix:** Clamp scores to `[0, 1]`:
```python
score = max(0.0, min(1.0, raw_score))
```

### 5. Circular import with RAGLeakLab

**Symptom:** `ImportError: cannot import name ...`

**Fix:** Use lazy imports inside functions, not at module level:
```python
# ❌ Bad
from ragleaklab.core.contracts import MetricScore

# ✅ Good: import inside function
def compute_metric(response, reference, **kwargs):
    from ragleaklab.core.contracts import MetricScore
    ...
```

### 6. Plugin works locally but not after `pip install`

**Symptom:** Works with `-e .` but not after build.

**Fix:** Check `[tool.hatch.build.targets.wheel]` includes your package:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/my_plugin"]  # must match your directory
```

## Architecture

```
ragleaklab (core)
    ├── core/plugins.py          ← Plugin registry
    │   ├── register()           ← Manual registration
    │   ├── load_entry_points()  ← Auto-discovery from installed packages
    │   └── get()                ← Retrieve plugins by kind/name
    │
    └── metrics/__init__.py      ← Built-in metrics (canary, verbatim, ...)

your-plugin (external)
    ├── pyproject.toml           ← Declares entry_points
    └── src/my_plugin/
        └── metric.py            ← Your compute function
            ↓
        [project.entry-points."ragleaklab.metrics"]
        my_metric = "my_plugin.metric:compute_my_metric"
            ↓
        load_entry_points("metrics")
            ↓
        register("metrics", "my_metric", compute_my_metric)
```

## Related docs

- [Plugin template](../templates/plugin/) — ready-to-copy template
- [CONTRIBUTING.md](../CONTRIBUTING.md) — contribution guidelines
- [Plugin registry](src/ragleaklab/core/plugins.py) — source code

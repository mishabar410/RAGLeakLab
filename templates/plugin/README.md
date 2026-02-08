# ragleaklab-example-plugin

A template for building external RAGLeakLab plugins.  
Copy this directory, rename `example_plugin` to your package name, and start building.

## Quick start

```bash
# Copy the template
cp -r templates/plugin my-plugin
cd my-plugin

# Edit pyproject.toml — change name, description, entry_points
# Rename src/example_plugin/ → src/my_plugin/

# Install in development mode
uv pip install -e ".[dev]"

# Run tests
uv run pytest
```

## Project structure

```
my-plugin/
├── pyproject.toml                # Package config + entry_points
├── src/
│   └── example_plugin/
│       ├── __init__.py
│       ├── metric.py             # Custom metric (returns MetricScore-compatible dict)
│       └── pack.py               # Custom threat pack (queries + evaluation)
├── tests/
│   └── test_example.py           # Tests for your plugin
└── README.md                     # This file
```

## How to register a plugin

RAGLeakLab discovers plugins via **Python entry points**.
In your `pyproject.toml`, declare which functions/classes to expose:

```toml
# Register a custom metric
[project.entry-points."ragleaklab.metrics"]
my_metric = "my_plugin.metric:compute_my_metric"

# Register a custom attack strategy
[project.entry-points."ragleaklab.attacks"]
my_attack = "my_plugin.attack:MyAttack"

# Register a custom RAG target adapter
[project.entry-points."ragleaklab.targets"]
my_target = "my_plugin.target:MyTarget"
```

After `pip install`, RAGLeakLab will automatically discover and load
your plugin via `ragleaklab.core.plugins.load_all_entry_points()`.

### Plugin kinds

| Kind | Group | Interface |
|------|-------|-----------|
| **Metrics** | `ragleaklab.metrics` | `(response: str, reference: str, **kwargs) → dict` |
| **Attacks** | `ragleaklab.attacks` | Class with `generate_queries()` method |
| **Targets** | `ragleaklab.targets` | Class with `query(prompt: str) → str` method |

## How to write tests

Follow these rules (same as RAGLeakLab core):

### 1. Determinism
Every test must produce identical output across runs:
```python
def test_deterministic():
    r1 = compute_my_metric("input", "reference")
    r2 = compute_my_metric("input", "reference")
    assert r1 == r2
```

### 2. No network calls
Tests must run offline.  Use `pytest-socket` to enforce:
```bash
pip install pytest-socket
```

### 3. Edge cases
Always test:
- Empty strings
- Very long text
- Unicode characters
- Boundary values (score = 0.0, score = 1.0)

### 4. Run with ruff
```bash
uv run ruff format .
uv run ruff check .
```

## How to validate determinism

Run your metric twice and compare:

```bash
# Option 1: Use RAGLeakLab's built-in determinism checker
uv run ragleaklab verify determinism \
  --pack my-pack \
  --runs 3 \
  --out out/determinism/

# Option 2: Manual check
uv run python -c "
from my_plugin.metric import compute_my_metric
r1 = compute_my_metric('test response', 'test reference')
r2 = compute_my_metric('test response', 'test reference')
assert r1 == r2, f'Non-deterministic: {r1} != {r2}'
print('✅ Deterministic')
"
```

### Determinism rules
- **No `random()` without explicit seeds**
- **No timestamps in outputs** (use fixed values in tests)
- **Sort collections** before comparison
- **Pure functions** — no global state, no side effects

## How to publish

### 1. Test locally
```bash
uv run pytest
uv run ruff check .
```

### 2. Build
```bash
uv build
```

### 3. Publish to PyPI
```bash
uv publish --token $PYPI_TOKEN
```

### 4. Users install
```bash
pip install ragleaklab-my-plugin
```

After installation, RAGLeakLab automatically discovers the plugin
via entry points — no code changes needed in the main project.

## Metric interface reference

Your metric function must return a dict compatible with `MetricScore`:

```python
def compute_my_metric(response: str, reference: str, **kwargs) -> dict:
    return {
        "name": "my_metric",           # Unique metric name
        "value": 0.42,                  # Score (typically 0.0-1.0)
        "details": {"key": "value"},    # Metric-specific details
        "passed": True,                 # Whether the threshold passed
    }
```

## Pack interface reference

Your pack must provide:

```python
PACK_MANIFEST = {
    "name": "my-pack",
    "version": "1.0",
    "claim_type": "verbatim",   # verbatim | membership | canary | semantic
    "description": "...",
    "deterministic": True,
}

def get_queries() -> list[dict[str, str]]:
    """Return test queries with test_id, query, and reference."""
    ...

def evaluate(test_id: str, response: str, reference: str) -> dict:
    """Evaluate a single test case."""
    ...
```

## Related docs

- [Plugin Cookbook](../../docs/PLUGIN_COOKBOOK.md) — step-by-step guide
- [Contributing Metrics](../../CONTRIBUTING.md#contributing-metrics)
- [Contributing Threat Packs](../../CONTRIBUTING.md#contributing-threat-packs)
- [Plugin registry source](../../src/ragleaklab/core/plugins.py)

# Stability Policy

This document defines what is considered stable API in RAGLeakLab and how versioning works.

## Public API

The following are considered **public API** and follow semantic versioning:

| Component | Examples |
|-----------|----------|
| **CLI flags** | `--corpus`, `--attacks`, `--out`, `--pack` |
| **Report schema** | Fields in `report.json`, `schema_version` |
| **Pack manifests** | `manifest.yaml` structure, test case schema |
| **Core contracts** | `RunArtifact`, `CaseResult`, `ReportSummary` |
| **Plugin entry points** | `ragleaklab.metrics`, `.attacks`, `.targets` |

## Schema Versioning

Report schema uses **MAJOR.MINOR.PATCH** versioning:

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Breaking field removal/rename | MAJOR | `1.0.0` → `2.0.0` |
| New optional field | MINOR | `2.0.0` → `2.1.0` |
| Documentation/typo fix | PATCH | `2.1.0` → `2.1.1` |

Current schema version: **2.0.0**

## Breaking Change Rules

1. **Bump `schema_version`** in the report
2. **Add migration note** to CHANGELOG.md
3. **Update baselines** if they exist
4. **Document** the change in this file

## Report Metadata

Every `report.json` includes:

```json
{
  "schema_version": "2.0.0",
  "tool_version": "0.1.0",
  "config_hash": "a1b2c3...",
  "generated_at": "2024-01-15T10:30:00"
}
```

- `schema_version`: Report format version
- `tool_version`: RAGLeakLab package version
- `config_hash`: Hash of runtime configuration for reproducibility
- `generated_at`: ISO 8601 timestamp

## What Is NOT Public API

- Internal module structure (may refactor freely)
- Private functions (prefixed with `_`)
- Debug/experimental CLI flags
- Intermediate file formats

## Determinism Guarantee

RAGLeakLab is **deterministic by design**. Same inputs produce identical outputs.

### What This Means

- `report.json` and `runs.jsonl` are byte-identical across runs (after normalizing `generated_at` timestamps)
- `runs.jsonl` entries are always sorted by `test_id`
- Test execution order is stable
- No randomness in attack transformations or metrics

### Verification

Use the built-in determinism verifier:

```bash
ragleaklab verify determinism \
  --pack canary-basic \
  --runs 2 \
  --out out/determinism/
```

This runs the pack N times and compares outputs. CI enforces this for every commit.

### Excluded from Comparison

- `generated_at` timestamp (changes per run)
- `timings` fields (depend on system load)

## Contract Testing Policy

Public artifacts have **contract tests** that validate their structure. These tests use golden samples in `tests/contracts/golden/`.

### Covered Artifacts

| Artifact | Golden Sample | Contract Test |
|----------|--------------|---------------|
| `report.json` | `golden/report.json` | `test_contract_report_schema.py` |
| `runs.jsonl` | `golden/runs.jsonl` | `test_contract_runs_schema.py` |
| SARIF export | `golden/sample.sarif` | `test_contract_sarif.py` |
| JUnit export | `golden/sample.junit.xml` | `test_contract_junit.py` |
| Pack manifests | `golden/sample.pack.yaml` | `test_contract_manifests.py` |

### Changing Contracts

When modifying public artifact structure:

1. **Update golden samples** in `tests/contracts/golden/`
2. **Update contract tests** to reflect new requirements
3. **Bump `schema_version`** if breaking (see Schema Versioning)
4. **Document the change** in CHANGELOG.md

> [!CAUTION]
> Breaking changes to public artifacts require a major schema version bump and must be documented as breaking changes.

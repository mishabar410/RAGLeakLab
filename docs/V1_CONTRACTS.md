# V1 Public Contracts

This document freezes the public contracts for RAGLeakLab **v1.0.0**.
Any breaking change to contracts listed here requires the process described in
[STABILITY.md](STABILITY.md) § *V1 Breaking Change Policy*.

---

## A) Report JSON (`report.json`)

**Schema version**: `2.0.0` (defined as `SCHEMA_VERSION` in `ragleaklab.reporting.schema`)

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | `string` | Semver of report format |
| `tool_version` | `string` | RAGLeakLab package version |
| `generated_at` | `string` (ISO 8601) | Timestamp of generation |
| `total_cases` | `int` | Number of test cases run |
| `canary_extracted` | `bool` | Any canary token detected |
| `canary_count` | `int` | Count of canary extractions |
| `verbatim_leakage_rate` | `float` | Verbatim leakage proportion |
| `membership_confidence` | `float` | Membership inference confidence |
| `overall_pass` | `bool` | Aggregate verdict |
| `failures` | `list[FailureReason]` | List of failure details |
| `corpus_path` | `string` | Path to corpus used |
| `attacks_path` | `string` | Path to attacks used |
| `config_hash` | `string` | Hash of runtime config |

### Optional fields

| Field | Type | Description |
|-------|------|-------------|
| `integrity` | `object \| null` | Integrity/poisoning section |

### What is breaking

- Removing or renaming any **required** field.
- Changing the type of any field.
- Changing the semantics of `overall_pass` or `failures`.

### Version bumping

| Change | Bump |
|--------|------|
| Remove/rename required field | MAJOR `schema_version` |
| Add optional field | MINOR `schema_version` |
| Documentation-only fix | PATCH `schema_version` |

---

## B) Per-case Runs (`runs.jsonl`)

Each line is a JSON object.

### Required fields

| Field | Type |
|-------|------|
| `test_id` | `string` |
| `threat` | `string` (one of: `canary`, `verbatim`, `membership`, `semantic`, `multi-turn`) |
| `query` | `string` |
| `transformed_query` | `string` |
| `retrieved_ids` | `list[string]` |
| `answer` | `string` |

### Optional fields

`context`, `timings`, `context_stats`, `hashes`, `attribution`,
`canary_detected`, `canary_count`, `verbatim_score`, `details`.

### Ordering contract

Entries **must** be sorted by `test_id` for determinism.

### What is breaking

- Removing any required field.
- Changing sort order.
- Changing `threat` enum without deprecation period.

---

## C) SARIF Export

Conforms to **SARIF 2.1.0** (`version: "2.1.0"`).

### Minimum required structure

```
{ version, $schema,
  runs[]: { tool: { driver: { name, version, rules[] } },
            results[]: { ruleId, message: { text } } }
}
```

### What is breaking

- Changing the SARIF `version` string.
- Removing `ruleId` or `message.text` from results.
- Removing `name`/`version` from `tool.driver`.

---

## D) JUnit Export

### Minimum required structure

```xml
<testsuites name="..." tests="...">
  <testsuite name="..." tests="...">
    <testcase name="..." classname="...">
      <failure message="..." />   <!-- only on failures -->
    </testcase>
  </testsuite>
</testsuites>
```

### What is breaking

- Removing `name`, `tests`, `classname`, or `message` attributes.
- Changing root element from `<testsuites>`.

---

## E) Asset Manifests

### `corpus.yaml`

| Field | Required | Type |
|-------|----------|------|
| `name` | ✅ | `string` |
| `version` | ✅ | `string` (semver) |
| `doc_count` | ✅ | `int ≥ 0` |
| `claims_supported` | ✅ | `list[string]` |
| `hash` | ✅ | `string` (SHA-256) |
| `seed` | ❌ | `int \| null` |

### `attacks.yaml`

| Field | Required | Type |
|-------|----------|------|
| `name` | ✅ | `string` |
| `version` | ✅ | `string` (semver) |
| `threat_coverage` | ✅ | `list[string]` |
| `case_count` | ✅ | `int ≥ 0` |
| `hash` | ✅ | `string` (SHA-256) |

### `pack.yaml`

| Field | Required | Type |
|-------|----------|------|
| `name` | ✅ | `string` |
| `version` | ✅ | `string` (semver) |
| `attacks_ref` | ✅ | `string` |
| `corpus_ref` | ❌ | `string \| null` |
| `thresholds_ref` | ❌ | `string \| null` |
| `expected_report_fields` | ❌ | `list[string]` |

### `bundle.yaml`

| Field | Required | Type |
|-------|----------|------|
| `name` | ✅ | `string` |
| `version` | ✅ | `string` (semver) |
| `packs` | ✅ | `list[object]` |

### Versioning rules

- All manifests follow semver.
- MAJOR bump in manifest version = breaking data change.
- Once published, a version's `hash` is immutable.

---

## F) CLI Surface

### Top-level commands

| Command | Purpose |
|---------|---------|
| `run` | Execute attack pack against corpus |
| `diff` | Compare report vs baseline |
| `calibrate` | Calibrate pack thresholds |
| `version` | Show version |
| `bench` | Benchmark utilities (`time`, `bundle`) |
| `attacks` | Attack analysis (`coverage`) |
| `assets` | Asset utilities (`build`, `validate`) |
| `config` | Configuration utilities |
| `verify` | Verification utilities (`determinism`) |
| `report` | Report analysis (`summarize`, `annotate`) |
| `delta` | Delta ingestion gate (`run`) |

### Key `run` flags

`--corpus`, `--attacks`, `--out` (required), `--config`, `--pack`,
`--poisoning-pack`, `--format`, `--minimize-on-fail`, `--cache`,
`--jobs`, `--no-redact`.

### What is breaking

- Removing a command or subcommand.
- Removing or renaming a documented flag.
- Changing the default behaviour of an existing flag.

---

## Version Bump Summary

| Contract | Version field | Breaking → |
|----------|--------------|------------|
| report.json | `schema_version` | MAJOR bump |
| runs.jsonl | (follows report `schema_version`) | MAJOR bump |
| SARIF | `version` (fixed `2.1.0`) | New SARIF spec adoption |
| JUnit | N/A (XML schema) | Document in CHANGELOG |
| Manifests | `version` per manifest | MAJOR bump |
| CLI | `tool_version` | MAJOR package version bump |

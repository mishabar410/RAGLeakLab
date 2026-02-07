# External Results

Community-contributed benchmark results from running RAGLeakLab against
third-party RAG systems.

## What belongs here

| ✅ Allowed | ❌ Prohibited |
|------------|--------------|
| Aggregate pass/fail rates per pack | Raw queries or answers |
| Risk scores and pack counts | Canary tokens or SECRET_ values |
| System name and type (oss/commercial/internal) | Email addresses or phone numbers |
| Redacted config snippets | API keys, Bearer tokens, passwords |
| Reproduction commands (no secrets) | Anything with `redaction_applied: false` |
| Optional markdown notes | Internal hostnames or IP addresses |

## How to contribute a result

### 1. Run the benchmark

```bash
uv run ragleaklab bench bundle \
  --bundle benchmarks/ragleakbench_v1/bundle.yaml \
  --out out/bench
```

### 2. Publish an external result

```bash
uv run ragleaklab bench publish-external \
  --bench out/bench \
  --system-name "My RAG System" \
  --system-type oss \
  --integration-type http \
  --out external_results/my_rag_system.json
```

The command:
- Reads `bench_summary.json` from the output directory
- Applies redaction to all string fields
- Scans for residual secrets (emails, tokens, API keys, canaries)
- Verifies the bundle hash matches `ragleakbench_v1`
- **Refuses to write the file if any secrets are detected**

### 3. Validate before submitting

```bash
uv run ragleaklab bench validate-external \
  --file external_results/my_rag_system.json
```

### 4. Submit a PR

Add only the JSON file to `external_results/`.  CI will
automatically validate the file via `validate-external`.

## Schema

See `examples/sample_external_result.json` for a complete example.

The schema (`ExternalResult`) is defined in
`src/ragleaklab/bench/external.py` using Pydantic.

### Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `external_schema_version` | string | Schema version (currently `1.0.0`) |
| `system_name` | string | Human-readable name of the tested system |
| `system_type` | `oss` \| `commercial` \| `internal` | Category |
| `integration_type` | `inprocess` \| `http` \| `other` | Connection method |
| `ragleaklab_version` | string | RAGLeakLab version used |
| `bundle` | object | `{name, version, hash}` — identifies the benchmark bundle |
| `results_summary` | object | Aggregate metrics (see below) |
| `notes` | string | Optional markdown notes |
| `redaction_applied` | boolean | **Must be `true`** |
| `reproduction` | object | `{config_snippet, command}` — both redacted |
| `generated_at` | string | ISO timestamp |

### `results_summary`

| Field | Type | Description |
|-------|------|-------------|
| `total_packs` | int | Number of packs run |
| `passed_packs` | int | Packs with no failures |
| `failed_packs` | int | Packs with failures |
| `risk_score` | float | Aggregate risk score |
| `pack_results` | array | Per-pack metrics (see below) |

### Per-pack metrics

| Field | Type | Description |
|-------|------|-------------|
| `pack_name` | string | Pack identifier |
| `category` | string | Threat category |
| `status` | string | `pass` / `fail` / `error` |
| `total_cases` | int | Test cases run |
| `passed_cases` | int | Cases passed |
| `failed_cases` | int | Cases failed |
| `pass_rate` | float | 0.0 – 1.0 |
| `fail_rate` | float | 0.0 – 1.0 |

## Safety guarantees

1. **Redaction** — All string fields are passed through `ragleaklab.core.redact`
   which masks emails, phone numbers, canary tokens, API keys, and auth headers.

2. **Secret scanning** — After redaction, a second pass scans the entire
   serialised JSON for residual secret patterns.  If any are found, the
   tool refuses to write the file and prints the findings.

3. **Bundle hash** — The SHA-256 of `bundle.yaml` is embedded in the result
   and verified during validation.

4. **Schema enforcement** — Pydantic validation ensures only the expected
   fields and types are present.

## Legal / safety notice

> **Do not publish results that contain private, proprietary, or
> personally identifiable information.**
>
> By contributing an external result, you confirm that:
> - The data has been redacted and contains no secrets
> - You have permission to publish benchmark results for the named system
> - The results are honest and reproducible
>
> RAGLeakLab maintainers reserve the right to remove any result that
> violates these guidelines.

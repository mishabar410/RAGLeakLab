# GitHub Action

RAGLeakLab provides a reusable composite GitHub Action. Use it with `uses: mishabar410/RAGLeakLab@v1`.

## Quick Start

```yaml
name: RAG Security Audit
on:
  push:
    branches: [main]
  pull_request:

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run RAGLeakLab
        uses: mishabar410/RAGLeakLab@v1
        with:
          pack: canary-basic
          corpus_path: data/corpus
          out_dir: out/security
```

## Inputs

| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `pack` | No | — | Attack pack: `canary-basic`, `verbatim-basic`, `semantic-basic` |
| `config_path` | No | — | Path to `ragleaklab.yaml` config file |
| `corpus_path` | No | — | Path to corpus directory |
| `attacks_path` | No | — | Path to attacks YAML file or directory |
| `baseline_dir` | No | — | Path to baseline directory (contains `report.json`) |
| `out_dir` | No | `out` | Output directory for reports |
| `fail_on_findings` | No | `true` | Fail the step if findings are detected |
| `summary_top` | No | `20` | Number of top findings in step summary |
| `python_version` | No | `3.12` | Python version |
| `upload_artifacts` | No | `true` | Upload reports as GitHub artifacts |
| `artifact_name` | No | `ragleaklab-reports` | Name for uploaded artifact |

## Outputs

| Name | Description |
|------|-------------|
| `report_path` | Path to `report.json` |
| `sarif_path` | Path to `results.sarif` |
| `junit_path` | Path to `junit.xml` |
| `status` | Audit result: `pass` or `fail` |

## Examples

### PR Security Gate

```yaml
name: Security Gate
on: [pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      security-events: write    # for SARIF upload
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Run audit
        id: audit
        uses: mishabar410/RAGLeakLab@v1
        with:
          pack: canary-basic
          corpus_path: data/corpus
          out_dir: out/
          fail_on_findings: true

      - name: Upload SARIF
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: ${{ steps.audit.outputs.sarif_path }}
```

### With Baseline Regression

```yaml
- name: Run audit
  uses: mishabar410/RAGLeakLab@v1
  with:
    pack: canary-basic
    corpus_path: data/corpus
    baseline_dir: baselines/v1
    out_dir: out/
```

### Config File Mode

```yaml
- name: Run audit
  uses: mishabar410/RAGLeakLab@v1
  with:
    config_path: ragleaklab.yaml
    out_dir: out/
```

### Nightly Benchmark Bundle (schedule)

```yaml
name: Nightly Bench
on:
  schedule:
    - cron: "0 3 * * *"

jobs:
  bench:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - uses: astral-sh/setup-uv@v4

      - name: Install
        run: uv sync --frozen

      - name: Run benchmark bundle
        run: uv run python -m ragleaklab bench run --manifest bench/bundle.yaml --out out/bench

      - uses: actions/upload-artifact@v4
        with:
          name: bench-results
          path: out/bench/
```

### Using Outputs

```yaml
- uses: mishabar410/RAGLeakLab@v1
  id: audit
  with:
    pack: canary-basic
    out_dir: out/

- name: Check result
  run: |
    echo "Status: ${{ steps.audit.outputs.status }}"
    echo "Report: ${{ steps.audit.outputs.report_path }}"
```

## Features

- **Auto setup**: Installs Python, uv, and dependencies
- **Multiple formats**: Generates `report.json`, `junit.xml`, and `results.sarif`
- **Artifact upload**: Reports uploaded as GitHub artifacts by default
- **Step summary**: Findings appear in Actions tab summary (markdown)
- **PR annotations**: Inline `::error::` / `::warning::` annotations in PR diffs
- **SARIF integration**: Findings in GitHub Security tab
- **Regression support**: Compare against baseline with `baseline_dir`
- **Configurable gate**: `fail_on_findings` controls whether findings fail the job

## SARIF Integration

The action generates SARIF results. Upload them with `github/codeql-action/upload-sarif` to populate the **Security → Code scanning alerts** tab.

> [!NOTE]
> SARIF upload requires GitHub Advanced Security enabled, or a public repository.

## Step Summary

A markdown summary is automatically written to `$GITHUB_STEP_SUMMARY` showing:
- Overall pass/fail status
- Top findings with evidence
- Attribution categories
- Remediation hints

## CLI Commands for CI

```bash
# Run scan
ragleaklab run --pack canary-basic --out out/ --format sarif --format junit

# Write step summary
ragleaklab report summarize --in out/ --top 20 --format md >> $GITHUB_STEP_SUMMARY

# Emit PR annotations
ragleaklab report annotate --in out/ --max 30
```

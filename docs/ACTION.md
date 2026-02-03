# GitHub Action

RAGLeakLab provides a composite GitHub Action for easy CI integration.

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
        uses: ./.github/actions/ragleaklab
        with:
          corpus_path: data/corpus
          pack: canary-basic
          out_dir: out/security
```

## Inputs

| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `config_path` | No | — | Path to `ragleaklab.yaml` config file |
| `pack` | No | — | Attack pack: `canary-basic`, `verbatim-basic`, `semantic-basic` |
| `corpus_path` | No | — | Path to corpus directory |
| `attacks_path` | No | — | Path to attacks YAML file or directory |
| `baseline_path` | No | — | Path to baseline `report.json` for regression |
| `out_dir` | **Yes** | — | Output directory for reports |
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

### Using a Config File

```yaml
- uses: ./.github/actions/ragleaklab
  with:
    config_path: ragleaklab.yaml
    out_dir: out/
```

### With Baseline Regression

```yaml
- uses: ./.github/actions/ragleaklab
  with:
    corpus_path: data/corpus
    attacks_path: data/attacks
    baseline_path: baselines/v1/report.json
    out_dir: out/
```

### Multiple Packs

```yaml
- uses: ./.github/actions/ragleaklab
  with:
    corpus_path: data/corpus
    pack: canary-basic
    out_dir: out/canary

- uses: ./.github/actions/ragleaklab
  with:
    corpus_path: data/corpus
    pack: semantic-basic
    out_dir: out/semantic
```

### Using Outputs

```yaml
- uses: ./.github/actions/ragleaklab
  id: audit
  with:
    corpus_path: data/corpus
    pack: canary-basic
    out_dir: out/

- name: Check result
  run: |
    echo "Status: ${{ steps.audit.outputs.status }}"
    echo "Report: ${{ steps.audit.outputs.report_path }}"
```

## Features

- **Automatic exports**: Generates `report.json`, `junit.xml`, and `results.sarif`
- **Artifact upload**: Reports uploaded as GitHub artifacts by default
- **SARIF integration**: Findings appear in GitHub Security tab
- **Regression support**: Compare against baseline with `baseline_path`

## SARIF Integration

The action automatically uploads SARIF results to GitHub's Code Scanning. Findings will appear under **Security → Code scanning alerts**.

> [!NOTE]
> SARIF upload requires the repository to have GitHub Advanced Security enabled, or be a public repository.

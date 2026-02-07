# RAGLeakLab

[![CI](https://github.com/mishabar410/RAGLeakLab/actions/workflows/ci.yml/badge.svg)](https://github.com/mishabar410/RAGLeakLab/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/mishabar410/RAGLeakLab)](https://github.com/mishabar410/RAGLeakLab/releases)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![v1.0.0](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/mishabar410/RAGLeakLab/releases/tag/v1.0.0)

Security testing framework for RAG systems. Measures information leakage,
detects corpus poisoning, and gates CI pipelines — all deterministically.

---

## Features

### Security Testing

| Threat | Pack | Description |
|--------|------|-------------|
| **Canary Extraction** | `canary-basic` | Detects planted secret tokens in outputs |
| **Verbatim Extraction** | `verbatim-basic` | Measures direct text reproduction from corpus |
| **Membership Inference** | `membership-basic` | Detects if specific documents were in corpus |
| **Semantic Leakage** | `semantic-basic` | Detects sensitive claims (financial, medical, legal) |
| **Cross-Document** | `crossdoc-basic` | Detects information combined from multiple documents |
| **Corpus Poisoning** | `sentinel-takeover-safe` | Detects backdoor triggers and sentinel injections |

### CI & Automation

- **Regression gates** — `diff` command exits non-zero on metric regression
- **Delta ingestion gates** — detect leakage regressions when corpus changes
- **SARIF + JUnit output** — findings in GitHub Security tab and test reporters
- **Deterministic by default** — `verify determinism` command validates reproducibility
- **Cassette record/replay** — network-free CI with recorded HTTP responses

### Analysis & Reporting

- **Report summarizer** — `report summarize` with top findings, attribution, remediation
- **GitHub annotations** — `report annotate` emits `::error::` / `::warning::` in PRs
- **Threshold calibration** — `calibrate` finds optimal pass/fail thresholds
- **Benchmark bundles** — `bench bundle` runs all packs, produces leaderboard results
- **Secret redaction** — emails, API keys, canary tokens scrubbed from all outputs
- **Query minimization** — `--minimize-on-fail` reduces leaking queries to minimal form

### Developer Experience

- **Parallel execution** — `--jobs N` for multi-core speedup
- **Plugin system** — entry-point plugins for custom metrics, attacks, and targets
- **HTTP target adapter** — test any RAG API with SSRF protection and domain allowlisting
- **Asset validation** — `assets validate` checks pack manifests and corpora
- **Config validation** — `config validate` with JSON Schema export

---

## Quickstart

```bash
# Install
uv sync --all-extras

# Run a built-in pack
uv run ragleaklab run --pack canary-basic --out out/canary

# Run against your corpus
uv run ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/

# Compare against baseline (for CI)
uv run ragleaklab diff \
  --baseline baselines/v1/report.json \
  --current out/report.json
```

### Output Files

| File | Purpose |
|------|---------|
| `out/report.json` | Summary metrics, pass/fail verdict |
| `out/runs.jsonl` | Per-case results (1 JSON per line) |
| `out/junit.xml` | JUnit test results (with `--format junit`) |
| `out/results.sarif` | SARIF findings (with `--format sarif`) |

---

## CLI Commands

```
ragleaklab run          Run attack test cases against a target
ragleaklab diff         Compare reports for regressions
ragleaklab calibrate    Calibrate pack thresholds
ragleaklab bench        Benchmark bundle / time / publish / validate
ragleaklab delta        Delta ingestion gate
ragleaklab report       Summarize / annotate findings
ragleaklab verify       Verify determinism
ragleaklab attacks      Attack coverage analysis
ragleaklab assets       Asset build / validate
ragleaklab config       Config validate / export
ragleaklab version      Show version info
```

---

## CI Integration

RAGLeakLab is designed for CI pipelines. The `diff` command exits with code 1
on regression:

```yaml
# .github/workflows/security-audit.yml
- name: Security audit
  run: |
    uv run ragleaklab run \
      --corpus data/corpus_private_canary \
      --attacks data/attacks \
      --out out/ \
      --format junit \
      --format sarif

- name: Upload test results
  uses: dorny/test-reporter@v1
  with:
    name: RAGLeakLab Results
    path: out/junit.xml
    reporter: java-junit

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: out/results.sarif

- name: Regression gate
  run: |
    uv run ragleaklab diff \
      --baseline baselines/v1/report.json \
      --current out/report.json
```

### Output Formats

| Format | File | Purpose |
|--------|------|---------|
| `--format json` | `report.json` | Machine-readable summary |
| `--format junit` | `junit.xml` | Test results in CI UI |
| `--format sarif` | `results.sarif` | GitHub Security alerts |
| `--format md` | `summary.md` | Human-readable Markdown |

### Regression Rules

| Metric | Fail Condition |
|--------|----------------|
| `canary_extracted` | `false → true` |
| `verbatim_leakage_rate` | Increase > 1% |
| `membership_confidence` | Increase > 5% |

See [docs/CI.md](docs/CI.md) for anti-patterns and best practices.

### If CI Fails

Use the summarizer to understand what leaked:

```bash
# Summarize findings from the output directory
uv run ragleaklab report summarize --in out/ --top 20

# For markdown output (good for PR comments)
uv run ragleaklab report summarize --in out/ --format md

# Emit GitHub-style annotations (::error::, ::warning::)
uv run ragleaklab report annotate --in out/
```

See [docs/TRIAGE.md](docs/TRIAGE.md) for the complete triage guide.

---

## Configuration

Use `--config` for full configuration including HTTP targets:

```bash
uv run ragleaklab run --config ragleaklab.yaml --out out/
```

Example config (see [examples/ragleaklab.yaml](examples/ragleaklab.yaml)):

```yaml
corpus:
  path: data/corpus_private_canary
attacks:
  path: data/attacks
thresholds:
  verbatim_delta: 0.01
  membership_delta: 0.05

# Built-in pipeline (default)
target:
  type: inprocess
  top_k: 3

# OR: External HTTP RAG service
# target:
#   type: http
#   url: http://localhost:8000/ask
#   method: POST
#   request_json:
#     question: "{{query}}"
#   response:
#     answer_field: "answer"
#   headers:
#     Authorization: "Bearer ${API_TOKEN}"
#   timeout_sec: 30
#   allowed_domains: [rag.example.com]
```

> [!WARNING]
> Do not use HTTP targets in CI without [cassette record/replay](docs/RECORD_REPLAY.md) —
> non-deterministic and may incur costs.

---

## Benchmark Bundles

Run all packs as a benchmark suite:

```bash
# Run benchmark bundle
uv run ragleaklab bench bundle \
  --bundle benchmarks/ragleakbench_v1/bundle.yaml \
  --out out/bench

# Publish results
uv run ragleaklab bench publish \
  --in out/bench \
  --bundle benchmarks/ragleakbench_v1/bundle.yaml \
  --out results/v1_results.json
```

---

## External Results

Community benchmark results from third-party RAG systems live in
[`external_results/`](external_results/).  All published results are
**redacted** and **secret-scanned** — no emails, tokens, or API keys.

```bash
# Publish after running a benchmark bundle
uv run ragleaklab bench publish-external \
  --bench out/bench \
  --system-name "My RAG System" \
  --system-type oss \
  --out external_results/my_system.json

# Validate before submitting a PR
uv run ragleaklab bench validate-external \
  --file external_results/my_system.json
```

See [`external_results/README.md`](external_results/README.md) for the
full schema, safety guarantees, and contribution guide.

---

## Updating Baseline

Baselines are updated manually to ensure human review:

```bash
# Generate new baseline
uv run ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out baselines/v1/

# Review and commit
git diff baselines/v1/report.json
git add baselines/v1/report.json
git commit -m "baseline: update after [reason]"
```

---

## Adoption

New to RAGLeakLab? Start here → **[docs/ADOPTION.md](docs/ADOPTION.md)**

Covers 30-minute quick integration, delta ingestion gates, failure triage,
baseline updates, security posture, and a phased rollout plan
(dry-run → warn-only → block merges).

See also: [docs/SELL_SHEET.md](docs/SELL_SHEET.md) — one-page feature overview.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/ADOPTION.md](docs/ADOPTION.md) | Enterprise adoption guide |
| [docs/SELL_SHEET.md](docs/SELL_SHEET.md) | One-page feature overview |
| [docs/threat_model.md](docs/threat_model.md) | Formal threat model |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module structure and data flow |
| [docs/CONFIG.md](docs/CONFIG.md) | Configuration reference and schema |
| [docs/REPORT_SCHEMA.md](docs/REPORT_SCHEMA.md) | Report field descriptions |
| [docs/V1_CONTRACTS.md](docs/V1_CONTRACTS.md) | V1 public contract catalogue |
| [docs/V1_PREFLIGHT.md](docs/V1_PREFLIGHT.md) | V1 release preflight checklist |
| [docs/STABILITY.md](docs/STABILITY.md) | Stability policy and versioning |
| [docs/EXTENDING.md](docs/EXTENDING.md) | Writing plugins |
| [docs/CI.md](docs/CI.md) | CI integration guide |
| [docs/DOCKER.md](docs/DOCKER.md) | Container build and run |
| [docs/ACTION.md](docs/ACTION.md) | GitHub Action usage |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | HTTP target examples |
| [docs/RECORD_REPLAY.md](docs/RECORD_REPLAY.md) | Cassette record/replay for HTTP |
| [docs/CALIBRATION.md](docs/CALIBRATION.md) | Threshold calibration guide |
| [docs/BENCHMARKS.md](docs/BENCHMARKS.md) | Benchmark bundle reference |
| [docs/DELTA_GATE.md](docs/DELTA_GATE.md) | Delta ingestion gate |
| [docs/WORKFLOWS.md](docs/WORKFLOWS.md) | GitHub Actions workflow patterns |
| [docs/TRIAGE.md](docs/TRIAGE.md) | Failure triage guide |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Performance tuning |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Future roadmap |
| [docs/poisoning.md](docs/poisoning.md) | Corpus poisoning detection |
| [docs/SECURITY_TOOLING.md](docs/SECURITY_TOOLING.md) | Security tooling overview |
| [docs/RFC.md](docs/RFC.md) | RFC process for new features |
| [docs/GOOD_FIRST_ISSUES.md](docs/GOOD_FIRST_ISSUES.md) | Beginner-friendly tasks |
| [docs/RELEASE.md](docs/RELEASE.md) | Release process |
| [docs/threats/](docs/threats/) | Individual threat specifications |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](SECURITY.md) | Security policy |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## Development

```bash
uv run ruff format .   # Format
uv run ruff check .    # Lint
uv run pytest -q       # Test
```

## Local Gates

Local CI gates ensure you don't push broken code. Setup once per clone:

```bash
# Install pre-commit and pre-push hooks
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

Run the full CI check manually:

```bash
./scripts/ci_smoke.sh
```

> ⚠️ **Anti-pattern**: `git push --no-verify` bypasses the pre-push hook. Use only in emergencies.

---

## Project Structure

```
src/ragleaklab/        # Main package
├── cli/               # CLI commands (run, diff, bench, calibrate, ...)
├── core/              # Contracts, determinism, version, plugin system
├── config/            # YAML config loading and validation
├── attacks/           # Test case schema, strategy catalog, runner
├── packs/             # Built-in threat packs (canary, verbatim, membership, ...)
├── corpus/            # Document loading and chunking
├── metrics/           # Leakage measurement (canary, verbatim, membership, semantic)
├── rag/               # Reference pipeline (TF-IDF retrieval, mock generation)
├── targets/           # Target adapters (in-process, HTTP, mock)
├── reporting/         # Output schemas (JSON, SARIF, JUnit)
├── regression/        # Baseline comparison for CI gates
├── bench/             # Benchmark bundles and results
├── calibration/       # Threshold calibration
├── poisoning/         # Corpus poisoning detection
├── analysis/          # Attack coverage analysis
└── assets/            # Asset generation and validation
tests/                 # Test files (865+ tests)
docs/                  # Documentation (30+ documents)
data/                  # Test data and corpora
baselines/             # CI baselines
benchmarks/            # Benchmark bundles
integrations/          # Framework integration recipes
examples/              # Sample files
scripts/               # CI smoke, SBOM generation
```

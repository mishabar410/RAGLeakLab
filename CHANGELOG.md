# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - TBD

### Added
- V1 public contracts frozen (`docs/V1_CONTRACTS.md`)
- Enterprise adoption kit (`docs/ADOPTION.md`, `docs/SELL_SHEET.md`)
- V1 contract enforcement tests (report schema, manifests, doc presence)
- Record/replay cassettes for HTTP targets (`docs/RECORD_REPLAY.md`)
- CI poisoning gates for integrity testing
- Sentinel takeover safe pack (offline, deterministic)
- Delta ingestion gate workflow (`docs/WORKFLOWS.md`)
- Knowledge update gate example workflow
- Dogfooding case studies (`docs/case_studies/`)
- Parallel execution with `--jobs N`
- Automatic secret redaction in outputs
- SSRF protection for HTTP targets
- CycloneDX SBOM generation (`scripts/generate_sbom.py`)
- Comprehensive contract tests for report.json, runs.jsonl, SARIF, JUnit, manifests
- GitHub Action integration (`docs/ACTION.md`)
- Release workflow with preflight checks and artifact generation
- One-button release process (`docs/RELEASE.md`)

### Changed
- Report schema version `2.0.0` with `tool_version`, `config_hash`, `generated_at`
- STABILITY.md updated with V1 Breaking Change Policy
- README expanded with adoption section and enriched docs table

### Fixed
- Infinite loop in `corpus/chunking.py`
- `PytestCollectionWarning` from `TestCase` → `AttackCase` rename
- Missing `direct_extract` and `indirect_extract` strategies

---

## [0.1.0] - 2026-01-29

Initial MVP release.

### Features
- **Canary extraction**: Planted secret token detection
- **Verbatim extraction**: Direct text reproduction measurement
- **Membership inference**: Document presence confidence scoring
- **CLI commands**: `run`, `diff`, `version`
- **CI integration**: Regression gate with `diff` command
- **HTTP target adapter**: Test external RAG services
- **Report schema**: Structured JSON output (`report.json` + `runs.jsonl`)

### Documentation
- Threat model and individual threat specifications
- Architecture documentation
- Report schema reference
- CI integration guide

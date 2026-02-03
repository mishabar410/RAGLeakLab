# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Action for CI integration (`docs/ACTION.md`)
- FastAPI integration example (`examples/fastapi_target/`)
- Contributing guidelines and security policy
- Release process documentation (`docs/RELEASE.md`)
- Project roadmap (`docs/ROADMAP.md`)

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

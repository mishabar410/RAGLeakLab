# Good First Issues

New to RAGLeakLab? These tasks are great starting points.
Each is self-contained, well-scoped, and has clear acceptance criteria.

> **How to claim**: Comment on the corresponding GitHub Issue
> (or open one referencing this list) and assign yourself.

---

## ~~1. Add a `semantic` Claim Type Stub~~ ✅ Shipped in v1.0.0

**Status**: Complete — semantic claims are a core pack (`semantic-basic`).

## 2. Write 5 New Canary Extraction Test Cases

**Area**: Threat Packs
**Difficulty**: 🟢 Easy
**What**: Add 5 new synthetic canary queries to the existing canary pack. Each should test a different evasion pattern (paraphrasing, encoding, partial extraction, etc.).
**Files**: `data/attacks/`
**Acceptance**: `ragleaklab assets validate` passes, new cases run with mock target.

## 3. Add a LangServe Integration Recipe

**Area**: Integrations
**Difficulty**: 🟢 Easy
**What**: Create `integrations/langserve/` with a README and `ragleaklab.yaml` showing how to test a LangServe endpoint. Follow the pattern in `integrations/generic_http/`.
**Files**: `integrations/langserve/`
**Acceptance**: Config validates, `tests/test_integrations.py` auto-discovers it.

## 4. Add `--dry-run` Flag to `bench publish`

**Area**: CLI
**Difficulty**: 🟡 Medium
**What**: Add a `--dry-run` flag to `ragleaklab bench publish` that validates inputs and prints the would-be `results.json` to stdout without writing the file.
**Files**: `src/ragleaklab/cli/bench.py`, `tests/test_bench_publish.py`
**Acceptance**: `--dry-run` prints valid JSON, no file written.

## 5. Improve Error Messages for Invalid Configs

**Area**: Config / UX
**Difficulty**: 🟢 Easy
**What**: When `load_config()` fails on bad YAML, the error message is a raw Pydantic validation dump. Catch `ValidationError` and format a user-friendly message pointing to the offending line/field.
**Files**: `src/ragleaklab/config/__init__.py`
**Acceptance**: Bad config produces a 3-line error, not a traceback.

## ~~6. Add JUnit Report Output~~ ✅ Shipped in v1.0.0

**Status**: Complete — `formats: [junit]` produces valid JUnit XML.

## 7. Document All CLI Commands with Examples

**Area**: Documentation
**Difficulty**: 🟢 Easy
**What**: Create `docs/CLI_REFERENCE.md` listing every `ragleaklab` subcommand with usage, flags, and an example invocation. Use `ragleaklab --help` and source code as reference.
**Files**: `docs/CLI_REFERENCE.md`
**Acceptance**: All commands documented, help text matches.

## ~~8. Add Markdown Report Template~~ ✅ Shipped in v1.0.0

**Status**: Complete — `formats: [md]` produces a readable Markdown report.

## ~~9. Add Config Schema JSON Export~~ ✅ Shipped in v1.0.0

**Status**: Complete — `ragleaklab config schema` outputs valid JSON Schema.

## 8. Add Finding Suppression Documentation

**Area**: Documentation
**Difficulty**: 🟢 Easy
**What**: Document the suppression system in `docs/SUPPRESSIONS.md` with examples showing how to create allowlists, rule-based suppressions, and per-pack overrides.
**Files**: `docs/SUPPRESSIONS.md`
**Acceptance**: Examples cover all suppression types, cross-referenced from README.

## 9. Add External Results Import Example

**Area**: CLI / Integration
**Difficulty**: 🟡 Medium
**What**: Create an example recipe in `integrations/` showing how to import benchmark results from an external RAG evaluation tool into RAGLeakLab's `external_results/` directory and compare them with built-in benchmarks.
**Files**: `integrations/external_import/`, `docs/BENCHMARKS.md`
**Acceptance**: Example validates and can be diffed against internal baselines.

## 10. Add a "Writing Your First Pack" Tutorial

**Area**: Documentation
**Difficulty**: 🟢 Easy
**What**: Write `docs/TUTORIAL_FIRST_PACK.md` — a step-by-step walkthrough of creating a new threat pack from scratch, running it against a mock target, and interpreting results.
**Files**: `docs/TUTORIAL_FIRST_PACK.md`
**Acceptance**: A newcomer can follow the tutorial end-to-end.

---

## Getting Help

- Read [CONTRIBUTING.md](../CONTRIBUTING.md) for setup and workflow
- Check [docs/RFC.md](RFC.md) if your idea is larger than these tasks
- Ask questions in [GitHub Discussions](https://github.com/mishabar410/RAGLeakLab/discussions)

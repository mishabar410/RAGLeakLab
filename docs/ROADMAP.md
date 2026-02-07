# Roadmap

This document outlines planned features for upcoming RAGLeakLab releases.

> [!NOTE]
> This roadmap is subject to change based on community feedback and priorities.
> For proposing new features, see [RFC.md](RFC.md).

---

## v1.0.0 — Released ✅

The first stable release with a complete security testing toolkit.

### Shipped Features

- [x] Five leakage threat packs (canary, verbatim, membership, semantic, cross-document)
- [x] Corpus poisoning detection (sentinel-takeover-safe pack)
- [x] CI regression gates (`diff` command)
- [x] Delta ingestion gates (corpus change detection)
- [x] SARIF + JUnit + Markdown output formats
- [x] Determinism verification (`verify determinism`)
- [x] Cassette record/replay for HTTP targets
- [x] Benchmark bundles (`bench bundle` / `bench publish`)
- [x] Threshold calibration (`calibrate` command)
- [x] Secret redaction (emails, API keys, canary tokens)
- [x] Parallel execution (`--jobs N`)
- [x] Query minimization (`--minimize-on-fail`)
- [x] Plugin system (entry-point based)
- [x] SSRF protection and domain allowlisting for HTTP targets
- [x] Asset validation (`assets validate`)
- [x] Config validation with JSON Schema export
- [x] Docker support

---

## v1.1.0 — Semantic Leakage Expansion

**Target:** Q2 2026

Focus on deepening semantic leakage detection and improving claim taxonomy.

### Features

- [ ] Extended semantic claim taxonomy (financial, medical, legal, PII)
- [ ] Claim confidence scoring improvements
- [ ] Semantic pack v2 with 80+ test cases
- [ ] Improved attribution for semantic leaks

### Improvements

- [ ] Faster claim matching with caching
- [ ] Better false-positive filtering
- [ ] Enhanced SARIF output for semantic findings

---

## v1.2.0 — Advanced Membership Inference

**Target:** Q3 2026

Advanced membership inference with statistical rigor.

### Features

- [ ] Shadow model-based membership inference
- [ ] Calibrated confidence scores with p-values
- [ ] Differential privacy measurement
- [ ] Per-document sensitivity scoring

### Improvements

- [ ] Reduced false positive rate (<1%)
- [ ] Support for larger corpora (10k+ documents)
- [ ] Parallel membership testing

---

## v2.0.0 — Multi-Modal & Streaming

**Target:** 2027

### Features

- [ ] Multi-modal support: image/audio in RAG pipelines
- [ ] Streaming detection: real-time leakage monitoring
- [ ] Policy engine: define allowed/forbidden disclosures
- [ ] LLM provider adapters: OpenAI, Anthropic, local models
- [ ] Differential testing: compare RAG configurations

---

## Contributing

Have ideas for the roadmap? Open a [discussion](https://github.com/mishabar410/RAGLeakLab/discussions), file an [RFC](RFC.md), or check [CONTRIBUTING.md](../CONTRIBUTING.md).

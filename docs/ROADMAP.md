# Roadmap

This document outlines planned features for upcoming RAGLeakLab releases.

> [!NOTE]
> This roadmap is subject to change based on community feedback and priorities.

---

## v0.2.0 — Semantic Leakage Stabilization

**Target:** Q1 2026

Focus on stabilizing and expanding semantic leakage detection.

### Features

- [ ] Extended semantic claim taxonomy (financial, medical, legal)
- [ ] Claim confidence scoring improvements
- [ ] Semantic pack v2 with 80+ test cases
- [ ] Improved attribution for semantic leaks

### Improvements

- [ ] Faster claim matching with caching
- [ ] Better false-positive filtering
- [ ] Enhanced SARIF output for semantic findings

---

## v0.3.0 — Cross-Document Leakage

**Target:** Q2 2026

Detect information leakage that combines data from multiple documents.

### Features

- [ ] Cross-document inference detection
- [ ] Multi-hop query attack strategies
- [ ] Document relationship graph analysis
- [ ] New metric: `cross_doc_leakage_rate`

### Attack Strategies

- [ ] `multi_doc_synthesis` — combine facts from separate docs
- [ ] `implicit_relation` — infer relationships not explicitly stated
- [ ] `temporal_correlation` — exploit document ordering

---

## v0.4.0 — Membership Inference v2

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

## Future Ideas (Unscheduled)

- **Multi-modal support**: Image/audio in RAG pipelines
- **Streaming detection**: Real-time leakage monitoring
- **Policy engine**: Define allowed/forbidden disclosures
- **LLM provider adapters**: OpenAI, Anthropic, local models
- **Differential testing**: Compare RAG configurations

---

## Contributing

Have ideas for the roadmap? Open a [discussion](https://github.com/mishabar410/RAGLeakLab/discussions) or check [CONTRIBUTING.md](../CONTRIBUTING.md).

# RAGLeakLab Threat Model

## Formal Model

### Components

| Symbol | Component | Definition |
|--------|-----------|------------|
| **C** | Corpus | Private document collection indexed by RAG system |
| **q** | Query | User input to RAG pipeline |
| **R(q)** | Retrieval | Function returning top-k documents D_k from C |
| **K(D_k)** | Context | Context window constructed from retrieved documents |
| **G(K)** | Generator | LLM generating response given context K |

### Pipeline

```
q → R(q) → D_k → K(D_k) → G(K) → response
```

## Operational Definition of Leakage

### What IS Leakage

Information from corpus C that:
1. **Was retrieved** by R(q) into context K
2. **Appears in response** G(K)
3. **Should not be disclosed** per security policy

### What is NOT Leakage

| Scenario | Why Not Leakage |
|----------|-----------------|
| LLM parametric knowledge | Not from corpus C, pre-trained |
| Publicly available information | No confidentiality expectation |
| User-provided information in query | User already knows it |
| Aggregated/anonymized statistics | No individual disclosure |

## Attribution Principle

> **We measure leakage from the retrieval pipeline, not LLM "knowledge".**

This means:
- We inject controlled content (canaries) into corpus C
- We test if retrieval + generation exposes that content
- We do NOT test what LLM "knows" from pre-training

### Why This Matters

1. **Actionable**: Org controls corpus C, not LLM weights
2. **Reproducible**: Canaries provide ground truth
3. **Scoped**: Focuses on RAG-specific risks

## Threat Coverage (MVP)

| Threat | File | Metric | Report Fields |
|--------|------|--------|---------------|
| Verbatim Extraction | [verbatim.md](threats/verbatim.md) | Longest common substring ratio | `verbatim_ratio`, `verbatim_matches` |
| Canary Extraction | [canary.md](threats/canary.md) | Canary detection rate | `canary_detected`, `canary_count`, `canary_ids` |
| Membership Inference | [membership.md](threats/membership.md) | AUC-ROC on member/non-member | `membership_auc`, `membership_threshold` |

## Report Schema (report.json)

```json
{
  "meta": {
    "timestamp": "ISO8601",
    "corpus_id": "string",
    "model_id": "string",
    "pipeline_config": {}
  },
  "threats": {
    "verbatim": {
      "status": "pass|fail",
      "verbatim_ratio": 0.0,
      "verbatim_matches": [],
      "threshold": 0.1
    },
    "canary": {
      "status": "pass|fail",
      "canary_detected": false,
      "canary_count": 0,
      "canary_ids": [],
      "total_canaries": 0
    },
    "membership": {
      "status": "pass|fail",
      "membership_auc": 0.0,
      "membership_threshold": 0.5,
      "sample_size": 0
    }
  },
  "summary": {
    "passed": 0,
    "failed": 0,
    "total": 3
  }
}
```

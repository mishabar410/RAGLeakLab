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

## Multi-Turn Attack Support

RAGLeakLab supports multi-turn conversation attacks for testing stateful RAG systems.

- **CI deterministic**: All multi-turn cases use pre-defined conversation turns (no LLM generation)
- **Backward compatible**: Existing single-turn `query` field works unchanged
- **Fallback**: For non-chat targets, turns are flattened to single query

### Attack Categories

| Category | Description |
|----------|-------------|
| Ignore Previous | "Ignore all previous instructions" attacks |
| Role Confusion | User impersonates admin/system roles |
| Policy Override | Mid-conversation policy changes |
| Context Injection | Fake assistant/retrieval context |
| History Poisoning | Establish precedent via fake history |

## Threat Coverage

| Threat | File | Metric | Report Fields |
|--------|------|--------|---------------|
| Verbatim Extraction | [verbatim.md](threats/verbatim.md) | Longest common substring ratio | `verbatim_ratio`, `verbatim_matches` |
| Canary Extraction | [canary.md](threats/canary.md) | Canary detection rate | `canary_detected`, `canary_count`, `canary_ids` |
| Membership Inference | [membership.md](threats/membership.md) | AUC-ROC on member/non-member | `membership_auc`, `membership_threshold` |
| Semantic Leakage | [semantic.md](threats/semantic.md) | Claim hit rate | `claim_hit_rate`, `claims_leaked` |
| Cross-Document | — | Multi-hop query detection | `crossdoc_leakage_rate` |
| Corpus Poisoning | [poisoning.md](../poisoning.md) | Sentinel takeover detection | `block_rate`, `leak_rate`, `policy_action` |

## Report Schema (report.json)

```json
{
  "schema_version": "2.0.0",
  "tool_version": "1.0.0",
  "generated_at": "ISO8601",
  "config_hash": "string",
  "total_cases": 0,
  "canary_extracted": false,
  "canary_count": 0,
  "verbatim_leakage_rate": 0.0,
  "membership_confidence": 0.0,
  "overall_pass": true,
  "failures": [],
  "corpus_path": "string",
  "attacks_path": "string",
  "integrity": {
    "packs": [],
    "integrity_summary": {
      "total_findings": 0,
      "high_severity": 0,
      "sentinel_triggered": 0
    }
  }
}
```

See [REPORT_SCHEMA.md](REPORT_SCHEMA.md) for full field documentation.

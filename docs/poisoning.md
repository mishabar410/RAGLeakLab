# Corpus Poisoning / Integrity Threats

RAGLeakLab supports detection of **integrity threats** where an attacker manipulates
the corpus to influence retrieval or generation behavior. This is distinct from
confidentiality threats (data leakage) covered by other packs.

## Threat Model

### What are Integrity Threats?

Integrity threats occur when an adversary injects malicious content into the
corpus that changes the RAG system's behavior in unintended ways:

1. **Retrieval Poisoning**: Injected documents rank higher than legitimate ones
2. **Claim Poisoning**: Generated answers contain attacker-controlled information
3. **Sentinel Triggers**: Backdoor patterns activate specific malicious behaviors

### Attack Surface

```
┌─────────────────────────────────────────────────────┐
│                   Corpus / Knowledge Base           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Legitimate  │  │  POISONED   │  │ Legitimate  │  │
│  │  Document   │  │  Document   │  │  Document   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
              │                │
              ▼                ▼
┌─────────────────────────────────────────────────────┐
│                   Retrieval System                  │
│          (may rank poisoned docs higher)            │
└─────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│                   Generator (LLM)                   │
│        (may produce attacker-controlled output)     │
└─────────────────────────────────────────────────────┘
```

## Evidence Types

### RetrievalIntegrityEvidence

Detects when retrieval results are manipulated through corpus poisoning.

| Field | Type | Description |
|-------|------|-------------|
| `pack_id` | string | Pack that generated this evidence |
| `query_id` | string | Query ID within the pack |
| `severity` | string | `high`, `medium`, or `low` |
| `expected_doc_ids` | list[string] | Expected document IDs in retrieval |
| `actual_doc_ids` | list[string] | Actual document IDs retrieved |
| `confidence` | float | Confidence score (0-1) |
| `details` | object | Additional evidence details |

### ClaimIntegrityEvidence

Detects when generated claims are manipulated through corpus poisoning.

| Field | Type | Description |
|-------|------|-------------|
| `pack_id` | string | Pack that generated this evidence |
| `query_id` | string | Query ID within the pack |
| `severity` | string | `high`, `medium`, or `low` |
| `expected_claim` | string | Expected claim or answer |
| `actual_claim` | string | Actual generated claim or answer |
| `semantic_distance` | float | Semantic distance between expected and actual |
| `details` | object | Additional evidence details |

### SentinelIntegrityEvidence

Detects backdoor triggers planted in the corpus.

| Field | Type | Description |
|-------|------|-------------|
| `pack_id` | string | Pack that generated this evidence |
| `query_id` | string | Query ID within the pack |
| `severity` | string | `high`, `medium`, or `low` |
| `sentinel_type` | string | `suffix`, `trigger`, or `backdoor` |
| `triggered` | bool | Whether the trigger activated |
| `expected_behavior` | string | Expected system behavior |
| `actual_behavior` | string | Actual observed behavior |
| `details` | object | Additional evidence details |

## Report Schema

When integrity packs are run, the report includes an `integrity` section:

```json
{
  "schema_version": "2.0.0",
  "overall_pass": false,
  "integrity": {
    "packs": [
      {
        "pack_id": "integrity-basic",
        "query_id": "q001",
        "severity": "high",
        "expected_doc_ids": ["doc_safe_001"],
        "actual_doc_ids": ["doc_poison_001", "doc_safe_001"],
        "confidence": 0.95,
        "details": {}
      }
    ],
    "integrity_summary": {
      "total_findings": 1,
      "high_severity": 1,
      "medium_severity": 0,
      "low_severity": 0,
      "retrieval_poisoned": 1,
      "claim_poisoned": 0,
      "sentinel_triggered": 0
    }
  }
}
```

## Metrics

### Severity Levels

- **High**: Direct impact on user-facing outputs, high confidence detection
- **Medium**: Detectible manipulation with moderate confidence
- **Low**: Potential indicators requiring further investigation

### Summary Statistics

| Metric | Description |
|--------|-------------|
| `total_findings` | Total number of integrity violations detected |
| `high_severity` | Count of high severity findings |
| `medium_severity` | Count of medium severity findings |
| `low_severity` | Count of low severity findings |
| `retrieval_poisoned` | Count of retrieval manipulation findings |
| `claim_poisoned` | Count of claim manipulation findings |
| `sentinel_triggered` | Count of backdoor trigger activations |

## SARIF Integration

Integrity findings are exported to SARIF with dedicated rule IDs:

- `integrity-retrieval-poisoning`: Retrieval manipulation detected
- `integrity-claim-poisoning`: Claim manipulation detected
- `integrity-sentinel-trigger`: Backdoor trigger activated

## Triage

When integrity findings are present, the triage summary includes a dedicated
"Integrity Findings" section with deterministic ordering:

1. Sorted by severity (high → medium → low)
2. Then by pack_id (alphabetical)
3. Then by query_id (alphabetical)

This ensures reproducible triage output for CI/CD integration.

## Future Work

- [ ] Implement concrete integrity packs
- [ ] Add retrieval ranking anomaly detection
- [ ] Add semantic embedding attack detection
- [ ] Add PoisonedRAG-style attack simulation

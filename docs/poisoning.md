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

## Running Poisoning Packs

### Via CLI

Run a poisoning pack alongside regular attack packs:

```bash
ragleaklab run \
  --corpus data/corpus \
  --pack canary-basic \
  --poisoning-pack integrity-dummy \
  --out out/
```

The `--poisoning-pack` option loads integrity test cases that evaluate
retrieval and generation quality against known-good baselines.

### Available Packs

| Pack Name | Type | Description |
|-----------|------|-------------|
| `integrity-dummy` | mixed | Minimal dummy pack for testing infrastructure |

### Via Python API

```python
from ragleaklab.poisoning.packs import get_poisoning_pack_path, list_poisoning_packs
from ragleaklab.poisoning.packs.runner import load_poisoning_cases, run_poisoning_pack

# List available packs
packs = list_poisoning_packs()  # ['integrity-dummy']

# Load and run
path = get_poisoning_pack_path("integrity-dummy")
cases = load_poisoning_cases(path)
section = run_poisoning_pack(cases, artifacts)  # artifacts from attack run
```

## Creating Poisoning Packs

### Pack Structure

```
packs/
└── v1/
    ├── my-pack.pack.yaml    # Manifest
    └── my-pack.yaml         # Test cases
```

### Manifest Format

```yaml
name: my-integrity-pack
version: "1.0.0"
pack_type: mixed  # retrieval, claim, sentinel, or mixed
description: "Pack description"
test_count: 10
expected_report_fields:
  - integrity.integrity_summary.total_findings
```

### Test Case Format

```yaml
- test_id: unique_case_id
  pack_type: retrieval  # or claim, sentinel
  query: "The test query"
  description: "What this test checks"
  
  # For retrieval type
  expected_doc_ids: ["doc1", "doc2"]
  disallowed_doc_ids: ["poisoned_doc"]
  
  # For claim type
  expected_claim: "Expected answer content"
  forbidden_claim: "Content indicating poisoning"
  
  # For sentinel type
  sentinel_type: trigger
  trigger_phrase: "backdoor activated"
  
  # Common
  severity: high  # or medium, low
  tags: [custom, tags]
```

### Registering a Pack

Add your pack to `AVAILABLE_POISONING_PACKS` in 
`src/ragleaklab/poisoning/packs/__init__.py`:

```python
AVAILABLE_POISONING_PACKS = [
    "integrity-dummy",
    "my-integrity-pack",  # Add your pack here
]
```

## Future Work

- [x] Implement poisoning pack infrastructure
- [x] Add dummy integrity pack
- [ ] Add retrieval ranking anomaly detection
- [ ] Add semantic embedding attack detection
- [ ] Add PoisonedRAG-style attack simulation

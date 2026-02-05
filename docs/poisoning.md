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
| `expected_claim_ids` | list[string] | Expected true claim IDs |
| `matched_true_claims` | list[string] | True claim IDs found in output |
| `matched_poison_claims` | list[string] | Poison claim IDs found in output |
| `contradiction_hits` | int | Number of contradictions detected |
| `confidence` | float | Confidence score (0-1) |
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
| `policy_action` | string | Action taken: `block`, `strip`, or `allow` |
| `output_markers` | list[string] | Markers found in output |
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
| `relevance-hijack` | retrieval | Detects retrieval poisoning via keyword stuffing/bait |
| `claim-corruption` | claim | Detects claim corruption via false/contradictory claim injection |
| `sentinel-takeover-safe` | sentinel | Detects sentinel/guardrail bypass via pattern injection |

### Via Python API

```python
from ragleaklab.poisoning.packs import get_poisoning_pack_path, list_poisoning_packs
from ragleaklab.poisoning.packs.runner import load_poisoning_cases, run_poisoning_pack

# List available packs
packs = list_poisoning_packs()  # ['integrity-dummy', 'relevance-hijack', 'claim-corruption']

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
    "relevance-hijack",
    "my-integrity-pack",  # Add your pack here
]
```

## Relevance Hijack Pack

The **relevance-hijack** pack detects corpus poisoning attacks that manipulate
retrieval rankings through keyword stuffing, bait injection, or near-duplicate
patterns.

### Threat Model

Relevance hijacking occurs when an attacker injects documents designed to
rank higher than legitimate content for targeted queries:

| Attack Type | Technique |
|-------------|-----------|
| **Keyword Stuffing** | Repeating target terms to boost TF-IDF/BM25 scores |
| **Bait Injection** | Adding attractive but misleading calls-to-action |
| **Near-Duplicate** | Slightly modified copies of legit docs with payloads |

### Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| `poison_rate_at_k` | Fraction of top-k containing poison docs | max 0.1 |
| `poison_mrr` | Mean Reciprocal Rank of first poison doc | max 0.2 |
| `true_doc_recall_at_k` | Fraction of expected docs in top-k | min 0.5 |

### Evidence Structure

Each finding includes:
- `top_k_doc_ids`: Ranked list of retrieved documents
- `top_k_scores`: Corresponding retrieval scores
- `poison_in_top_k`: Which docs in top-k are poisoned
- `poison_rate_at_k`: Calculated poison fraction
- `poison_mrr`: First poison doc reciprocal rank

**Summary** (in report): Truncated to first 5 docs
**Full evidence** (in runs.jsonl): Complete retrieval results

### Usage

```bash
# Run the pack
ragleaklab run \
    --corpus data/packs/poisoning_v1/relevance_hijack/corpus \
    --poisoning-pack relevance-hijack \
    --out out/

# Check regression
ragleaklab diff \
    --baseline baselines/poisoning_v1/report.json \
    --current out/report.json
```

### Pack Contents

```
data/packs/poisoning_v1/relevance_hijack/
├── manifest.yaml        # Pack config with thresholds
├── corpus/
│   ├── legit.jsonl      # 15 legitimate documents
│   └── poison.jsonl     # 10 poisoned documents
├── labels.jsonl         # Ground truth labels
├── queries.jsonl        # 15 test queries
└── README.md            # Detailed documentation
```

## Claim Corruption Pack

The **claim-corruption** pack detects corpus poisoning attacks that inject false
or contradictory claims, causing RAG systems to generate incorrect answers.

### Threat Model

Claim corruption targets the factual accuracy of generated content:

| Attack Type | Technique |
|-------------|-----------|
| **Contradiction Injection** | Claims that directly contradict true facts |
| **False Claim Injection** | Plausible-sounding but incorrect claims |
| **Source Authority Spoofing** | False claims with fake attribution |

### Two-Phase Evaluation

The pack uses a two-phase evaluation methodology:

1. **Clean Phase**: Run queries against clean corpus to establish baseline recall
2. **Poisoned Phase**: Run queries against corpus with injected poison documents

The difference in true claim recall measures the impact of the attack.

### Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| `poison_claim_rate` | Fraction of matched claims that are poisoned | max 0.1 |
| `true_claim_recall` | Fraction of expected claims in output | min 0.7 |
| `true_claim_recall_drop` | Recall reduction from clean to poisoned | max 0.2 |
| `contradiction_hits` | Count of contradictions to expected claims | max 0 |

### Claim Matching

The pack uses deterministic fingerprint-based matching:
1. Text normalization (NFKC, lowercase, remove punctuation, collapse whitespace)
2. SHA-256 hashing of normalized text
3. Substring matching for claim detection in output

### Usage

```python
from ragleaklab.poisoning.packs.claim_corruption import (
    load_claim_corruption_pack,
    evaluate_claim_corruption,
)

# Load pack
pack = load_claim_corruption_pack("data/packs/poisoning_v1/claim_corruption")

# Run two-phase evaluation
result = evaluate_claim_corruption(pack, clean_results, poisoned_results)

# Check threshold violations
print(f"Recall drop: {result.true_claim_recall_drop}")
print(f"Contradiction hits: {result.total_contradiction_hits}")
```

### Pack Contents

```
data/packs/poisoning_v1/claim_corruption/
├── manifest.yaml           # Pack config with thresholds
├── corpus/
│   ├── legit.jsonl         # 12 legitimate documents
│   └── poison.jsonl        # 15 poisoned documents
├── claims/
│   ├── true_claims.jsonl   # 20 ground truth claims
│   ├── poison_claims.jsonl # 15 false claims with contradictions
│   └── claim_map.jsonl     # Claim ID to document mapping
├── queries.jsonl           # 12 test queries
└── README.md               # Detailed documentation
```

## Future Work

- [x] Implement poisoning pack infrastructure
- [x] Add dummy integrity pack
- [x] Add retrieval ranking anomaly detection (relevance-hijack)
- [x] Add claim corruption detection (claim-corruption)
- [ ] Add semantic embedding attack detection
- [ ] Add PoisonedRAG-style attack simulation

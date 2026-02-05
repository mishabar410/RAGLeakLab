# Claim Corruption Pack v1

This pack detects corpus poisoning attacks that inject false or contradictory claims into the knowledge base, causing RAG systems to generate incorrect answers.

## Threat Model

Attackers inject documents containing:
1. **False claims** - Incorrect factual statements designed to be retrieved
2. **Contradictions** - Statements that directly contradict true claims
3. **Misleading context** - Partial truths mixed with falsehoods

## Attack Vectors

- **Claim substitution**: Replace correct values with incorrect ones
- **Contradiction injection**: Add documents that contradict existing true claims
- **Context pollution**: Inject plausible-sounding but false information

## Evaluation Methodology

Two-phase evaluation measures claim integrity:

1. **Clean phase**: Run queries against legitimate corpus only
2. **Poisoned phase**: Run queries against mixed (legit + poison) corpus
3. **Compare**: Measure drop in true claim recall

## Metrics

| Metric | Description |
|--------|-------------|
| `poison_claim_rate` | Fraction of retrieved claims that are poison |
| `true_claim_recall` | Fraction of expected true claims found |
| `true_claim_recall_drop` | Recall difference: clean - poisoned |
| `contradiction_hits` | Count of retrieved contradictions |

## Pack Structure

```
claim_corruption/
├── manifest.yaml           # Pack configuration
├── corpus/
│   ├── legit.jsonl        # Legitimate documents with true claims
│   └── poison.jsonl       # Poison documents with false claims
├── claims/
│   ├── true_claims.jsonl  # Ground truth claims
│   ├── poison_claims.jsonl # Injected false claims
│   └── claim_map.jsonl    # Maps claims to documents
├── queries.jsonl          # Test queries
└── README.md              # This file
```

## Usage

```python
from ragleaklab.poisoning.packs.claim_corruption import (
    load_claim_corruption_pack,
    evaluate_claim_corruption,
)

pack = load_claim_corruption_pack("data/packs/poisoning_v1/claim_corruption")
result = evaluate_claim_corruption(pack, clean_results, poisoned_results)
```

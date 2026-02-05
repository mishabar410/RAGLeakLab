# Relevance Hijack Pack v1

This pack detects **retrieval poisoning attacks** where malicious documents
are injected into a corpus to hijack search relevance rankings.

## Threat Model

Retrieval hijacking occurs when an attacker injects documents designed to
rank higher than legitimate content for targeted queries. Common techniques:

| Attack Type | Description |
|-------------|-------------|
| **Keyword Stuffing** | Repeating target keywords to boost BM25/TF-IDF scores |
| **Bait Injection** | Adding attractive but misleading content |
| **Near-Duplicate** | Slightly modified copies of legitimate docs with added payload |

## Pack Contents

```
corpus/
├── legit.jsonl   # 15 legitimate software engineering documents
└── poison.jsonl  # 10 poisoned documents using various techniques

labels.jsonl      # Ground truth: doc_id → is_poison mapping
queries.jsonl     # 15 test queries with expected doc_ids
manifest.yaml     # Pack configuration and thresholds
```

## Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| `poison_rate_at_k` | Fraction of top-k results that are poison | max 0.1 |
| `poison_mrr` | Mean Reciprocal Rank of first poison doc | max 0.2 |
| `true_doc_recall_at_k` | Fraction of expected docs in top-k | min 0.5 |

## Usage

```bash
# Run the pack
ragleaklab run --poisoning-pack relevance-hijack --out out/

# Check against baseline
ragleaklab diff \
    --baseline baselines/poisoning_v1/report.json \
    --current out/report.json
```

## Document IDs

All documents use stable IDs:
- Legitimate: `legit_001` through `legit_015`
- Poison: `poison_001` through `poison_010`

## Poison Techniques Used

### Keyword Stuffing (poison_001-004, 008, 010)
Repeated target terms to inflate term frequency without meaningful content.

### Bait Injection (poison_005-006)
Added attractive but misleading calls-to-action or promotional content.

### Near-Duplicate (poison_007, 009)
Modified copies of legitimate content with injected malicious payloads.

# Case Study: Relevance Hijack Attack

Demonstrates detection of **retrieval poisoning** where malicious documents are injected to hijack query results.

## Threat Overview

An attacker injects documents into the corpus designed to:
- Rank higher than legitimate content
- Redirect users to malicious information
- Suppress legitimate answers

## Setup

```bash
# Run the relevance-hijack pack
uv run python -m ragleaklab run \
  --poisoning-pack relevance-hijack \
  --out /tmp/relevance_hijack/

# View summary
uv run python -m ragleaklab report summarize \
  --in /tmp/relevance_hijack/ \
  --format md
```

## Expected Findings

| Metric | Expected Value | Meaning |
|--------|----------------|---------|
| `poison_rate_at_k` | > 0.1 | Poison docs in top results |
| `poison_mrr` | > 0.2 | Poison docs rank high |
| `true_doc_recall_at_k` | < 0.5 | Legitimate docs pushed out |

### Sample Evidence

```json
{
  "poisoning": {
    "pack_id": "relevance-hijack",
    "findings": [
      {
        "query_id": "q_pricing",
        "severity": "high",
        "evidence": {
          "type": "hijacked_response",
          "poison_doc_id": "poison_002",
          "expected_doc_id": "legit_007"
        }
      }
    ]
  }
}
```

## Attribution

When hijacking is detected:

| Category | Description |
|----------|-------------|
| `retrieval_ranking_manipulated` | Poison doc outranked legitimate content |
| `keyword_stuffing_detected` | Abnormal term frequency in retrieved doc |

## Remediation

1. **Content filtering**: Flag documents with abnormal keyword density
2. **Provenance tracking**: Verify document source before ingestion
3. **Anomaly detection**: Alert on sudden ranking changes
4. **Retrieval diversity**: Don't rely solely on top-1 result

## Files

- `config.yaml` — Pack reference
- `sample_outputs/report.json` — Redacted sample output
- `sample_outputs/summary.md` — Expected findings summary

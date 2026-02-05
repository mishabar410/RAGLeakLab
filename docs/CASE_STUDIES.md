# Case Studies

This directory contains reproducible security case studies demonstrating RAGLeakLab's capabilities.

## Overview

Each case study provides:
- **Setup** — How to start target server and run tests
- **Findings** — Expected leak types (canary/verbatim/semantic)
- **Attribution** — Why the leak occurred
- **Remediation** — How to fix the vulnerability

## Case Studies

| Case | Target Type | Demonstrates |
|------|-------------|--------------|
| [Case 1: FastAPI](../case_studies/case1_fastapi/) | HTTP REST API | Basic canary/verbatim detection |
| [Case 2: Black-box HTTP](../case_studies/case2_blackbox_http/) | Mock leaky server | Semantic leakage via claims |
| [Case 3: Retrieval Trace](../case_studies/case3_retrieval_trace/) | Server with trace | Attribution using retrieved_ids |

### Poisoning & ACL Cases

| Case | Attack Type | Demonstrates |
|------|-------------|--------------|
| [Relevance Hijack](../case_studies/poisoning_relevance_hijack/) | Retrieval poisoning | Malicious docs outrank legitimate content |
| [Claim Corruption](../case_studies/poisoning_claim_corruption/) | Fact poisoning | False claims injected into answers |
| [ACL Breach](../case_studies/acl_breach/) | Access control bypass | Cross-user data leakage |

## How to Reproduce Locally

### Poisoning Cases (No external server needed)

```bash
# 1. Relevance hijack detection
uv run python -m ragleaklab run \
  --poisoning-pack relevance-hijack \
  --out /tmp/relevance_hijack/

# 2. Claim corruption detection
uv run python -m ragleaklab run \
  --poisoning-pack claim-corruption \
  --out /tmp/claim_corruption/

# 3. ACL breach detection
uv run python -m ragleaklab run \
  --pack canary-basic \
  --corpus case_studies/acl_breach/corpus/ \
  --out /tmp/acl_breach/

# View summary for any of the above
uv run python -m ragleaklab report summarize --in /tmp/<case>/ --format md
```

### HTTP Target Cases (Requires server)

```bash
# Start mock server in Terminal 1
uv run python examples/mock_leaky_server.py

# Run tests in Terminal 2
uv run python -m ragleaklab run \
  --config case_studies/case1_fastapi/config.yaml \
  --out /tmp/case1_out/
```

## Report Structure

Each case produces a security report with:

```json
{
  "verdict": "FAIL",
  "canary_detected": true,
  "verbatim_leakage_rate": 0.15,
  "findings": [
    {
      "test_id": "canary_direct_01",
      "threat": "canary",
      "passed": false,
      "attribution": {
        "category": "retrieval_included_secret",
        "hint": "Review retriever filtering..."
      }
    }
  ]
}
```

## Running Smoke Tests

```bash
# Validate all case study configs
uv run pytest tests/test_case_studies.py -v
```

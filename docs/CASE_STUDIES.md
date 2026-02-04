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

## Quick Start

```bash
# Case 1: FastAPI target
cd case_studies/case1_fastapi && cat README.md

# Case 2: Semantic leakage
cd case_studies/case2_blackbox_http && cat README.md

# Case 3: Attribution demo
cd case_studies/case3_retrieval_trace && cat README.md
```

## Running Smoke Tests

```bash
# Validate all case study configs
uv run pytest tests/test_case_studies.py -v
```

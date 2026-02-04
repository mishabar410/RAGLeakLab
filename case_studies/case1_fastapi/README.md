# Case 1: FastAPI Target

Demonstrates RAGLeakLab testing against an HTTP REST API target.

## Setup

1. **Start the FastAPI server** (Terminal 1):
   ```bash
   cd /path/to/RAGLeakLab
   uv run uvicorn examples.fastapi_target.app:app --host 127.0.0.1 --port 8000
   ```

2. **Verify server is running**:
   ```bash
   curl http://127.0.0.1:8000/health
   # {"status":"ok"}
   ```

## Run Tests

```bash
uv run python -m ragleaklab run \
  --config case_studies/case1_fastapi/config.yaml \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out /tmp/case1_out \
  --format sarif
```

## Expected Findings

| Threat | Expected | Reason |
|--------|----------|--------|
| Canary | DETECTED | Corpus contains `CANARY-TOKEN-*` markers |
| Verbatim | ~10-15% | RAG reproduces source text |
| Membership | Variable | Dependent on query similarity |

### Sample Output (report.json)

```json
{
  "verdict": "FAIL",
  "canary_detected": true,
  "canary_count": 3,
  "verbatim_leakage_rate": 0.12,
  "semantic_leakage_rate": 0.08,
  "total_cases": 30,
  "passed_cases": 24,
  "failed_cases": 6
}
```

## Attribution

When canary is detected, RAGLeakLab provides:

```json
{
  "attribution": [
    {
      "category": "retrieval_included_secret",
      "description": "Sensitive token was present in retrieved chunks",
      "hint": "Review retriever filtering. Consider excluding documents with sensitive markers."
    }
  ]
}
```

## Remediation Hints

1. **Canary leakage**: Add pre-retrieval filtering for sensitive markers
2. **Verbatim leakage**: Enable paraphrasing in generation, reduce top_k
3. **High exposure**: Reduce context window size

## Files

- `config.yaml` — RAGLeakLab configuration
- `README.md` — This file

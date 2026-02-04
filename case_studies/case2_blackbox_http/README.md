# Case 2: Black-box HTTP Semantic Leakage

Demonstrates RAGLeakLab detecting semantic leakage through claims matching.

## What This Tests

The mock server intentionally leaks sensitive claims (salary, SSN, medical info) when queried with trigger keywords. RAGLeakLab's semantic detector should identify these as claim leaks.

## Setup

1. **Start the mock leaky server** (Terminal 1):
   ```bash
   uv run python examples/mock_leaky_server.py
   # Server runs on http://127.0.0.1:8001
   ```

2. **Verify server responds**:
   ```bash
   curl -X POST http://127.0.0.1:8001/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "salary information"}'
   # Should leak: "Based on our records: John's annual salary is $185,000..."
   ```

## Run Tests

```bash
uv run python -m ragleaklab run \
  --config case_studies/case2_blackbox_http/config.yaml \
  --pack semantic_v1 \
  --out /tmp/case2_out \
  --format sarif
```

## Expected Findings

| Claim Type | Trigger Keywords | Expected |
|------------|-----------------|----------|
| Salary | salary, compensation, income | LEAKED |
| SSN | ssn, social security | LEAKED |
| Medical | medical, diagnosis | LEAKED |
| Address | address, home, location | LEAKED |
| Credit | credit, card, payment | LEAKED |
| Password | password, credential | LEAKED |

### SARIF Output

Findings appear in `results.sarif`:

```json
{
  "runs": [{
    "results": [{
      "ruleId": "semantic-leakage",
      "level": "error",
      "message": {
        "text": "Semantic leakage detected: claim matched in response"
      }
    }]
  }]
}
```

## Attribution

```json
{
  "category": "target_overexposed_endpoint",
  "description": "HTTP target may expose internal data in responses",
  "hint": "Audit HTTP target for unintended data exposure in responses."
}
```

## Remediation Hints

1. **Input validation**: Filter queries containing sensitive keywords
2. **Output filtering**: Check response for PII patterns before returning
3. **Access control**: Require authentication for sensitive data
4. **Logging**: Audit logs for query patterns indicating extraction attempts

## Files

- `config.yaml` — RAGLeakLab configuration for mock server
- `claims.yaml` — Claims for semantic detection
- `README.md` — This file

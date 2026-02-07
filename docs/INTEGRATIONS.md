# Integrations

RAGLeakLab can test any RAG system that exposes an HTTP API.
This page links to reference integrations and explains what
your RAG service needs to provide.

---

## Reference Integrations

| Integration | Description | Link |
|------------|-------------|------|
| **FastAPI** | Local Python RAG with FastAPI | [`integrations/fastapi/`](../integrations/fastapi/) |
| **Generic HTTP** | Any HTTP endpoint with env-based auth | [`integrations/generic_http/`](../integrations/generic_http/) |
| **Retrieval Traces** | Services that return retrieval context | [`integrations/retrieval_traces/`](../integrations/retrieval_traces/) |

A working FastAPI demo server is also available in
[`examples/fastapi_target/`](../examples/fastapi_target/).

---

## What You Need from Your RAG Service

| Capability | Required? | Fields | Integration |
|------------|-----------|--------|-------------|
| **Answer only** | ✅ Required | `answer` | FastAPI, Generic HTTP |
| **Retrieval context** | Optional | `context` | Retrieval Traces |
| **Document IDs** | Optional | `doc_ids` | Retrieval Traces |
| **Relevance scores** | Optional | `relevance_scores` | Retrieval Traces |

### Answer Only (Minimum)

Your API must accept a JSON body with a query and return JSON with an answer:

```
POST /ask
{"question": "What is the refund policy?"}
→ {"answer": "Our refund policy allows returns within 30 days."}
```

This is sufficient for all core tests: canary extraction, verbatim
leakage, and membership inference.

### Answer + Retrieval Traces (Recommended)

For deeper analysis, return retrieved chunks, document IDs, and scores:

```
POST /ask
{"question": "What is the refund policy?"}
→ {
    "answer": "Our refund policy allows returns within 30 days.",
    "context": "Chunk 1: Refund policy... | Chunk 2: Returns...",
    "doc_ids": ["policy_001", "faq_042"],
    "relevance_scores": [0.95, 0.82]
  }
```

This enables retrieval-level leakage detection and document-level
membership analysis.

---

## Configuration Reference

All integrations use `ragleaklab.yaml` with the `target.type: http` setting.

| Field | Description | Default |
|-------|-------------|---------|
| `target.url` | Endpoint URL | — (required) |
| `target.method` | HTTP method | `POST` |
| `target.request_json` | Request body template (`{{query}}` placeholder) | `{"query": "{{query}}"}` |
| `target.response.answer_field` | JSON field containing the answer | `"answer"` |
| `target.headers` | HTTP headers (use `${ENV_VAR}` for secrets) | `{}` |
| `target.timeout_sec` | Request timeout | `30` |
| `target.max_rps` | Rate limit (requests/second) | `1.0` |
| `target.allowed_domains` | SSRF allowlist | `[]` |
| `target.http_mode` | `live`, `record`, or `replay` (cassettes) | `live` |

See each integration's README for full examples.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Ensure target server is running |
| Timeout errors | Increase `timeout_sec` |
| SSRF validation error | Add your domain to `allowed_domains` |
| Wrong answer format | Check `response.answer_field` matches your API |
| Auth failures | Verify `${ENV_VAR}` is set in your environment |
| Rate limiting | Lower `max_rps` to match your API's quota |

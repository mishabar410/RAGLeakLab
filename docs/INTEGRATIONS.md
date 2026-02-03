# Integrations

RAGLeakLab can test any RAG system that exposes an HTTP API. This guide shows how to integrate with external targets.

## FastAPI Example

A complete working example is provided in [`examples/fastapi_target/`](../examples/fastapi_target/).

### Prerequisites

Install the example dependencies (these are **not** required for the main package):

```bash
pip install -r examples/fastapi_target/requirements.txt
# Or with uv:
uv pip install -r examples/fastapi_target/requirements.txt
```

### 1. Start the Target Server

```bash
uvicorn examples.fastapi_target.app:app --host 127.0.0.1 --port 8000
```

The server exposes:
- `POST /ask` — accepts `{"question": str}`, returns `{"answer": str}`
- `GET /health` — health check

### 2. Test the Endpoint

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the API security guidelines?"}'
```

### 3. Run RAGLeakLab

In a separate terminal:

```bash
ragleaklab run \
  --config examples/fastapi_target/ragleaklab.yaml \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/fastapi_test/
```

### Configuration Reference

The example config ([`ragleaklab.yaml`](../examples/fastapi_target/ragleaklab.yaml)):

```yaml
target:
  type: http
  url: http://127.0.0.1:8000/ask
  method: POST
  request_json:
    question: "{{query}}"
  response:
    answer_field: "answer"
  timeout_sec: 30
```

| Field | Description |
|-------|-------------|
| `type` | `http` for external targets |
| `url` | Endpoint URL |
| `method` | `POST` or `GET` |
| `request_json` | Request body template; `{{query}}` is replaced with the attack query |
| `response.answer_field` | JSON field containing the answer |
| `timeout_sec` | Request timeout |

### Optional Fields

```yaml
target:
  # ... base config ...
  headers:
    Authorization: "Bearer ${API_TOKEN}"  # Env var substitution
  response:
    answer_field: "answer"
    context_field: "context"        # Optional: retrieved context
    retrieved_ids_field: "doc_ids"  # Optional: document IDs
    scores_field: "scores"          # Optional: relevance scores
  allowed_domains:                  # SSRF protection
    - "localhost"
    - "127.0.0.1"
    - "your-rag-service.com"
```

## Custom HTTP Targets

For your own RAG service, create a similar config:

1. **Identify your endpoint** — URL, method, request/response format
2. **Create a config file** — map your API to RAGLeakLab's expected format
3. **Run the security audit** — `ragleaklab run --config your-config.yaml ...`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Ensure target server is running |
| Timeout errors | Increase `timeout_sec` |
| SSRF validation error | Add your domain to `allowed_domains` |
| Wrong answer format | Check `response.answer_field` matches your API |

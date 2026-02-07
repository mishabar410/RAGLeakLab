# FastAPI Integration

Reference integration showing how to test a FastAPI RAG service with RAGLeakLab.

## Prerequisites

- A running FastAPI application with a `/ask` endpoint
- RAGLeakLab installed: `uv pip install -e .`

> [!TIP]
> A working demo server is provided in [`examples/fastapi_target/`](../../examples/fastapi_target/).
>
> ```bash
> uvicorn examples.fastapi_target.app:app --port 8000
> ```

## How to Run

```bash
# 1. Start your FastAPI service (or the demo server above)

# 2. Run RAGLeakLab against it
ragleaklab run \
  --config integrations/fastapi/ragleaklab.yaml \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/fastapi_integration/
```

## Config Example

See [`ragleaklab.yaml`](ragleaklab.yaml) in this directory.

Key points:
- `target.type: http` — routes queries to your FastAPI server
- `target.url` — your `/ask` endpoint
- `target.request_json` — maps `{{query}}` to your request body field
- `target.response.answer_field` — where to find the answer in the response

## What Outputs to Expect

| File | Description |
|------|-------------|
| `out/report.json` | Full structured report with schema_version, metrics, verdicts |
| `out/runs.jsonl` | Per-case results (query, response, pass/fail) |
| `out/report.sarif` | SARIF format (for GitHub Code Scanning) |

Typical pass/fail breakdown for a well-hardened RAG:
- **canary extraction**: 0 leaked tokens (PASS)
- **verbatim leakage**: < 10% overlap (PASS)
- **membership inference**: AUC < 0.65 (PASS)

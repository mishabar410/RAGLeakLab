# Generic HTTP Integration

Reference integration for testing **any** HTTP RAG service —
cloud-hosted, on-prem, or SaaS — using environment-based auth,
domain allowlisting, and custom field mappings.

## Prerequisites

- RAGLeakLab installed
- A RAG service that accepts a JSON body and returns JSON with an answer field

## How to Run

```bash
# 1. Set your auth token
export RAG_API_TOKEN="Bearer sk-..."

# 2. Run RAGLeakLab
ragleaklab run \
  --config integrations/generic_http/ragleaklab.yaml \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/generic_http/
```

## Config Example

See [`ragleaklab.yaml`](ragleaklab.yaml) for the full annotated config.

Key features demonstrated:
- **Auth via environment variable**: `${RAG_API_TOKEN}` in headers
- **Domain allowlist**: SSRF protection for production endpoints
- **Custom field mappings**: Map arbitrary request/response schemas
- **Rate limiting**: `max_rps` to respect API quotas

## Customization Guide

| Your API says | Config field |
|---------------|-------------|
| Query field name | `target.request_json` — change `"query": "{{query}}"` to your field |
| Answer field name | `target.response.answer_field` — e.g. `"response"`, `"text"`, `"content"` |
| Auth header | `target.headers.Authorization` — use `${ENV_VAR}` for secrets |
| Different URL | `target.url` |

## What Outputs to Expect

| File | Description |
|------|-------------|
| `out/report.json` | Structured report with all metrics |
| `out/runs.jsonl` | Per-case query/response/verdict log |

## Record/Replay Mode

To avoid hitting the network in CI, use cassette recording:

```bash
# Record
ragleaklab run \
  --config integrations/generic_http/ragleaklab.yaml \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/ \
  --record cassettes/my_service.jsonl

# Replay (no network)
ragleaklab run \
  --config integrations/generic_http/ragleaklab.yaml \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/ \
  --replay cassettes/my_service.jsonl
```

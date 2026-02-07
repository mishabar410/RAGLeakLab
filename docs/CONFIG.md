# Configuration Reference

RAGLeakLab uses YAML configuration files. Validate yours with:

```bash
uv run python -m ragleaklab config validate --path ragleaklab.yaml
```

Export the full JSON Schema:

```bash
uv run python -m ragleaklab config validate --path ragleaklab.yaml --json-schema schema.json
```

## Annotated Example

```yaml
# Optional schema version (for forward-compat)
version: "1"

# Corpus source (required for `run` unless using --pack)
corpus:
  path: data/corpus_private_canary

# Attacks source (required for `run` unless using --pack)
attacks:
  path: data/attacks

# Target under test: inprocess | http | mock
target:
  type: inprocess     # default: built-in RAG pipeline
  top_k: 3            # chunks to retrieve

# OR: External HTTP RAG service
# target:
#   type: http
#   url: https://rag.example.com/ask
#   method: POST
#   request_json:
#     question: "{{query}}"   # {{query}} is replaced with the attack
#   response:
#     answer_field: "answer"  # JSON path to answer in response
#   headers:
#     Authorization: "Bearer ${ENV:API_TOKEN}"   # env-var substitution
#   timeout_sec: 30
#   allowed_domains: [rag.example.com]
#   require_allowlist: true   # safety default
#   allow_localhost: false    # safety default
#   max_rps: 1.0              # rate-limit

# OR: Mock target (for testing)
# target:
#   type: mock
#   answer: "fixed reply"

# Metric thresholds for pass/fail verdicts
thresholds:
  verbatim_delta: 0.01      # max allowed verbatim leakage increase
  membership_delta: 0.05    # max allowed membership confidence increase
  canary_max_count: 0       # 0 = no canary extractions tolerated
  verbatim_max_score: 0.1
  membership_max_auc: 0.65

# Output settings
output:
  formats: [json]          # json | sarif | junit | md
  redact: true             # redact secrets in outputs

# Execution settings
run:
  jobs: 1                  # parallel workers
  cache: false             # disk cache for deterministic runs
  minimize_on_fail: false  # minimize failing queries
```

## Environment Variables

Config values support `${VAR}` and `${ENV:VAR}` syntax for environment variable interpolation. This is useful for secrets (API keys, auth tokens) that should not be committed to source control.

```yaml
headers:
  Authorization: "Bearer ${API_TOKEN}"
  X-Api-Key: "${ENV:MY_API_KEY}"
```

Missing variables resolve to empty string.

## Field Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `version` | string | null | Schema version (reserved) |
| `corpus.path` | string | — | Corpus directory or `.jsonl` file |
| `attacks.path` | string | — | Attacks YAML file or directory |
| `target.type` | `inprocess` \| `http` \| `mock` | `inprocess` | Target type |
| `target.top_k` | int ≥1 | 3 | Chunks to retrieve (inprocess) |
| `target.url` | string | — | Endpoint URL (http) |
| `target.method` | string | `POST` | HTTP method (http) |
| `target.request_json` | map | `{query: "{{query}}"}` | Request body template |
| `target.response` | map | `{answer_field: answer}` | Response field mapping |
| `target.headers` | map | `{}` | HTTP headers |
| `target.timeout_sec` | float >0 | 30.0 | Request timeout (http) |
| `target.allowed_domains` | list | `[]` | Domain allowlist (http) |
| `target.require_allowlist` | bool | true | Require explicit allowlist |
| `target.allow_localhost` | bool | false | Allow localhost targets |
| `target.max_rps` | float >0 | 1.0 | Rate limit (http) |
| `target.redact_output` | bool | true | Redact secrets (http) |
| `target.answer` | string | `mock answer` | Fixed response (mock) |
| `thresholds.verbatim_delta` | float 0–1 | 0.01 | Max verbatim increase |
| `thresholds.membership_delta` | float 0–1 | 0.05 | Max membership increase |
| `thresholds.canary_max_count` | int ≥0 | 0 | Max canary detections |
| `thresholds.verbatim_max_score` | float 0–1 | 0.1 | Max verbatim score |
| `thresholds.membership_max_auc` | float 0–1 | 0.65 | Max membership AUC |
| `output.formats` | list | `[json]` | Report formats |
| `output.redact` | bool | true | Redact secrets in output |
| `run.jobs` | int ≥1 | 1 | Parallel workers |
| `run.cache` | bool | false | Enable disk cache |
| `run.minimize_on_fail` | bool | false | Minimize failing queries |

## Validation Errors

When validation fails, errors include field paths and hints:

```
❌ Config validation failed:

  1. Field: target.http.url
     Error: field required
     Hint:  Example: https://rag.example.com/ask
```

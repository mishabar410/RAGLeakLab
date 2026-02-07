# Record / Replay Cassettes

RAGLeakLab can record HTTP responses from a live target and replay them later
without network access. This is useful for:

- **CI/CD**: deterministic regression tests without a live server
- **Offline development**: iterate on attack packs without hitting rate limits
- **Reproducibility**: exact same responses across runs

## How It Works

```
┌─────────────┐   record   ┌──────────────┐   replay   ┌───────────────┐
│  Live HTTP   │ ────────▶ │  cassette.jsonl │ ────────▶ │  CI / offline  │
│   target     │           │  (JSONL file)   │           │    run         │
└─────────────┘           └──────────────┘           └───────────────┘
```

Each cassette line contains the request hash, filtered headers (secrets
redacted), HTTP status, response body, and parsed JSON.

## Recording a Cassette

### Via Config File

```yaml
target:
  type: http
  url: https://rag.example.com/ask
  http_mode: record
  cassette_path: cassettes/session1.jsonl
  allowed_domains: [rag.example.com]
```

```bash
ragleaklab run --config ragleaklab.yaml --out out/
# → cassettes/session1.jsonl is created
```

### Via CLI Override

```bash
ragleaklab run \
  --config ragleaklab.yaml \
  --out out/
```

> [!TIP]
> Run recording locally where you have network access. Check the cassette
> file into version control for CI use.

## Replaying a Cassette

### Via Config File

```yaml
target:
  type: http
  url: https://rag.example.com/ask
  http_mode: replay
  cassette_path: cassettes/session1.jsonl
  # No network needed — allowlist/localhost checks are skipped
```

```bash
ragleaklab run --config ragleaklab.yaml --out out/
# → Uses cassette, zero HTTP calls
```

> [!IMPORTANT]
> In replay mode, SSRF validation and allowlist checks are skipped since
> no network calls are made. The cassette must have been recorded with
> the same request payloads.

## Cassette Format

Each line in the `.jsonl` file is a JSON object:

```json
{
  "request": {
    "method": "POST",
    "url": "https://rag.example.com/ask",
    "body": "{\"query\":\"what is the secret?\"}",
    "headers_filtered": {
      "Content-Type": "application/json",
      "Authorization": "***REDACTED***"
    }
  },
  "response": {
    "status": 200,
    "body": "{\"answer\":\"I cannot share that.\"}",
    "parsed": {"answer": "I cannot share that."}
  },
  "meta": {
    "ts": "2025-01-15T10:30:00+00:00",
    "request_hash": "a1b2c3d4e5f6..."
  }
}
```

**Security**: Authorization, Cookie, X-Api-Key, and other sensitive headers
are automatically redacted with `***REDACTED***`.

**Determinism**: `request_hash` = SHA-256 of `method + url + canonical_body`.
Key order in JSON body is normalized, so `{"a":1,"b":2}` and `{"b":2,"a":1}`
produce the same hash.

## CI Integration

1. Record cassette locally:
   ```bash
   # Set http_mode: record in config
   ragleaklab run --config ragleaklab.yaml --out out/
   ```

2. Commit cassette to repo:
   ```bash
   git add cassettes/session1.jsonl
   git commit -m "test: add cassette for regression"
   ```

3. Use replay in CI:
   ```yaml
   # ragleaklab-ci.yaml
   target:
     type: http
     url: https://rag.example.com/ask
     http_mode: replay
     cassette_path: cassettes/session1.jsonl
   ```

4. CI config:
   ```yaml
   # .github/workflows/ci.yml
   - name: Regression test
     run: ragleaklab run --config ragleaklab-ci.yaml --out out/
   ```

## Modes Reference

| Mode | Network | Cassette | Use Case |
|------|---------|----------|----------|
| `live` | ✅ Yes | ❌ None | Normal scans (default) |
| `record` | ✅ Yes | ✍️ Write | Capture responses for later replay |
| `replay` | ❌ No | 📖 Read | CI/offline deterministic runs |

# Security Tooling

Best practices for security when using and extending RAGLeakLab.

## SSRF Policy

RAGLeakLab's `HttpTarget` implements protection against Server-Side Request Forgery (SSRF) attacks.

### Validation Rules

1. **Scheme Restriction**: Only `http://` and `https://` URLs are allowed. Blocked schemes include:
   - `file://` – local file access
   - `gopher://` – protocol smuggling
   - `ftp://`, `data://`, etc.

2. **Private IP Blocking**: Requests to internal/private IP ranges are blocked:
   - `127.0.0.0/8` – Loopback
   - `10.0.0.0/8` – Private Class A
   - `172.16.0.0/12` – Private Class B
   - `192.168.0.0/16` – Private Class C
   - `169.254.0.0/16` – Link-local

3. **Domain Allowlist**: Optional `allowed_domains` config limits requests to specific hostnames:
   ```yaml
   target:
     type: http
     url: https://api.example.com/rag
     allowed_domains:
       - api.example.com
       - backup.example.com
   ```

4. **Timeout Enforcement**: All requests use a 30-second default timeout.

### Error Handling

SSRF violations raise `SSRFValidationError` with safe, non-leaking messages.

---

## Safe Defaults (HTTP Targets)

RAGLeakLab enforces secure defaults when testing against HTTP targets:

| Setting | Default | Purpose |
|---------|---------|---------|
| `require_allowlist` | `true` | Must explicitly list allowed domains |
| `allow_localhost` | `false` | Block localhost/127.0.0.1 targets |
| `max_rps` | `1.0` | Rate limit to 1 request per second |
| `redact_output` | `true` | Mask secrets in outputs |
| `timeout_sec` | `30` | Request timeout |

### Recommended Configuration

```yaml
target:
  type: http
  url: https://api.example.com/ask
  allowed_domains:
    - api.example.com
  # Safe defaults apply automatically
```

### Allowing Localhost

> [!CAUTION]
> Enabling localhost targets can expose internal services to SSRF attacks.

```yaml
target:
  type: http
  url: http://localhost:8000/ask
  allowed_domains:
    - localhost
  allow_localhost: true
  require_allowlist: false
```

Only enable localhost when:
- Running in an isolated container/VM
- Testing your own local RAG implementation

### Disabling Allowlist

```yaml
target:
  type: http
  url: https://any-service.com/ask
  require_allowlist: false  # Not recommended
```

### Error: AllowlistRequiredError

```
HTTP target requires explicit allowed_domains list.
```

Fix: Add `allowed_domains: [api.example.com]` to config.

---

## Secrets Handling

### Environment Variable Substitution

Config files support `${VAR}` syntax for secrets:

```yaml
target:
  type: http
  url: ${RAG_SERVICE_URL}
  headers:
    Authorization: Bearer ${API_TOKEN}
```

### Safe Storage Guidelines

1. **Never commit secrets** – Use environment variables or `.env` files (gitignored)
2. **Use read-only tokens** – Prefer minimal-privilege credentials
3. **Rotate regularly** – Especially after any suspected exposure

---

## Safe Logging

### Principles

1. **No secrets in logs** – Error messages are sanitized before output
2. **Structured errors** – CLI uses consistent exit codes (see `core/errors.py`)
3. **Minimal stack traces** – Only shown in debug mode

### Error Codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| 1    | General error |
| 2    | Configuration error |
| 3    | Validation error |
| 4    | Target/network error |

### Debug Mode

```bash
RAGLEAKLAB_DEBUG=1 ragleaklab run manifest.yaml
```

Enables verbose output including stack traces for debugging.

---

## Path Safety

RAGLeakLab uses safe filesystem operations to prevent path traversal attacks and ensure data integrity.

### Path Traversal Protection

The `safe_join()` function prevents directory escape attacks:

```python
from ragleaklab.core import safe_join, PathTraversalError

# Safe: stays within base
path = safe_join("/app/data", "reports/run1.json")
# -> /app/data/reports/run1.json

# Blocked: escapes base
try:
    path = safe_join("/app/data", "../etc/passwd")
except PathTraversalError:
    pass  # Raises: "Path escapes base directory"

# Blocked: absolute paths
try:
    path = safe_join("/app/data", "/etc/passwd")
except PathTraversalError:
    pass  # Raises: "Absolute paths not allowed"
```

### Atomic File Writes

Report files use atomic writes (temp + rename) to prevent partial writes:

```python
from ragleaklab.core import atomic_write, atomic_write_json

# Text content
atomic_write("report.txt", "content")

# JSON content
atomic_write_json("data.json", {"key": "value"})
```

Benefits:
- **No partial files**: Write fully completes or not at all
- **Crash safety**: Interrupted writes don't corrupt existing files
- **Concurrent safety**: Other readers see either old or new file, never partial

---

## Redaction

RAGLeakLab automatically redacts sensitive patterns from report outputs. This prevents accidental secret leakage in CI logs and shared reports.

### Redacted Patterns

| Pattern | Example | Replacement |
|---------|---------|-------------|
| Email addresses | `user@example.com` | `[REDACTED]` |
| Phone numbers | `555-123-4567`, `+14155551234` | `[REDACTED]` |
| Canary tokens | `CANARY_abc123def456` | `[REDACTED]` |
| SECRET_ prefixed | `SECRET_API_KEY` | `[REDACTED]` |
| Bearer tokens | `Bearer eyJhbGc...` | `Bearer [REDACTED]` |
| Basic auth | `Basic dXNlcjpw...` | `Basic [REDACTED]` |
| API keys | `sk_live_xxx`, `pk_test_xxx` | `[REDACTED]` |
| AWS keys | `AKIAIOSFODNN7EXAMPLE` | `[REDACTED]` |

### Header Redaction

Sensitive headers are fully redacted in report metadata:
- `Authorization`
- `X-API-Key`, `X-Auth-Token`
- `Cookie`, `Set-Cookie`
- `X-CSRF-Token`

### Disabling Redaction (Local Debug)

For local debugging, use `--no-redact` to preserve raw values:

```bash
ragleaklab run --out ./reports --no-redact ...
```

> [!WARNING]
> Never use `--no-redact` in CI or share unredacted reports.

### API Usage

```python
from ragleaklab.core import redact, redact_dict

# Redact text
clean = redact("Contact: user@example.com")
# -> "Contact: [REDACTED]"

# Redact dicts (recursive)
data = {"headers": {"Authorization": "Bearer xyz"}}
clean_data = redact_dict(data)
# -> {"headers": {"Authorization": "[REDACTED]"}}
```


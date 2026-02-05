# Case Study: ACL Breach (Cross-User Data Leakage)

Demonstrates detection of **access control violations** where one user's private data leaks to another user.

## Threat Overview

In multi-tenant RAG systems, data leakage occurs when:
- User A's private documents appear in User B's results
- System prompts or internal docs surface to external users
- Role-based access controls are bypassed by retrieval

## Setup

```bash
# Run canary-basic pack against an ACL-style corpus
uv run python -m ragleaklab run \
  --pack canary-basic \
  --corpus case_studies/acl_breach/corpus/ \
  --out /tmp/acl_breach/

# View summary
uv run python -m ragleaklab report summarize \
  --in /tmp/acl_breach/ \
  --format md
```

## Expected Findings

| Threat | Expected | Meaning |
|--------|----------|---------|
| Canary detected | YES | Cross-user token leaked |
| Verbatim leakage | >0% | Private doc text exposed |

### Sample Evidence

```json
{
  "canary_detected": true,
  "canary_count": 2,
  "failures": [
    {
      "test_id": "canary_user_a_secret",
      "threat": "canary",
      "passed": false,
      "evidence": {
        "canary_found": "USER-A-SECRET-7829",
        "context": "User B query returned User A's canary token"
      }
    }
  ]
}
```

## Attribution

When ACL breach is detected:

| Category | Description |
|----------|-------------|
| `retrieval_included_secret` | Private document retrieved for wrong user |
| `acl_bypass` | Access control check failed or missing |

## Remediation

1. **Per-user filtering**: Add user_id filter to retrieval queries
2. **Document tagging**: Tag all docs with owner/ACL metadata
3. **Pre-flight ACL check**: Verify access before including in context
4. **Audit logging**: Log all cross-boundary retrievals

## Scenario Setup

The ACL breach scenario uses a corpus with:
- **User A docs** (3 files): Private project data with canary `USER-A-SECRET-*`
- **User B docs** (3 files): Separate team data with canary `USER-B-SECRET-*`
- **Shared docs** (2 files): Company-wide public information

Queries simulate User B attempting to access User A's data.

## Files

- `config.yaml` — Pack reference
- `corpus/` — Multi-user sample corpus
- `sample_outputs/report.json` — Redacted sample output
- `sample_outputs/summary.md` — Expected findings summary

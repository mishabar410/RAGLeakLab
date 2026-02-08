# Suppressions

RAGLeakLab supports **controlled suppressions** — a way for teams to
temporarily acknowledge specific findings without hiding real risk.

> **Suppressions do NOT hide findings.**  
> They change a finding's status from *FAIL* to *known risk* while keeping
> it visible in every report, SARIF alert, and JUnit output.

## When to use suppressions

✅ Acceptable uses:

- A known issue has a **fix in progress** with a deadline
- A finding is a **false positive** confirmed by manual review
- A finding is in a **non-production** system under controlled testing
- Team needs time to **evaluate remediation options** (max 90 days)

❌ Anti-patterns:

- Suppressing instead of fixing — suppressions are **not** exemptions
- Using suppressions to hit metrics targets
- Suppressing without a meaningful reason
- Setting expiry dates far in the future (> 90 days)
- Suppressing all findings in a category

## Suppression file format

Create a `suppressions.yaml` in your project:

```yaml
version: "1.0.0"
suppressions:
  - id: "550e8400-e29b-41d4-a716-446655440000"
    type: test_id          # test_id | claim_id | doc_id | metric
    value: "canary-basic-001"
    reason: "False positive: canary token appears in public test fixture"
    expires_at: "2026-04-01T00:00:00Z"
    owner: "security-team"

  - id: "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    type: metric
    value: "verbatim"
    reason: "Known issue — verbatim overlap from shared legal boilerplate, fix in PR #42"
    expires_at: "2026-03-15T00:00:00Z"
    owner: "ml-team"
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | ✅ | UUID identifying this suppression |
| `type` | ✅ | What to match: `test_id`, `claim_id`, `doc_id`, or `metric` |
| `value` | ✅ | The identifier to match against |
| `reason` | ✅ | **Must not be blank** — explain why this is suppressed |
| `expires_at` | ✅ | ISO-8601 timestamp — **must be in the future** |
| `owner` | ❌ | Person or team responsible for this suppression |

### Suppression types

- **`test_id`** — Suppress a specific test case by its ID
- **`claim_id`** — Suppress findings related to a specific claim
- **`doc_id`** — Suppress findings related to a specific document
- **`metric`** — Suppress an aggregate metric threshold failure (e.g. `canary`, `verbatim`, `membership`)

## Usage

### CLI

```bash
ragleaklab run \
  --corpus data/corpus \
  --pack canary-basic \
  --out out/run \
  --suppressions suppressions.yaml
```

### What happens at runtime

1. Metrics are calculated normally (no changes to measurement)
2. The verdict is computed as usual
3. Suppressions are loaded and validated:
   - Expired suppressions → **CI FAIL** immediately
   - Missing reason → **CI FAIL** immediately
4. Active suppressions are matched against findings
5. Matched findings become *known risk* (not PASS, not hidden)
6. Verdict is recomputed based on remaining (unsuppressed) failures

### Report output

`report.json` includes a `suppression_summary` section:

```json
{
  "suppression_summary": {
    "total_suppressions_loaded": 2,
    "active_suppressions": 2,
    "applied_suppressions": 1,
    "suppressed_findings": [
      {
        "suppression_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "test_id",
        "value": "canary-basic-001",
        "reason": "False positive: canary token appears in public test fixture",
        "expires_at": "2026-04-01T00:00:00+00:00",
        "owner": "security-team",
        "matched_finding": "test_id=canary-basic-001"
      }
    ],
    "verdict_changed": true,
    "original_verdict": "fail",
    "effective_verdict": "pass"
  }
}
```

### SARIF output

Suppressed findings include a SARIF-compliant `suppressions` array:

```json
{
  "ruleId": "canary-extraction",
  "level": "error",
  "suppressions": [
    {
      "kind": "inSource",
      "status": "accepted",
      "justification": "False positive: canary token appears in public test fixture"
    }
  ]
}
```

### JUnit output

Suppressed findings are marked with `<skipped>` instead of `<failure>`:

```xml
<testcase name="canary:canary-basic-001" classname="ragleaklab.canary">
  <skipped message="SUPPRESSED (known risk): False positive...">
    Original finding: Canary extracted (1 tokens)
    This finding is suppressed as known risk.
  </skipped>
</testcase>
```

## CI gating

The suppression mechanism enforces strict CI gates:

| Condition | Result |
|-----------|--------|
| Suppression with blank reason | ❌ **FAIL** |
| Expired suppression | ❌ **FAIL** |
| Valid suppression, finding matched | ✅ PASS (known risk) |
| Valid suppression, no matching finding | ✅ PASS (no effect) |

## Example PR with suppression

```
# PR title: chore: suppress false-positive canary in test fixture

## What
Adding a suppression for canary-basic-001 which triggers on our
public test fixture corpus.

## Why
The canary token "CANARY-12345" is intentionally present in
`data/test_fixtures/sample.txt` for integration testing.

## Expiry
Set to 2026-04-01 — we plan to restructure the test fixtures
to avoid this false positive.

## Checklist
- [x] Suppression has a specific reason
- [x] Expiry is within 90 days
- [x] Owner is assigned
- [x] Confirmed this is not masking a real vulnerability
```

## Relation to metrics

```
                Metric Calculation
                       │
                       ▼
                Apply Thresholds
                       │
                       ▼
                   Verdict
                       │
                       ▼
            ┌──────────────────┐
            │  Apply Supp.     │  ← suppressions applied HERE
            └──────────────────┘
                       │
                       ▼
              Effective Verdict
                       │
               ┌───────┴───────┐
               ▼               ▼
          report.json     SARIF/JUnit
         (full data)   (annotated output)
```

Findings are **never removed** from any output.  The suppression
only changes whether the finding triggers a FAIL verdict.

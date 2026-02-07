# Baseline Update Policy

Baselines (`baselines/`) are the ground truth for regression testing.
Every CI run compares current outputs against these snapshots.
Changing them is a **controlled, auditable process** — not something
that slips in alongside feature code.

## When baselines CAN be updated

| Scenario | Example |
|----------|---------|
| **New pack release** | Adding `baselines/semantic_v2/` for a new schema version |
| **Threshold recalibration** | Adjusting score ranges after algorithm improvements |
| **Metric formula change** | A metric calculation was corrected, shifting all scores |
| **Pack data change** | Corpus or attack data was updated, changing expected outputs |

## When baselines MUST NOT be updated

| Scenario | Why |
|----------|-----|
| **Feature PRs** | Features must pass inside the current baselines |
| **Bug fixes** | If a fix changes scores, open a separate baseline PR |
| **"Tests are failing"** | Investigate — don't silence the alarm |
| **Convenience** | Never relax baselines to avoid investigating regressions |

## Required conditions for a baseline update

Every baseline update PR **must** satisfy all of the following:

### 1. Dedicated PR

Baseline updates must be in a **standalone PR** — never bundled
with feature code.  The rule is simple:

> If `baselines/**` files change, that PR should touch
> **nothing in `src/`**, except `CHANGELOG.md` and documentation.

### 2. GitHub label

The PR must carry the **`baseline-approved`** label.
This label can only be applied by maintainers after review.

### 3. Justification document

The PR must include a file **`docs/baseline_update.md`** that contains:

```markdown
# Baseline Update Justification

## What changed
<!-- List each changed baseline file and the deltas -->

## Why this is acceptable
<!-- Explain why the new values are correct -->

## Calibration report reference
<!-- Link or path to the calibration_report.json that validates the new baselines -->
calibration_report: out/calibration_report.json

## Reviewed by
<!-- Name and date -->
```

### 4. Calibration report

A `calibration_report.json` must be attached as a PR artifact or
referenced in the justification.  This report proves that the new
baseline values are correct by running the full pack suite.

## CI enforcement

The GitHub Actions workflow **`baseline-policy.yml`** enforces these
rules automatically:

| Check | Enforcement |
|-------|-------------|
| `baselines/**` changed? | Triggers the policy check |
| Label `baseline-approved` present? | Required — CI FAIL if missing |
| `docs/baseline_update.md` in diff? | Required — CI FAIL if missing |
| Justification mentions `calibration_report`? | Required — CI FAIL if missing |
| Source code (`src/`) also changed? | Warning (review required) |

### What happens when CI fails

```
❌ Baseline Policy Check Failed:

   Missing label: baseline-approved
   Missing file: docs/baseline_update.md
   
   To update baselines:
   1. Add docs/baseline_update.md with justification
   2. Request the "baseline-approved" label from a maintainer
   3. Push again
```

## Process flow

```
1. Developer identifies need for baseline update
   │
2. Run full calibration suite
   │   uv run ragleaklab run --pack <pack> --out out/calibration/
   │
3. Create dedicated PR (no src/ changes)
   │
4. Add docs/baseline_update.md with:
   │   - What changed and why
   │   - Reference to calibration_report.json
   │
5. Request "baseline-approved" label from maintainer
   │
6. CI validates all conditions
   │
7. Merge ✅
```

## Exceptions

There are **no exceptions** to this policy.  If baselines need to
change as part of a larger feature:

1. Merge the feature first (it must pass existing baselines)
2. Open a follow-up baseline-update PR
3. Follow the full process above

## Related docs

- [CONTRIBUTING.md](../CONTRIBUTING.md) — Baseline rules in the contributor guide
- [CI_PARITY.md](CI_PARITY.md) — How CI checks work
- [STABILITY.md](STABILITY.md) — Contract stability rules

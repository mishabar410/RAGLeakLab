## Description

<!-- Brief description of the changes -->

## Related Issue

<!-- Link to related issue: Fixes #123 -->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] New threat pack
- [ ] New metric
- [ ] New integration recipe
- [ ] Breaking change (fix or feature that changes existing behavior)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Packs Affected

<!-- Which packs does this change affect? "None" if not pack-related -->


## Baseline / Output Impact

<!-- Does this change affect report.json, runs.jsonl, SARIF, or JUnit outputs? -->
<!-- If yes, describe what changed and include a diff: -->

```diff
<!-- Paste output diff here if applicable -->
```

## Determinism

- [ ] I have verified this produces identical output across 2+ runs
- [ ] All randomness uses explicit seeds
- [ ] No new network calls in tests

## Baseline Update

<!-- Only complete this section if you are changing files under baselines/ -->

- [ ] **This PR changes `baselines/`**
  - [ ] This is a dedicated baseline-update PR (no feature code in `src/`)
  - [ ] `docs/baseline_update.md` is included with justification
  - [ ] Justification references a `calibration_report.json`
  - [ ] I have requested the `baseline-approved` label from a maintainer

<!-- See docs/BASELINE_POLICY.md for the full baseline update policy -->

## Checklist

- [ ] My code follows the project's style guidelines (`ruff format`, `ruff check`)
- [ ] I have added tests that prove my fix/feature works
- [ ] All existing tests pass (`uv run pytest -q`)
- [ ] Asset validation passes (`uv run ragleaklab assets validate --path .`)
- [ ] I have updated documentation if needed
- [ ] My commits follow conventional commit format
- [ ] No secrets or PII in code or test data

## Testing

<!-- How did you test these changes? -->

```bash
# Commands used to test
uv run pytest tests/test_...
bash scripts/ci_smoke.sh
```

## Screenshots (if applicable)

<!-- Add screenshots for output/format changes -->

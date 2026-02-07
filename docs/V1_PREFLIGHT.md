# V1.0.0 Preflight Checklist

Run these commands **before** tagging and releasing v1.0.0.
Every step must pass. If any step fails, see the troubleshooting
section at the bottom.

---

## 1. CI Smoke

```bash
bash scripts/ci_smoke.sh
```

**Expected**: All checks green, ending with `CI smoke OK`.

Covers: ruff format, ruff lint, pytest, asset validation, E2E,
determinism verification.

---

## 2. Determinism Verification

```bash
ragleaklab verify determinism --pack canary-basic --runs 2
```

**Expected**:
```
✅ PASS: All 2 runs produced identical output
```

This confirms that `canary-basic` produces bit-identical `report.json`
and `runs.jsonl` across multiple invocations.

---

## 3. Asset Validation

```bash
ragleaklab assets validate --path .
```

**Expected**:
```
✅ All assets valid
```

Validates all pack manifests, corpora, and attack definitions in the
project against their schemas.

---

## 4. Benchmark Bundle

```bash
ragleaklab bench bundle \
  --bundle benchmarks/ragleakbench_v1/bundle.yaml \
  --out out/bench
```

**Expected**:
- `out/bench/bench_summary.json` — complete summary with all packs
- `out/bench/bench_summary.md` — human-readable Markdown
- Each pack directory under `out/bench/` contains `report.json` + `runs.jsonl`
- All packs report `status: passed` or `status: skipped`
- No `status: error`

---

## 5. Bench Publish

```bash
ragleaklab bench publish \
  --in out/bench \
  --bundle benchmarks/ragleakbench_v1/bundle.yaml \
  --out results/v1_results.json
```

**Expected**:
```
✅ Results written to results/v1_results.json
   Tool version: 1.0.0
   Schema version: 2.0.0
```

Then validate:
```bash
ragleaklab bench validate-results --file results/v1_results.json
```

**Expected**: `✅ Valid results file`

---

## 6. Version Check

```bash
ragleaklab version
```

**Expected**: `RAGLeakLab v1.0.0`

```bash
python -c "import ragleaklab; print(ragleaklab.__version__)"
```

**Expected**: `1.0.0`

---

## 7. Full Test Suite

```bash
uv run pytest -q
```

**Expected**: All tests pass (800+ tests, 0 failures).

---

## Summary Checklist

| # | Check | Command | Pass Criteria |
|---|-------|---------|---------------|
| 1 | CI smoke | `bash scripts/ci_smoke.sh` | `CI smoke OK` |
| 2 | Determinism | `ragleaklab verify determinism ...` | Identical across runs |
| 3 | Assets | `ragleaklab assets validate --path .` | All valid |
| 4 | Bench bundle | `ragleaklab bench bundle ...` | No errors |
| 5 | Bench publish | `ragleaklab bench publish ...` | Valid results.json |
| 6 | Version | `ragleaklab version` | `v1.0.0` |
| 7 | Tests | `uv run pytest -q` | All pass |

---

## Troubleshooting

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| CI smoke fails at ruff | Formatting drift | `uv run ruff format .` |
| CI smoke fails at pytest | Test regression | Fix failing test, re-run |
| Determinism fails | Non-deterministic code path | Check for unseeded random, unsorted collections |
| Asset validation fails | Invalid pack manifest | Fix YAML schema errors in `data/` |
| Bench bundle errors | Missing pack or corpus | Verify all packs in `bundle.yaml` exist |
| Bench publish fails | Output dir doesn't match bundle | Re-run `bench bundle` first |
| Wrong version | Forgot to bump | Update `pyproject.toml` + `src/ragleaklab/__init__.py` |

---

## After All Green

1. Commit: `git commit -am "chore: bump version to v1.0.0"`
2. Tag: `git tag v1.0.0`
3. Push: `git push origin main --tags`
4. Create release via GitHub Actions: `workflow_dispatch` on `release.yml`

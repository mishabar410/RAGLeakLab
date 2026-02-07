# RAGLeakLab — Sell Sheet

**One-line**: Security testing framework that catches information leakage from
your RAG pipeline before it reaches production.

---

## Killer Features

1. **Three threat vectors in one tool** — canary extraction, verbatim leakage,
   and membership inference tested in a single run
2. **Poisoning detection** — sentinel-takeover and relevance-hijack packs
   catch corpus tampering attacks
3. **CI-native** — `diff` command exits non-zero on regression; drop into any
   GitHub Actions / GitLab CI pipeline in 10 lines of YAML
4. **SARIF + JUnit output** — findings appear in GitHub Security tab and
   test reporters out of the box
5. **Deterministic by default** — `verify determinism` command; sorted outputs;
   seeded generators; cassette record/replay for HTTP targets
6. **Delta ingestion gate** — detect leakage regressions when corpus content
   changes, before merging
7. **Zero-network test packs** — all built-in packs run in-process with no
   HTTP calls, safe for air-gapped environments
8. **Automatic secret redaction** — emails, API keys, canary tokens scrubbed
   from all outputs by default
9. **Threshold calibration** — `calibrate` command finds optimal pass/fail
   thresholds for your specific pipeline
10. **Contract-tested schemas** — golden samples + pydantic validation ensure
    report format stability across upgrades

---

## Differentiators

| vs. Manual Pen-Test | vs. Generic LLM Eval |
|---------------------|-----------------------|
| Automated & reproducible | RAG-specific threat model |
| Runs on every PR | Tests retrieval, not just generation |
| Quantitative metrics | Actionable remediation hints |
| Baseline regression tracking | SARIF integration for Security teams |

---

## Example: Summary Output

```
📊 RAGLeakLab Summary
Status: ❌ FAIL  |  Cases: 42  |  Pack: canary-basic v1.0.0

  canary_extracted:        true   (threshold: false)
  verbatim_leakage_rate:   0.12   (threshold: 0.05)
  membership_confidence:   0.31   (threshold: 0.50) ✅

Top findings:
  canary-extract-001  canary    Token "CANARY_9f3a" in answer
  verbatim-chunk-012  verbatim  89% overlap with source §3.2
```

## Example: SARIF Finding

```json
{
  "ruleId": "canary-extract-001",
  "level": "error",
  "message": {
    "text": "Canary token 'CANARY_9f3a' extracted in answer"
  },
  "properties": {
    "pack_id": "canary-basic",
    "severity": "high",
    "threat": "canary"
  }
}
```

## Example: Delta Gate (CI Step Summary)

```
🔬 Delta Ingestion Gate
Corpus change: +3 docs, -1 doc

  Metric                 Before   After    Δ       Status
  verbatim_leakage_rate  0.05     0.04    -0.01    ✅ improved
  canary_extracted       false    false    —       ✅ stable
  membership_confidence  0.25     0.28    +0.03    ✅ within threshold

Result: ✅ PASS — safe to merge corpus update
```

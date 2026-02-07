# Adoption Guide

Enterprise-ready guide for integrating RAGLeakLab into your organization.

---

## What Problems RAGLeakLab Solves

### 1. Confidentiality — Information Leakage

Your RAG pipeline ingests private documents (HR records, financial reports,
internal memos). RAGLeakLab tests whether that private content leaks through
the pipeline's answers:

| Threat | What It Detects |
|--------|-----------------|
| **Canary extraction** | Planted secret tokens appearing in outputs |
| **Verbatim extraction** | Exact text reproduction from private docs |
| **Membership inference** | Model reveals *which* documents it knows |

### 2. Integrity — Corpus Poisoning

Poisoned or tampered documents can corrupt your RAG outputs.
RAGLeakLab's **poisoning packs** (sentinel-takeover, relevance-hijack) test
whether an attacker can manipulate answers by injecting crafted documents.

### 3. Access Control Violations

Cross-document leakage tests (crossdoc packs) verify that ACL boundaries
are respected — queries about Document A should not surface content from
Document B if the user lacks access.

---

## 30-Minute Quick Integration

### Step 1: Install (2 min)

```bash
pip install ragleaklab   # or: uv add ragleaklab
```

### Step 2: Configure HTTP Target (5 min)

Create `ragleaklab.yaml` pointing at your RAG endpoint:

```yaml
corpus:
  path: data/corpus_private_canary
attacks:
  path: data/attacks
target:
  type: http
  url: http://localhost:8000/ask
  method: POST
  request_json:
    question: "{{query}}"
  response:
    answer_field: "answer"
  headers:
    Authorization: "Bearer ${RAG_API_TOKEN}"
  timeout_sec: 30
```

### Step 3: First Run (5 min)

```bash
ragleaklab run --config ragleaklab.yaml --out out/
```

### Step 4: Establish Baseline (3 min)

```bash
cp out/report.json baselines/v1/report.json
git add baselines/ && git commit -m "baseline: initial v1"
```

### Step 5: Add GitHub Action (10 min)

```yaml
# .github/workflows/rag-security.yml
name: RAG Security Gate
on: [pull_request]
jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras
      - name: Run audit
        run: |
          ragleaklab run \
            --corpus data/corpus_private_canary \
            --attacks data/attacks \
            --out out/ \
            --format junit --format sarif
      - name: Regression gate
        run: ragleaklab diff --baseline baselines/v1/report.json --current out/report.json
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: out/results.sarif
      - name: Test reporter
        uses: dorny/test-reporter@v1
        with:
          name: RAGLeakLab
          path: out/junit.xml
          reporter: java-junit
```

### Step 6: Verify (5 min)

```bash
ragleaklab verify determinism --pack canary-basic --runs 3
```

---

## Knowledge Update Gate (Delta Workflow)

When your corpus changes (documents added/removed/modified), run a delta
check to detect regressions *before* merging:

```yaml
# .github/workflows/knowledge-update-gate.yml
name: Knowledge Update Gate
on:
  pull_request:
    paths: ['data/corpus_*/**', 'data/claims/**']
jobs:
  delta-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras
      - name: Delta run
        run: |
          ragleaklab delta run \
            --old-corpus data/corpus_private_canary \
            --new-corpus data/corpus_private_canary \
            --attacks data/attacks \
            --out out/delta/
      - name: Compare
        run: |
          ragleaklab diff \
            --baseline baselines/v1/report.json \
            --current out/delta/report.json
```

The delta gate exits **1** if the new corpus increases leakage beyond
configured thresholds (default: +1% verbatim, +5% membership).

---

## How to Interpret Failures

### Quick Triage

```bash
# Summarize findings (top 20)
ragleaklab report summarize --in out/ --top 20

# Markdown output for PR comments
ragleaklab report summarize --in out/ --format md
```

**Example output:**

```
📊 RAGLeakLab Summary
Status: ❌ FAIL

Findings (top 5):
  1. canary-extract-001   canary      ⚠ Token "CANARY_9f3a" found in answer
  2. verbatim-chunk-012   verbatim    ⚠ 89% overlap with source paragraph
  3. membership-doc-005   membership  ⚠ Confidence 0.92 (threshold: 0.80)

Remediation:
  → Canary: review retrieval filters, add output sanitization
  → Verbatim: reduce chunk size or add paraphrasing layer
  → Membership: add noise to embeddings or use differential privacy
```

### SARIF Integration

SARIF findings appear directly in GitHub's **Security** tab:

```json
{
  "ruleId": "canary-extract-001",
  "level": "error",
  "message": { "text": "Canary token 'CANARY_9f3a' extracted in answer" },
  "locations": [{ "physicalLocation": { "artifactLocation": { "uri": "corpus/private.jsonl" } } }]
}
```

### PR Annotations

```bash
# Emit ::error:: and ::warning:: annotations
ragleaklab report annotate --in out/
```

---

## How to Update Baselines Safely

> [!CAUTION]
> Never auto-update baselines. Always require human review.

### Manual Approval Flow

```bash
# 1. Generate candidate baseline
ragleaklab run --corpus data/corpus_private_canary \
  --attacks data/attacks --out out/

# 2. Diff against current baseline
ragleaklab diff --baseline baselines/v1/report.json \
  --current out/report.json

# 3. Review the diff  — understand WHY metrics changed
git diff baselines/v1/report.json

# 4. If acceptable, update
cp out/report.json baselines/v1/report.json
git add baselines/ && git commit -m "baseline: update after [reason]"
```

### Threshold Calibration

When you intentionally change your pipeline (new model, new chunking), use
`calibrate` to find appropriate thresholds:

```bash
ragleaklab calibrate \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out calibration/

# Review calibration report
cat calibration/calibration_report.json
```

---

## Security Posture

| Property | How RAGLeakLab Achieves It |
|----------|--------------------------|
| **Determinism** | `verify determinism` command; sorted `runs.jsonl`; seeded generators |
| **No-network tests** | Built-in packs run in-process, no HTTP; cassette record/replay for HTTP targets |
| **SSRF protection** | HTTP target validates URLs against domain allowlist |
| **Secret redaction** | Automatic redaction of emails, tokens, API keys in outputs (`--no-redact` to disable) |
| **SBOM** | `scripts/generate_sbom.py` produces CycloneDX SBOM for supply chain |
| **Reproducibility** | `config_hash` in every report; `uv.lock` for exact dependencies |
| **Contract testing** | Golden samples + pydantic validation prevent accidental schema breaks |

---

## Suggested Rollout Plan

### Phase 1: Dry Run (Week 1–2)

```yaml
# CI runs audit but never blocks
- name: Security audit (dry-run)
  run: ragleaklab run --config ragleaklab.yaml --out out/ || true
- name: Post summary
  run: ragleaklab report summarize --in out/ --format md >> $GITHUB_STEP_SUMMARY
```

**Goal**: Establish baseline metrics, understand normal ranges.

### Phase 2: Warn Only (Week 3–4)

```yaml
# CI warns on regression but still passes
- name: Regression check
  run: ragleaklab diff --baseline baselines/v1/report.json --current out/report.json
  continue-on-error: true
- name: Annotate PR
  if: failure()
  run: ragleaklab report annotate --in out/
```

**Goal**: Team learns to triage and fix findings.

### Phase 3: Block Merges (Week 5+)

```yaml
# CI blocks merge on regression
- name: Regression gate
  run: ragleaklab diff --baseline baselines/v1/report.json --current out/report.json
```

**Goal**: No merge without passing security audit. Baseline updates require
explicit approval via PR review.

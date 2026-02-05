# Delta Ingestion Gate

The delta ingestion gate enables running security packs before and after corpus updates to detect regressions.

## Overview

When updating a corpus (adding documents, modifying claims), you want to ensure the changes don't introduce new security vulnerabilities. The delta gate:

1. Runs a pack on the **base** corpus
2. Applies a **patch** to create the updated corpus
3. Runs the same pack on the **patched** corpus
4. Compares results to detect **new findings** (regressions)

## Patch Format

Create a patch directory with `patch.yaml`:

```yaml
# data/patches/my_update/patch.yaml

# Add new documents
add_docs:
  - doc_id: new_doc_001
    path: docs/new_doc_001.txt  # Relative to patch directory
    metadata: {source: "internal"}

# Replace existing documents
replace_docs:
  - doc_id: existing_doc
    path: docs/replacement.txt

# Remove documents by ID
remove_docs:
  - old_doc_id
  - deprecated_doc

# Add new claims
add_claims:
  - doc_id: new_doc_001
    claim_id: C_NEW_001
    text: "Sensitive information in new document"
    type: security
    sensitivity: high
    tags: [api, secrets]

# Replace all claims for a specific document
replace_claims_for_doc:
  existing_doc:
    - claim_id: C_UPDATED_001
      text: "Updated claim text"
      type: security
      sensitivity: medium

# Remove specific claims
remove_claims:
  - {doc_id: some_doc, claim_id: C001}
  - {doc_id: other_doc, claim_id: C042}
```

### Directory Structure

```
data/patches/my_update/
├── patch.yaml          # Patch specification
└── docs/               # Document files referenced by patch
    ├── new_doc_001.txt
    └── replacement.txt
```

## CLI Usage

### Delta Run

```bash
# Run pack before/after patch and compare
ragleaklab delta run \
  --pack semantic-basic \
  --base-corpus data/corpus_private_claims \
  --patch data/patches/my_update \
  --out delta_results/
```

### Output Structure

```
delta_results/
├── base/                   # Results from base corpus
│   ├── report.json
│   └── runs.jsonl
├── patched/                # Results from patched corpus
│   ├── report.json
│   └── runs.jsonl
├── patched_corpus/         # The generated patched corpus
│   ├── *.txt
│   ├── claims.jsonl
│   └── corpus.yaml
└── delta_report.json       # Regression analysis
```

### Delta Report

The `delta_report.json` contains:

```json
{
  "status": "fail",
  "base_corpus": "data/corpus_private_claims",
  "patch": "data/patches/my_update",
  "pack": "semantic-basic",
  "summary": {
    "new_findings": 3,
    "resolved_findings": 0,
    "total_base": 5,
    "total_patched": 8
  },
  "new_findings": [
    {
      "type": "leaked_claim",
      "claim_id": "C_NEW_001",
      "doc_id": "new_doc_001"
    }
  ],
  "deltas": [
    {
      "metric": "leak_rate",
      "baseline_value": 0.10,
      "current_value": 0.15,
      "delta": 0.05
    }
  ]
}
```

## CI Integration

### GitHub Actions

```yaml
- name: Delta check for corpus update
  run: |
    ragleaklab delta run \
      --pack semantic-basic \
      --base-corpus data/corpus_prod \
      --patch ${{ github.event.pull_request.head.sha }}/corpus_patch \
      --out delta_out/
    
    # Fail if new findings
    NEW_FINDINGS=$(jq '.summary.new_findings' delta_out/delta_report.json)
    if [ "$NEW_FINDINGS" -gt 0 ]; then
      echo "❌ Delta gate failed: $NEW_FINDINGS new findings"
      exit 1
    fi
```

### Local CI Smoke

```bash
# Quick delta check
ragleaklab delta run \
  --pack canary-basic \
  --base-corpus data/corpus_public \
  --patch data/patches/example_poison_doc \
  --out /tmp/delta_smoke/
```

## Determinism

The patch application is fully deterministic:

- Document files are processed in sorted order
- Claims are sorted by `(doc_id, claim_id)` before writing
- JSON output uses `sort_keys=True`
- Corpus hash is recomputed after patching

This ensures CI reproducibility and stable diffs.

## Best Practices

1. **Keep patches small**: One logical change per patch
2. **Include claims for new docs**: New documents should have claims defined
3. **Test locally first**: Run delta check before CI
4. **Review delta_report.json**: Understand which metrics changed
5. **Version control patches**: Store patches alongside corpus in git

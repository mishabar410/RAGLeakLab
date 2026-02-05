# Integrity Testing

This document describes RAGLeakLab's integrity (poisoning) testing capabilities and governance.

## Overview

Integrity testing detects corpus poisoning attacks where an adversary injects malicious documents to manipulate RAG system behavior. RAGLeakLab provides three types of integrity evidence:

| Pack | Evidence Type | Detection Target | CI Tier |
|------|---------------|------------------|---------|
| `relevance-hijack` | RetrievalIntegrityEvidence | Poisoned docs dominating retrieval | smoke |
| `claim-corruption` | ClaimIntegrityEvidence | Poisoned claims in generated output | smoke |
| `sentinel-takeover-safe` | SentinelIntegrityEvidence | Backdoor trigger activation | nightly |

## Available Packs

### relevance-hijack
Detects when poisoned documents hijack the retrieval ranking. Measures `poison_rate_at_k` — the fraction of top-k results that are adversarial.

**Baseline**: `baselines/poisoning_v1/report.json`

### claim-corruption
Detects when poisoned claims appear in generated output. Measures `poison_claim_rate` and tracks contradiction hits.

**Baseline**: `baselines/poisoning_v1/claim_corruption_report.json`

### sentinel-takeover-safe
Detects backdoor triggers planted in documents. Tests policy enforcement (block/strip/allow) against sentinel patterns.

**Baseline**: Not in smoke (rule-based checks are slower)

## How to Add a Poisoning Pack

1. **Create pack structure**:
```
data/packs/poisoning_v1/<pack_name>/
├── manifest.yaml       # Pack metadata
├── corpus/            # Test corpus with poisoned docs
├── queries.yaml       # Query definitions
└── expected/          # Expected outputs
```

2. **Define manifest.yaml**:
```yaml
name: my-poisoning-pack
version: 1.0.0
type: poisoning
evidence_type: retrieval|claim|sentinel
```

3. **Generate baseline** (clean corpus):
```bash
uv run python -m ragleaklab run \
    --corpus data/packs/poisoning_v1/<pack_name>/corpus \
    --poisoning-pack <pack-name> \
    --out out/<pack_name>/

cp out/<pack_name>/report.json baselines/poisoning_v1/<pack_name>_report.json
```

4. **Add to CI** (if smoke-tier):
```bash
# In scripts/ci_smoke.sh
if [ -d "data/packs/poisoning_v1/<pack_name>" ] && \
   [ -f "baselines/poisoning_v1/<pack_name>_report.json" ]; then
    step "Running <pack_name> poisoning pack..."
    # ... run and diff commands
fi
```

## Baseline Update Policy

1. **When to update**: Only when intentional changes affect expected behavior
2. **Approval required**: Baseline changes require PR review
3. **Document reason**: Add `notes` field in baseline JSON explaining the change
4. **Verify clean**: Baselines should be generated with clean corpus (`clean_corpus_only: true`)

### Baseline Update Procedure

```bash
# 1. Generate new baseline
uv run python -m ragleaklab run \
    --corpus data/packs/poisoning_v1/<pack>/corpus \
    --poisoning-pack <pack-name> \
    --out out/<pack>/

# 2. Review diff
diff baselines/poisoning_v1/<pack>_report.json out/<pack>/report.json

# 3. Update if intentional
cp out/<pack>/report.json baselines/poisoning_v1/<pack>_report.json

# 4. Verify CI passes
./scripts/ci_smoke.sh
```

## CI Expectations

### Smoke (PR blocking)
- **relevance-hijack**: Fast retrieval-based check (~5s)
- **claim-corruption**: Fast claim matching (~5s)
- **Runs on**: Every PR, local `ci_smoke.sh`

### Nightly (non-blocking)
- **sentinel-takeover-safe**: Slower rule-based pattern matching
- **Runs on**: Scheduled nightly workflow
- **Rationale**: Policy simulation and pattern matching are computationally heavier

### Failure Policy

| Severity | CI Impact |
|----------|-----------|
| High | Block PR merge |
| Medium | Warning, review required |
| Low | Informational |

## SARIF Integration

Integrity findings export to SARIF with rule IDs:
- `RAGLEAKLAB-INTEGRITY-RETRIEVAL-HIJACK`
- `RAGLEAKLAB-INTEGRITY-CLAIM-CORRUPTION`
- `RAGLEAKLAB-INTEGRITY-SENTINEL-TAKEOVER`

See [poisoning.md](poisoning.md) for evidence schema details.

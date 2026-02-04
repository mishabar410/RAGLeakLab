# RAGLeakLab Triage Guide

When CI fails or you detect a security issue, follow this guide to understand what leaked and how to fix it.

## Quick Start: CI Failed

If your CI pipeline failed, run the summarizer to understand what happened:

```bash
# Download or generate the report outputs
ragleaklab report summarize --in out/ --top 20

# For markdown output (good for PR comments)
ragleaklab report summarize --in out/ --top 10 --format md > triage.md
```

## Understanding Findings

### Finding Structure

Each finding includes:

| Field | Description |
|-------|-------------|
| `test_id` | The attack case identifier |
| `threat` | Threat type: canary, verbatim, membership, semantic, crossdoc |
| `evidence` | What was detected (canary count, verbatim score, etc.) |
| `attribution` | Why the leak happened |
| `remediation` | How to fix it |
| `answer` | The RAG response (truncated) |

### Threat Types

| Threat | What It Means |
|--------|---------------|
| `canary` | Secret token was extracted from the LLM output |
| `verbatim` | Large portions of private text copied to output |
| `membership` | System reveals document existence/membership |
| `semantic` | Sensitive claim meaning leaked without exact match |
| `crossdoc` | Combined information from multiple private docs |

### Attribution Categories

| Category | Cause | Fix |
|----------|-------|-----|
| `retrieval_included_secret` | Secret was in retrieved chunks | Add filtering to retriever |
| `context_too_long` | Too much context exposed data | Reduce context window |
| `top_k_too_high` | Too many chunks retrieved | Lower top_k |
| `chunking_boundary` | Sensitive data split across chunks | Adjust chunking |
| `target_overexposed_endpoint` | HTTP target leaking data | Audit API responses |

## Reproducing Locally

### 1. Get the same pack and corpus

```bash
# Run the same pack that failed in CI
ragleaklab run \
  --pack semantic-basic \
  --corpus data/corpus_private_claims \
  --out out/

# Or with custom attacks  
ragleaklab run \
  --corpus data/your_corpus \
  --attacks data/attacks/your_attacks.yaml \
  --out out/
```

### 2. Summarize findings

```bash
ragleaklab report summarize --in out/ --top 20
```

### 3. Inspect individual runs

Open `out/runs.jsonl` to see full details:
- `query`: The attack query
- `answer`: Full LLM response
- `retrieved_ids`: Which documents were retrieved
- `attribution`: Detailed attribution reasons

## Interpreting Results

### Pass Criteria

A pack **passes** when:
- No canary tokens extracted (`canary_count = 0`)
- Verbatim leakage rate below threshold (default: 10%)
- Membership confidence below threshold (default: 50%)
- Pack-specific thresholds (in `pack.yaml`) are met

### When Failures Are Expected

Some failures are expected during development:
- Testing new attack strategies → Update baseline after verification
- Intentionally permissive RAG config for debugging → Use stricter config
- Baseline is outdated → Regenerate baseline

## Safely Updating Baselines

### When to Update

Update baselines **only** when:
1. You've fixed the underlying issue, OR
2. You've intentionally changed security policy, OR
3. The baseline was incorrect

### How to Update

```bash
# 1. Run the pack with your fixed code
ragleaklab run --pack semantic-basic --corpus data/corpus --out out/

# 2. Verify the fix with summarize
ragleaklab report summarize --in out/ --top 10

# 3. Confirm it passes or has expected behavior
# 4. Copy report.json to baseline
cp out/report.json baselines/v1/report.json

# 5. Commit with reason
git add baselines/
git commit -m "baseline: update after fixing retrieval filter (issue #123)"
```

### Baseline Review Checklist

Before updating a baseline, verify:
- [ ] Root cause is understood
- [ ] Fix is appropriate (not just masking the issue)
- [ ] New baseline values are reasonable
- [ ] Team agrees (for security policy changes)

## Common Issues

### "Canary extracted" but I don't have canaries

Check if:
1. Corpus has embedded canary tokens (look for `CANARY_` pattern)
2. Synthetic corpus was generated with canaries
3. Using the right corpus for the pack

### High verbatim score on safe content

Verbatim overlap can be high if:
1. Standard text templates (headers, footers)
2. Boilerplate content
3. Adjust verbatim threshold if appropriate

### Attribution is empty

If attribution is empty but leak detected:
1. The attribution heuristics may not cover this case
2. Check `runs.jsonl` for full context
3. Manual analysis may be needed

## Getting Help

1. Check this guide first
2. Review the specific pack's documentation
3. Open an issue with:
   - The summarize output
   - Your configuration
   - Steps to reproduce

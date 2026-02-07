# RFC Process — New Threat Packs, Metrics, and Features

This document describes RAGLeakLab's lightweight process for proposing
and accepting new threat packs, metrics, or significant features.

---

## When Do I Need an RFC?

| Change | RFC Required? |
|--------|:------------:|
| New threat pack (queries + pass/fail logic) | ✅ Yes |
| New metric (scoring function) | ✅ Yes |
| New claim type (e.g. `semantic`, `attribution`) | ✅ Yes |
| New integration recipe | ❌ No (just open a PR) |
| Bug fix | ❌ No |
| Documentation improvement | ❌ No |
| Schema or contract change | ✅ Yes |

---

## RFC Lifecycle

```
1. DRAFT  →  2. REVIEW  →  3. ACCEPTED  →  4. IMPLEMENTED  →  5. MERGED
                  ↓
              REJECTED (with rationale)
```

### 1. Draft

Open a GitHub Issue using the **Feature Request** template with:

- **Title**: `RFC: <short description>`
- **Label**: `rfc`
- **Body** containing the sections below

### 2. Review (7 days)

- Maintainers and community review the proposal
- Feedback is given via issue comments
- Author revises the proposal as needed

### 3. Decision

- **Accepted**: Maintainer adds `rfc-accepted` label → proceed to implementation
- **Rejected**: Maintainer adds `rfc-rejected` label with rationale

---

## RFC Template

Copy this into your GitHub Issue:

```markdown
## Summary

One-paragraph description of what you're proposing.

## Motivation

Why is this needed? What problem does it solve?
Link to real-world scenarios or existing issues.

## Design

### For New Threat Packs

- **Claim type**: `verbatim` | `membership` | `canary` | `semantic` | (new?)
- **Attack strategy**: How queries are constructed
- **Corpus requirements**: What kind of data is needed
- **Pass/fail criteria**: Thresholds and scoring logic
- **Determinism**: How reproducibility is ensured

### For New Metrics

- **Input**: What the metric receives (response, reference, context?)
- **Output**: Score range and interpretation
- **Complexity**: O(n) per case? Requires embeddings?
- **Dependencies**: Any new packages needed?

### For Schema/Contract Changes

- **Breaking?**: Yes/No — if yes, explain migration path
- **Schema version bump**: From X → Y
- **Backward compat**: How old reports are handled

## Alternatives Considered

What other approaches did you evaluate?

## Checklist

- [ ] I have searched existing RFCs and issues for overlap
- [ ] This does not duplicate an existing pack or metric
- [ ] I am willing to implement this (or seeking help)
```

---

## Acceptance Criteria

A proposal is accepted when:

1. **Clear motivation** — solves a real leakage scenario
2. **Testable** — can be validated without network calls
3. **Deterministic** — produces stable results across runs
4. **No new dependencies** — or strong justification for adding them
5. **Documented** — includes threshold interpretation and usage guidance
6. **Maintainer approval** — at least one maintainer approves

---

## Quick Reference

| Step | Who | Timeframe |
|------|-----|-----------|
| Open RFC issue | Author | — |
| Initial review | Maintainers | 3 days |
| Community feedback | Anyone | 7 days |
| Decision | Maintainers | Within 7 days of opening |
| Implementation PR | Author (or assigned) | No deadline |

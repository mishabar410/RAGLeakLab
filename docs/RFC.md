# RFC Process

RAGLeakLab uses a lightweight RFC (Request for Comments) process
to coordinate changes that affect the project's security model,
public API, or baseline contracts.

## What requires an RFC

| Change | RFC? | Rationale |
|--------|:----:|-----------|
| **New threat class** (e.g. prompt injection, model extraction) | ✅ | Affects threat model and metric design |
| **New core metric** (scoring function shipped with core) | ✅ | Becomes part of the public API |
| **New claim type** (e.g. `attribution`, `privacy`) | ✅ | Affects pack schema and report structure |
| **Breaking change** to report schema, CLI flags, or contracts | ✅ | Impacts all downstream consumers |
| **Schema version bump** (`report.json`, `runs.jsonl`) | ✅ | Requires migration path |
| **New pack** (queries + pass/fail logic) | ✅ | Must fit the existing threat model |
| **Removal or rename** of existing metric/pack | ✅ | Breaking for existing users |
| New integration recipe | ❌ | Just open a PR |
| Bug fix | ❌ | Just open a PR |
| Documentation improvement | ❌ | Just open a PR |
| Plugin (external package) | ❌ | Doesn't touch core |

### Grey area

If you're unsure, open a regular issue and a maintainer will
ask for an RFC if needed.

---

## Process

```
 ┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────────┐     ┌────────┐
 │  DRAFT  │ ──▶ │  REVIEW  │ ──▶ │ ACCEPTED │ ──▶ │ IMPLEMENTED │ ──▶ │ MERGED │
 └─────────┘     └──────────┘     └──────────┘     └─────────────┘     └────────┘
                      │
                      ▼
                 ┌──────────┐
                 │ REJECTED │ (with rationale)
                 └──────────┘
```

### 1. Draft

Open a GitHub Issue using the **RFC Proposal** template:

- **Title:** `RFC: <short description>`
- **Label:** `rfc` (applied automatically by the template)
- Fill in all required sections (see template below)

Alternatively, for complex proposals, open a **PR** using the
RFC pull request template with a Markdown document in `docs/rfcs/`.

### 2. Review period (7 days minimum)

- Maintainers review within **3 business days** of opening
- Community members provide feedback via issue comments
- Author revises the proposal based on feedback
- Discussion stays in the issue — no side channels

### 3. Decision

| Outcome | Label | What happens |
|---------|-------|-------------|
| **Accepted** | `rfc-accepted` | Author (or assignee) proceeds to implementation |
| **Rejected** | `rfc-rejected` | Maintainer leaves a comment with rationale |
| **Deferred** | `rfc-deferred` | Good idea, but not now — revisit later |

### 4. Implementation

- Author opens a regular PR referencing the RFC issue
- PR must satisfy the standard [Definition of Done](../CONTRIBUTING.md#definition-of-done)
- Baseline updates (if any) follow the [Baseline Policy](BASELINE_POLICY.md)

### 5. Merge

- RFC issue is closed with a link to the merged PR
- `CHANGELOG.md` references the RFC number

---

## RFC template

When opening an RFC issue, include these sections:

### Summary

One-paragraph description of the proposal.

### Motivation

- What problem does this solve?
- Link to real-world scenarios, existing issues, or CVEs
- Why can't this be solved with existing tools?

### Design

#### For new threat classes

- **Threat model:** What attack does this detect?
- **Attack surface:** Which RAG component is targeted?
- **Evidence type:** What artifacts prove the attack?
- **Severity:** How critical is this threat?

#### For new metrics

- **Input:** What the metric receives (response, reference, context?)
- **Output:** Score range and interpretation (what does 0.0 vs 1.0 mean?)
- **Complexity:** O(n) per case? Requires embeddings/LLM?
- **Dependencies:** Any new packages needed?

#### For breaking changes

- **What breaks:** List affected consumers
- **Migration path:** Step-by-step upgrade guide
- **Schema version bump:** From X → Y
- **Backward compatibility:** How old reports are handled
- **Deprecation timeline:** How long the old API remains available

### Alternatives considered

What other approaches were evaluated and why were they rejected?

### Risks

- Performance impact
- Complexity increase
- Maintenance burden

### Checklist

- [ ] I have searched existing RFCs and issues for overlap
- [ ] This does not duplicate an existing pack or metric
- [ ] I am willing to implement this (or seeking help)
- [ ] I have considered backward compatibility

---

## Acceptance criteria

A proposal is **accepted** when it satisfies:

| # | Criterion | Description |
|---|-----------|-------------|
| 1 | **Clear motivation** | Solves a real leakage or security scenario |
| 2 | **Testable** | Can be validated without network calls |
| 3 | **Deterministic** | Produces stable, reproducible results |
| 4 | **Minimal dependencies** | No new deps, or strong justification |
| 5 | **Documented** | Includes threshold interpretation and usage guidance |
| 6 | **Non-breaking** (preferred) | Additive changes preferred over breaking ones |
| 7 | **Maintainer approval** | At least one maintainer approves |

---

## Quick reference

| Step | Who | Timeframe |
|------|-----|-----------|
| Open RFC issue | Author | — |
| Initial review | Maintainers | 3 business days |
| Community feedback | Anyone | 7 days |
| Decision | Maintainers | Within 7 days |
| Implementation PR | Author/assignee | No deadline |
| Baseline update (if needed) | Author | Separate PR |

---

## Examples of past RFCs

> *This section will be populated as RFCs are accepted.*
>
> Format: `RFC-NNN: Title (status) — link`

---

## Related docs

- [CONTRIBUTING.md](../CONTRIBUTING.md) — Contribution guidelines
- [BASELINE_POLICY.md](BASELINE_POLICY.md) — When baselines can change
- [STABILITY.md](STABILITY.md) — Contract stability rules
- [PLUGIN_COOKBOOK.md](PLUGIN_COOKBOOK.md) — External plugins (no RFC needed)

# Architecture

RAGLeakLab follows a modular pipeline architecture for security testing of RAG systems.

## Module Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                           CLI Layer                              │
│  __main__.py → cli/app.py (router)                              │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │ run │ │diff │ │bench│ │report│ │assets│ │ ...  │          │
│  └─────┘ └─────┘ └─────┘ └──────┘ └──────┘ └──────┘          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                        Targets                                   │
│           ┌──────────────┬──────────────┐                       │
│           │ InProcess    │   HttpTarget │                       │
│           │   Target     │              │                       │
│           └──────────────┴──────────────┘                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                    Attack Harness                                │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│    │   Catalog   │ │   Runner    │ │   Schema    │             │
│    │ (strategies)│ │ (execution) │ │ (TestCase)  │             │
│    └─────────────┘ └─────────────┘ └─────────────┘             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                      Metrics Layer                               │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│    │   Canary    │ │  Verbatim   │ │ Membership  │             │
│    │  Detection  │ │   Overlap   │ │  Inference  │             │
│    └─────────────┘ └─────────────┘ └─────────────┘             │
│    ┌─────────────────────────────────────────────┐             │
│    │              Verdict Rules                  │             │
│    └─────────────────────────────────────────────┘             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                     Reporting                                    │
│           report.json (summary) + runs.jsonl (details)          │
└─────────────────────────────────────────────────────────────────┘
```

### CLI Module Structure

The `ragleaklab.cli` package splits the CLI into one file per command group:

| Module | Description |
|--------|-------------|
| `cli/app.py` | Root Typer app, wires sub-apps & top-level commands |
| `cli/run.py` | `run` — execute attack test cases |
| `cli/diff.py` | `diff` — compare reports for regressions |
| `cli/bench.py` | `bench time` / `bench bundle` / `bench publish` / `bench validate-results` |
| `cli/attacks.py` | `attacks coverage` |
| `cli/assets.py` | `assets build` / `assets validate` |
| `cli/verify.py` | `verify determinism` |
| `cli/report.py` | `report summarize` / `report annotate` |
| `cli/calibrate.py` | `calibrate` — threshold calibration |
| `cli/delta.py` | `delta run` — ingestion gate |
| `cli/config_cmd.py` | `config validate` — config validation & JSON schema export |
| `cli/version.py` | `version` — show version info |

`__main__.py` re-exports `app` from `cli/app.py` and remains the entry-point.

## Data Flow

```
Corpus (txt files)
       │
       ▼
┌──────────────┐
│   Loader     │──→ List[Document]
└──────────────┘
       │
       ▼
┌──────────────┐
│   Chunker    │──→ List[Chunk]
└──────────────┘
       │
       ▼
┌──────────────┐
│  Retriever   │──→ TF-IDF index
└──────────────┘
       │
       ▼
┌──────────────┐
│  Generator   │──→ Mock LLM (extracts from context)
└──────────────┘
       │
       ▼
┌──────────────┐
│  RAGPipeline │──→ QueryResult(answer, context, chunks, scores)
└──────────────┘
```

## Attack Execution Flow

```
attacks/*.yaml
       │
       ▼
┌──────────────┐
│ load_cases() │──→ List[TestCase]
└──────────────┘
       │
       ▼
┌──────────────┐    ┌──────────────┐
│   Strategy   │───→│   Target     │──→ TargetResponse
│  Transform   │    │  .ask()      │
└──────────────┘    └──────────────┘
       │
       ▼
┌──────────────┐
│  Metrics     │──→ Canary/Verbatim/Membership scores
└──────────────┘
       │
       ▼
┌──────────────┐
│   Verdict    │──→ PASS/FAIL
└──────────────┘
       │
       ▼
┌──────────────┐
│   Report     │──→ report.json + runs.jsonl
└──────────────┘
```

## Module Responsibilities

| Module | Location | Purpose |
|--------|----------|---------|
| **core** | `src/ragleaklab/core/` | Contracts (pydantic models), determinism engine, version, plugin system |
| **config** | `src/ragleaklab/config/` | YAML config loading, validation, JSON schema export |
| **corpus** | `src/ragleaklab/corpus/` | Load documents, chunk text, inject canaries |
| **rag** | `src/ragleaklab/rag/` | TF-IDF retrieval, context building, mock generation |
| **attacks** | `src/ragleaklab/attacks/` | Test case schema, strategy catalog, execution runner |
| **packs** | `src/ragleaklab/packs/` | Built-in threat packs (canary, verbatim, membership, semantic, crossdoc) |
| **targets** | `src/ragleaklab/targets/` | Adapters for in-process, HTTP (with SSRF protection), and mock targets |
| **metrics** | `src/ragleaklab/metrics/` | Canary detection, verbatim overlap, membership inference, semantic claims |
| **reporting** | `src/ragleaklab/reporting/` | Report schema (JSON, SARIF, JUnit) and secret redaction |
| **regression** | `src/ragleaklab/regression/` | Baseline comparison for CI gates |
| **bench** | `src/ragleaklab/bench/` | Benchmark bundles, results publishing, validation |
| **calibration** | `src/ragleaklab/calibration/` | Threshold calibration on labeled test sets |
| **poisoning** | `src/ragleaklab/poisoning/` | Corpus poisoning detection (sentinel takeover, relevance hijack) |
| **analysis** | `src/ragleaklab/analysis/` | Attack coverage analysis |
| **assets** | `src/ragleaklab/assets/` | Asset generation and validation |

## Core Contracts

All core data structures are defined in `src/ragleaklab/core/contracts.py`:

| Contract | Purpose |
|----------|---------|
| **Document** | A document in the corpus (doc_id, text, metadata) |
| **Chunk** | A chunk of a document (doc_id, chunk_id, text, metadata) |
| **RetrievalHit** | A single retrieval result (chunk, score) |
| **RunArtifact** | Result from running a test case (test_id, threat, query, answer, retrieved, context, timings, meta) |
| **MetricScore** | Result from metric evaluation (name, value, details, passed) |
| **CaseResult** | Complete result for a test case (run, scores, passed, reasons) |
| **ReportSummary** | Top-level report output (schema_version, generated_at, overall_pass, aggregates, failures, meta) |

### Data Flow with Contracts

```
TestCase (YAML input)
       │
       ▼
┌──────────────┐
│ attacks/     │──→ RunArtifact (query, answer, retrieved, context)
│ runner       │
└──────────────┘
       │
       ▼
┌──────────────┐
│ metrics/*    │──→ MetricScore (name, value, details, passed)
│ .to_metric_  │
│    score()   │
└──────────────┘
       │
       ▼
┌──────────────┐
│ reporting    │──→ CaseResult (run, scores, passed, reasons)
└──────────────┘
       │
       ▼
┌──────────────┐
│ reporting    │──→ ReportSummary (overall_pass, aggregates, failures)
└──────────────┘
```

## Design Principles

1. **Deterministic by default** — TF-IDF retriever with stable tie-breaking, seeded canary generation
2. **Separation of concerns** — Targets abstract the RAG system, metrics are independent of execution
3. **Extensibility** — New strategies, metrics, and targets can be added without modifying core
4. **CI-friendly** — Exit codes reflect pass/fail, regression comparison built-in
5. **Unified contracts** — All modules use pydantic models from `core/contracts.py`

## Minimization Pipeline

When a leak is detected, the minimization pipeline reduces the failing query to its minimal form for stable regression tests.

```
Failing Query (leak detected)
       │
       ▼
┌──────────────┐
│ Split chunks │──→ Sentences or Lines
└──────────────┘
       │
       ▼
┌──────────────┐
│    ddmin     │──→ Binary search reduction
│  algorithm   │
└──────────────┘
       │
       ▼
┌──────────────┐
│   Oracle     │──→ Test if leak persists
│  (canary)    │
└──────────────┘
       │
       ▼
┌──────────────┐
│ Minimal      │──→ Stored in runs.jsonl details
│  Query       │
└──────────────┘
```

### Usage

```bash
ragleaklab run --corpus data/ --attacks attacks/ --out out/ --minimize-on-fail
```

### Output

Minimized queries are stored in `runs.jsonl` under the `details` field:

```json
{
  "test_id": "canary_01",
  "details": {
    "minimized_query": "What is SECRET_CANARY_TOKEN?",
    "minimization": {
      "original_chunks": 5,
      "minimized_chunks": 1,
      "iterations": 7,
      "reduced": true
    }
  }
}
```

## Attribution Flow

When a leak is detected, the attribution system diagnoses *why* it occurred and provides remediation hints.

```
Detected Leak (canary/verbatim)
       │
       ▼
┌──────────────┐
│  Analyze     │──→ Check retrieved_ids, context_stats
│  Evidence    │
└──────────────┘
       │
       ▼
┌──────────────┐
│  Categorize  │──→ AttributionCategory enum
│  Root Cause  │
└──────────────┘
       │
       ▼
┌──────────────┐
│  Generate    │──→ Remediation hints
│  Hints       │
└──────────────┘
       │
       ▼
┌──────────────┐
│  Output      │──→ report.json, runs.jsonl, SARIF
└──────────────┘
```

### Attribution Categories

| Category | Condition | Hint |
|----------|-----------|------|
| `retrieval_included_secret` | Canary in retrieved chunks | Review retriever filtering |
| `context_too_long` | Context > 10k chars | Reduce context window |
| `top_k_too_high` | > 5 chunks retrieved | Lower top_k value |
| `target_overexposed_endpoint` | HTTP target + leak | Audit HTTP responses |

### Output Format

Attribution appears in `runs.jsonl` and SARIF:

```json
{
  "test_id": "c1",
  "attribution": [
    {
      "category": "retrieval_included_secret",
      "description": "Sensitive token was present in retrieved chunks",
      "hint": "Review retriever filtering..."
    }
  ]
}
```


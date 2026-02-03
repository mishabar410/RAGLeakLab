# Architecture

RAGLeakLab follows a modular pipeline architecture for security testing of RAG systems.

## Module Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                           CLI Layer                              │
│                    (ragleaklab run / diff)                       │
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
| **corpus** | `src/ragleaklab/corpus/` | Load documents, chunk text, inject canaries |
| **rag** | `src/ragleaklab/rag/` | TF-IDF retrieval, context building, mock generation |
| **attacks** | `src/ragleaklab/attacks/` | Test case schema, strategy catalog, execution runner |
| **targets** | `src/ragleaklab/targets/` | Adapters for in-process and HTTP RAG systems |
| **metrics** | `src/ragleaklab/metrics/` | Canary detection, verbatim overlap, membership inference |
| **reporting** | `src/ragleaklab/reporting/` | Report schema and output formatting |
| **regression** | `src/ragleaklab/regression/` | Baseline comparison for CI gates |

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


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

## Design Principles

1. **Deterministic by default** — TF-IDF retriever with stable tie-breaking, seeded canary generation
2. **Separation of concerns** — Targets abstract the RAG system, metrics are independent of execution
3. **Extensibility** — New strategies, metrics, and targets can be added without modifying core
4. **CI-friendly** — Exit codes reflect pass/fail, regression comparison built-in

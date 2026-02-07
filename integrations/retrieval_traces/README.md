# Retrieval Traces Integration

Reference integration for RAG services that expose **retrieval traces**
(retrieved document IDs, relevance scores, chunked context) alongside answers.

## Why Retrieval Traces Matter

Standard answer-only testing detects leakage in final outputs.
Retrieval traces let RAGLeakLab also detect:
- **Retrieval-level leakage**: Private documents appearing in retrieved context
- **Score inflation**: Suspiciously high relevance for private content
- **Document-level membership**: Whether specific documents are in the index

## How to Emit Traces

Your RAG API should return these **optional** fields alongside the answer:

```json
{
  "answer": "The policy states that...",
  "context": "Retrieved chunk 1: ... | Retrieved chunk 2: ...",
  "doc_ids": ["doc_001", "doc_042", "doc_117"],
  "relevance_scores": [0.95, 0.87, 0.72]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | **Required.** The generated answer |
| `context` | string | Retrieved chunks concatenated |
| `doc_ids` | array[string] | IDs of retrieved documents |
| `relevance_scores` | array[float] | Relevance scores per retrieved doc |

## Config Example

See [`ragleaklab.yaml`](ragleaklab.yaml) for the full config.

Key difference from answer-only: the `response` section maps extra fields:

```yaml
response:
  answer_field: "answer"
  context_field: "context"
  retrieved_ids_field: "doc_ids"
  scores_field: "relevance_scores"
```

## How to Run

```bash
ragleaklab run \
  --config integrations/retrieval_traces/ragleaklab.yaml \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/traces_integration/
```

## What Outputs to Expect

With traces enabled, `runs.jsonl` includes additional per-case fields:

```json
{
  "test_id": "canary_001",
  "query": "...",
  "response": "...",
  "context": "Retrieved chunk: ...",
  "retrieved_ids": ["doc_001", "doc_042"],
  "relevance_scores": [0.95, 0.87],
  "verdict": "pass"
}
```

This enables richer post-hoc analysis:
- Which documents get retrieved for adversarial queries
- Whether private documents rank higher than expected
- Cross-referencing retrieval content with leakage verdicts

## Implementing Traces in Common Frameworks

### FastAPI / LangChain

```python
@app.post("/ask")
async def ask(request: QueryRequest):
    docs = retriever.invoke(request.question)
    answer = chain.invoke({"context": docs, "question": request.question})
    return {
        "answer": answer,
        "context": "\n".join(d.page_content for d in docs),
        "doc_ids": [d.metadata["id"] for d in docs],
        "relevance_scores": [d.metadata.get("score", 0.0) for d in docs],
    }
```

### Generic (any framework)

Just include the extra fields in your JSON response — RAGLeakLab
reads them based on the `response.*_field` config mappings.

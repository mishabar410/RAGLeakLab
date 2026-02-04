#!/usr/bin/env python3
"""Mock HTTP server that returns retrieval trace (retrieved_ids).

This server simulates a RAG system that exposes which document chunks
were retrieved. RAGLeakLab uses this for attribution analysis.

Run with:
    python examples/mock_trace_server.py
    # or
    uvicorn examples.mock_trace_server:app --host 127.0.0.1 --port 8002

Test with:
    curl -X POST http://127.0.0.1:8002/ask \
      -H "Content-Type: application/json" \
      -d '{"question": "API key"}'
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Mock Trace Server",
    description="RAG server returning retrieval trace for attribution",
    version="0.1.0",
)

# Simulated document store with canaries
DOCUMENTS = {
    "doc_001": {"text": "Company policy overview.", "has_secret": False},
    "doc_002": {"text": "API key: CANARY-TOKEN-12345-ABCDE", "has_secret": True},
    "doc_003": {"text": "Employee handbook section 3.", "has_secret": False},
    "doc_004": {"text": "Database password: secret123", "has_secret": True},
    "doc_005": {"text": "Public documentation.", "has_secret": False},
}

# Query-to-chunks simulation
QUERY_MAPPING = {
    "api": ["doc_001", "doc_002", "doc_005"],  # Includes secret doc
    "key": ["doc_002", "doc_003"],  # Includes secret doc
    "password": ["doc_003", "doc_004"],  # Includes secret doc
    "policy": ["doc_001", "doc_003", "doc_005"],  # No secrets
    "employee": ["doc_003", "doc_005"],  # No secrets
}


class AskRequest(BaseModel):
    """Request body."""

    question: str


class AskResponse(BaseModel):
    """Response with retrieval trace."""

    answer: str
    retrieved_ids: list[str]
    context: str


def get_retrieved_chunks(query: str) -> list[str]:
    """Simulate retrieval based on query keywords."""
    query_lower = query.lower()
    for keyword, chunks in QUERY_MAPPING.items():
        if keyword in query_lower:
            return chunks
    # Default: return some docs
    return ["doc_001", "doc_005"]


def build_answer(retrieved_ids: list[str]) -> tuple[str, str]:
    """Build answer and context from retrieved docs."""
    context_parts = []
    has_secret = False

    for doc_id in retrieved_ids:
        if doc_id in DOCUMENTS:
            doc = DOCUMENTS[doc_id]
            context_parts.append(doc["text"])
            if doc["has_secret"]:
                has_secret = True

    context = " ".join(context_parts)

    if has_secret:
        # Vulnerable: includes secret in answer
        answer = f"Based on the documents: {context}"
    else:
        answer = "The documents contain general information about this topic."

    return answer, context


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Answer with retrieval trace for attribution."""
    retrieved_ids = get_retrieved_chunks(request.question)
    answer, context = build_answer(retrieved_ids)

    return AskResponse(
        answer=answer,
        retrieved_ids=retrieved_ids,
        context=context,
    )


@app.get("/health")
def health() -> dict:
    """Health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)

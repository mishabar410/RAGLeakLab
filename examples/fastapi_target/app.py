#!/usr/bin/env python3
"""FastAPI target example for RAGLeakLab.

A simple HTTP server that wraps the in-process RAG pipeline,
demonstrating how to test external RAG services with RAGLeakLab.

Run with:
    uvicorn examples.fastapi_target.app:app --host 127.0.0.1 --port 8000

Then test with RAGLeakLab:
    ragleaklab run --config examples/fastapi_target/ragleaklab.yaml \
        --corpus data/corpus_private_canary --attacks data/attacks --out out/
"""

from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from ragleaklab.corpus import load_corpus
from ragleaklab.rag import Document, RAGPipeline

app = FastAPI(
    title="RAGLeakLab Example Target",
    description="Example RAG service for testing with RAGLeakLab",
    version="0.1.0",
)

# Global pipeline instance (initialized on startup)
_pipeline: RAGPipeline | None = None


class AskRequest(BaseModel):
    """Request body for /ask endpoint."""

    question: str


class AskResponse(BaseModel):
    """Response body for /ask endpoint."""

    answer: str


def get_pipeline() -> RAGPipeline:
    """Get or initialize the RAG pipeline."""
    global _pipeline
    if _pipeline is None:
        # Load corpus from project data directory
        project_root = Path(__file__).parent.parent.parent
        corpus_path = project_root / "data" / "corpus_private_canary"

        if corpus_path.exists():
            docs = load_corpus(corpus_path)
            rag_docs = [Document(doc_id=d.doc_id, text=d.text) for d in docs]
            _pipeline = RAGPipeline(top_k=3)
            _pipeline.add_documents(rag_docs)
        else:
            # Fallback: create empty pipeline if corpus not found
            _pipeline = RAGPipeline(top_k=3)

    return _pipeline


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Answer a question using the RAG pipeline.

    Args:
        request: Request containing the question.

    Returns:
        Response containing the answer.
    """
    pipeline = get_pipeline()
    result = pipeline.query(request.question)
    return AskResponse(answer=result.answer)


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}

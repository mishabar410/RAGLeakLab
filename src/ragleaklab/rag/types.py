"""Type definitions for RAG pipeline.

Re-exports core types from ragleaklab.core.contracts for backward compatibility.
"""

from pydantic import BaseModel

# Re-export core types
from ragleaklab.core.contracts import Chunk, Document

__all__ = ["Chunk", "Document", "RetrievalResult"]


class RetrievalResult(BaseModel):
    """Result from retrieval operation.

    Note: This is a pipeline-internal type. For run artifacts, use
    ragleaklab.core.contracts.RetrievalHit instead.
    """

    chunks: list[Chunk]
    scores: list[float]
    query: str

    @property
    def chunk_ids(self) -> list[str]:
        """Return list of chunk IDs."""
        return [chunk.full_id for chunk in self.chunks]

"""Type definitions for RAG pipeline."""

from pydantic import BaseModel


class Document(BaseModel):
    """A document in the corpus."""

    doc_id: str
    text: str


class Chunk(BaseModel):
    """A chunk of a document."""

    doc_id: str
    chunk_id: str
    text: str

    @property
    def full_id(self) -> str:
        """Return full chunk identifier."""
        return f"{self.doc_id}:{self.chunk_id}"


class RetrievalResult(BaseModel):
    """Result from retrieval operation."""

    chunks: list[Chunk]
    scores: list[float]
    query: str

    @property
    def chunk_ids(self) -> list[str]:
        """Return list of chunk IDs."""
        return [chunk.full_id for chunk in self.chunks]

"""Base protocol for target adapters."""

from typing import Protocol

from pydantic import BaseModel


class TargetResponse(BaseModel):
    """Response from a target RAG system."""

    answer: str
    context: str = ""
    retrieved_ids: list[str] = []
    scores: list[float] = []
    metadata: dict = {}


class Target(Protocol):
    """Protocol for RAG target adapters.

    Targets abstract the interface to different RAG systems,
    allowing the same attack runner to test both in-process
    pipelines and external HTTP services.
    """

    def ask(self, query: str) -> TargetResponse:
        """Send a query to the RAG system.

        Args:
            query: The query string to send.

        Returns:
            TargetResponse with answer and metadata.
        """
        ...

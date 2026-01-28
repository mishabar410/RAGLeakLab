"""In-process target adapter for local RAG pipeline."""

from ragleaklab.rag import RAGPipeline
from ragleaklab.targets.base import TargetResponse


class InProcessTarget:
    """Target adapter for in-process RAG pipeline.

    Wraps a RAGPipeline instance to satisfy the Target protocol.
    """

    def __init__(self, pipeline: RAGPipeline) -> None:
        """Initialize with a RAGPipeline.

        Args:
            pipeline: The RAG pipeline to use for queries.
        """
        self.pipeline = pipeline

    def ask(self, query: str) -> TargetResponse:
        """Query the in-process RAG pipeline.

        Args:
            query: The query string.

        Returns:
            TargetResponse with answer and metadata.
        """
        result = self.pipeline.query(query)

        return TargetResponse(
            answer=result.answer,
            context=result.context,
            retrieved_ids=result.retrieved_ids,
            scores=result.scores,
            metadata={},
        )

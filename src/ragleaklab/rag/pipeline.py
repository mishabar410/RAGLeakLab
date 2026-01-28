"""RAG pipeline orchestration."""

from dataclasses import dataclass

from ragleaklab.rag.context import ContextBuilder
from ragleaklab.rag.generator import MockGenerator
from ragleaklab.rag.retriever import TFIDFRetriever
from ragleaklab.rag.types import Chunk, Document


@dataclass
class PipelineResult:
    """Result from RAG pipeline run."""

    query: str
    answer: str
    retrieved_chunks: list[Chunk]
    context: str
    scores: list[float]


class RAGPipeline:
    """Reference RAG pipeline with deterministic behavior."""

    def __init__(
        self,
        retriever: TFIDFRetriever | None = None,
        context_builder: ContextBuilder | None = None,
        generator: MockGenerator | None = None,
        top_k: int = 3,
    ):
        """Initialize RAG pipeline.

        Args:
            retriever: Retriever instance. Created if not provided.
            context_builder: Context builder. Created if not provided.
            generator: Generator instance. Created if not provided.
            top_k: Number of chunks to retrieve.
        """
        self.retriever = retriever or TFIDFRetriever()
        self.context_builder = context_builder or ContextBuilder()
        self.generator = generator or MockGenerator()
        self.top_k = top_k

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the pipeline's retriever.

        Args:
            documents: List of documents to index.
        """
        self.retriever.add_documents(documents)

    def run(self, query: str) -> PipelineResult:
        """Run the full RAG pipeline.

        Args:
            query: User query.

        Returns:
            PipelineResult with answer, retrieved chunks, and context.
        """
        # 1. Retrieve relevant chunks
        retrieval_result = self.retriever.retrieve(query, top_k=self.top_k)

        # 2. Build context
        context = self.context_builder.build(retrieval_result.chunks)

        # 3. Generate answer
        answer = self.generator.generate(query, context)

        return PipelineResult(
            query=query,
            answer=answer,
            retrieved_chunks=retrieval_result.chunks,
            context=context,
            scores=retrieval_result.scores,
        )

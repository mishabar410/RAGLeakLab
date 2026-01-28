"""Tests for RAG pipeline components."""

from ragleaklab.rag import (
    Chunk,
    ContextBuilder,
    Document,
    MockGenerator,
    RAGPipeline,
    TFIDFRetriever,
)


class TestTFIDFRetriever:
    """Tests for TF-IDF retriever."""

    def test_retrieval_deterministic(self):
        """Two retrievals with same query return identical results."""
        docs = [
            Document(doc_id="doc1", text="Machine learning is a subset of AI."),
            Document(doc_id="doc2", text="Natural language processing uses AI."),
            Document(doc_id="doc3", text="Databases store structured data."),
        ]

        retriever1 = TFIDFRetriever(chunk_size=100, chunk_overlap=0)
        retriever1.add_documents(docs)
        result1 = retriever1.retrieve("AI and machine learning", top_k=2)

        retriever2 = TFIDFRetriever(chunk_size=100, chunk_overlap=0)
        retriever2.add_documents(docs)
        result2 = retriever2.retrieve("AI and machine learning", top_k=2)

        assert result1.chunk_ids == result2.chunk_ids
        assert result1.scores == result2.scores

    def test_retrieval_ordering(self):
        """Retrieval returns results in score-descending order."""
        docs = [
            Document(doc_id="doc1", text="Python is a programming language."),
            Document(doc_id="doc2", text="Python programming is fun and easy."),
        ]

        retriever = TFIDFRetriever(chunk_size=100, chunk_overlap=0)
        retriever.add_documents(docs)
        result = retriever.retrieve("Python programming", top_k=2)

        # Scores should be descending
        assert result.scores == sorted(result.scores, reverse=True)

    def test_empty_corpus(self):
        """Retrieval on empty corpus returns empty results."""
        retriever = TFIDFRetriever()
        result = retriever.retrieve("test query", top_k=5)

        assert result.chunks == []
        assert result.scores == []


class TestContextBuilder:
    """Tests for context builder."""

    def test_context_contains_chunk_ids(self):
        """Context contains expected chunk IDs."""
        chunks = [
            Chunk(doc_id="doc1", chunk_id="c0", text="First chunk."),
            Chunk(doc_id="doc2", chunk_id="c1", text="Second chunk."),
        ]

        builder = ContextBuilder()
        context = builder.build(chunks)

        assert "[doc1:c0]" in context
        assert "[doc2:c1]" in context

    def test_context_order_stable(self):
        """Context maintains chunk order."""
        chunks = [
            Chunk(doc_id="a", chunk_id="c0", text="A"),
            Chunk(doc_id="b", chunk_id="c1", text="B"),
            Chunk(doc_id="c", chunk_id="c2", text="C"),
        ]

        builder = ContextBuilder()
        context = builder.build(chunks)
        extracted = builder.extract_chunk_ids(context)

        assert extracted == ["a:c0", "b:c1", "c:c2"]

    def test_empty_chunks(self):
        """Empty chunk list returns empty context."""
        builder = ContextBuilder()
        context = builder.build([])
        assert context == ""


class TestMockGenerator:
    """Tests for mock generator."""

    def test_generator_deterministic(self):
        """Generator produces identical output for same inputs."""
        context = "[doc1:c0]\nMachine learning uses algorithms.\n---\n[doc2:c1]\nAI is growing."
        query = "machine learning"

        gen1 = MockGenerator()
        gen2 = MockGenerator()

        result1 = gen1.generate(query, context)
        result2 = gen2.generate(query, context)

        assert result1 == result2

    def test_generator_extracts_from_context(self):
        """Generator output contains content from context."""
        context = "[doc1:c0]\nNeural networks are powerful."
        query = "neural networks"

        gen = MockGenerator()
        result = gen.generate(query, context)

        # Should extract sentence about neural networks
        assert "neural" in result.lower() or "networks" in result.lower()

    def test_generator_empty_context(self):
        """Generator handles empty context gracefully."""
        gen = MockGenerator()
        result = gen.generate("test", "")
        assert "No context" in result


class TestRAGPipeline:
    """Tests for full RAG pipeline."""

    def test_pipeline_end_to_end(self):
        """Pipeline runs end-to-end and returns expected structure."""
        docs = [
            Document(doc_id="doc1", text="Machine learning enables AI systems."),
            Document(doc_id="doc2", text="Data science uses statistics."),
        ]

        pipeline = RAGPipeline(top_k=2)
        pipeline.add_documents(docs)
        result = pipeline.run("machine learning")

        assert result.query == "machine learning"
        assert result.answer  # Non-empty answer
        assert len(result.retrieved_chunks) > 0
        assert result.context  # Non-empty context

    def test_pipeline_deterministic(self):
        """Pipeline produces identical results for same inputs."""
        docs = [
            Document(doc_id="doc1", text="Python is widely used in data science."),
            Document(doc_id="doc2", text="Java is used for enterprise applications."),
        ]

        # Run 1
        pipeline1 = RAGPipeline(top_k=2)
        pipeline1.add_documents(docs)
        result1 = pipeline1.run("data science")

        # Run 2
        pipeline2 = RAGPipeline(top_k=2)
        pipeline2.add_documents(docs)
        result2 = pipeline2.run("data science")

        assert result1.answer == result2.answer
        assert result1.context == result2.context
        assert [c.full_id for c in result1.retrieved_chunks] == [
            c.full_id for c in result2.retrieved_chunks
        ]

"""Smoke tests for core contracts - verify imports and instantiation."""

from ragleaklab.core.contracts import (
    CaseResult,
    Chunk,
    Document,
    MetricScore,
    ReportSummary,
    RetrievalHit,
    RunArtifact,
)


class TestContractsImportAndInstantiate:
    """Test that all contracts can be imported and instantiated."""

    def test_document_minimal(self):
        """Document with minimal required fields."""
        doc = Document(doc_id="doc1", text="Sample text")
        assert doc.doc_id == "doc1"
        assert doc.text == "Sample text"
        assert doc.metadata is None

    def test_document_with_metadata(self):
        """Document with metadata."""
        doc = Document(doc_id="doc1", text="Text", metadata={"key": "value"})
        assert doc.metadata == {"key": "value"}

    def test_chunk_minimal(self):
        """Chunk with minimal required fields."""
        chunk = Chunk(doc_id="doc1", chunk_id="c0", text="Chunk text")
        assert chunk.doc_id == "doc1"
        assert chunk.chunk_id == "c0"
        assert chunk.full_id == "doc1:c0"

    def test_retrieval_hit(self):
        """RetrievalHit with chunk and score."""
        chunk = Chunk(doc_id="doc1", chunk_id="c0", text="Text")
        hit = RetrievalHit(chunk=chunk, score=0.85)
        assert hit.chunk.doc_id == "doc1"
        assert hit.score == 0.85

    def test_retrieval_hit_no_score(self):
        """RetrievalHit without score."""
        chunk = Chunk(doc_id="doc1", chunk_id="c0", text="Text")
        hit = RetrievalHit(chunk=chunk)
        assert hit.score is None

    def test_run_artifact_minimal(self):
        """RunArtifact with minimal fields."""
        artifact = RunArtifact(
            test_id="test_01",
            threat="canary",
            query="test query",
            answer="test answer",
            context="context",
        )
        assert artifact.test_id == "test_01"
        assert artifact.threat == "canary"
        assert artifact.retrieved == []
        assert artifact.retrieved_ids == []
        assert artifact.scores == []

    def test_run_artifact_with_retrieved(self):
        """RunArtifact with retrieved chunks."""
        chunk = Chunk(doc_id="doc1", chunk_id="c0", text="Text")
        hit = RetrievalHit(chunk=chunk, score=0.9)
        artifact = RunArtifact(
            test_id="test_02",
            threat="verbatim",
            query="query",
            answer="answer",
            context="ctx",
            retrieved=[hit],
            meta={"key": "val"},
        )
        assert len(artifact.retrieved) == 1
        assert artifact.retrieved_ids == ["doc1:c0"]
        assert artifact.scores == [0.9]

    def test_metric_score(self):
        """MetricScore with all fields."""
        score = MetricScore(
            name="canary",
            value=0.0,
            details={"matches": []},
            passed=True,
        )
        assert score.name == "canary"
        assert score.passed is True

    def test_case_result(self):
        """CaseResult with run and scores."""
        artifact = RunArtifact(
            test_id="test_01",
            threat="canary",
            query="q",
            answer="a",
            context="c",
        )
        score = MetricScore(name="canary", value=0.0, passed=True)
        result = CaseResult(
            run=artifact,
            scores=[score],
            passed=True,
            reasons=[],
        )
        assert result.passed is True
        assert len(result.scores) == 1

    def test_report_summary(self):
        """ReportSummary with all fields."""
        summary = ReportSummary(
            overall_pass=True,
            aggregates={"total_cases": 10},
            failures=[],
            meta={"corpus_path": "/path"},
        )
        assert summary.overall_pass is True
        assert summary.schema_version == "2.0.0"
        assert "generated_at" in summary.model_dump()

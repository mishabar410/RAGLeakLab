"""Tests for RunArtifact JSON serialization roundtrip."""

import json

from ragleaklab.core.contracts import Chunk, RetrievalHit, RunArtifact


class TestRunArtifactRoundtrip:
    """Test JSON serialization stability."""

    def test_minimal_roundtrip(self):
        """Minimal RunArtifact survives roundtrip."""
        original = RunArtifact(
            test_id="test_01",
            threat="canary",
            query="test query",
            answer="test answer",
            context="context text",
        )

        # Serialize
        json_str = original.model_dump_json()

        # Deserialize
        restored = RunArtifact.model_validate_json(json_str)

        # Compare
        assert restored.test_id == original.test_id
        assert restored.threat == original.threat
        assert restored.query == original.query
        assert restored.answer == original.answer
        assert restored.context == original.context
        assert restored.retrieved == original.retrieved
        assert restored.timings == original.timings
        assert restored.meta == original.meta

    def test_full_roundtrip(self):
        """Full RunArtifact with all fields survives roundtrip."""
        chunk1 = Chunk(doc_id="doc1", chunk_id="c0", text="Chunk 1 text")
        chunk2 = Chunk(
            doc_id="doc2", chunk_id="c1", text="Chunk 2 text", metadata={"src": "file.txt"}
        )

        original = RunArtifact(
            test_id="test_02",
            threat="verbatim",
            query="original query",
            answer="generated answer",
            context="combined context",
            retrieved=[
                RetrievalHit(chunk=chunk1, score=0.95),
                RetrievalHit(chunk=chunk2, score=0.87),
            ],
            timings={"retrieval_ms": 42.5, "generation_ms": 123.4},
            meta={
                "strategy": "direct_ask",
                "original_query": "original query",
                "tags": ["tag1", "tag2"],
            },
        )

        # Serialize
        json_str = original.model_dump_json()

        # Deserialize
        restored = RunArtifact.model_validate_json(json_str)

        # Compare all fields
        assert restored.test_id == original.test_id
        assert restored.threat == original.threat
        assert restored.query == original.query
        assert restored.answer == original.answer
        assert restored.context == original.context
        assert restored.timings == original.timings
        assert restored.meta == original.meta

        # Compare retrieved
        assert len(restored.retrieved) == 2
        assert restored.retrieved[0].chunk.doc_id == "doc1"
        assert restored.retrieved[0].chunk.chunk_id == "c0"
        assert restored.retrieved[0].score == 0.95
        assert restored.retrieved[1].chunk.metadata == {"src": "file.txt"}

        # Verify computed properties
        assert restored.retrieved_ids == ["doc1:c0", "doc2:c1"]
        assert restored.scores == [0.95, 0.87]

    def test_json_structure(self):
        """Verify JSON structure matches expected format."""
        chunk = Chunk(doc_id="doc1", chunk_id="c0", text="txt")
        artifact = RunArtifact(
            test_id="test_03",
            threat="membership",
            query="q",
            answer="a",
            context="c",
            retrieved=[RetrievalHit(chunk=chunk, score=0.5)],
        )

        # Parse as dict
        data = json.loads(artifact.model_dump_json())

        # Verify structure
        assert "test_id" in data
        assert "retrieved" in data
        assert isinstance(data["retrieved"], list)
        assert len(data["retrieved"]) == 1
        assert "chunk" in data["retrieved"][0]
        assert "score" in data["retrieved"][0]
        assert data["retrieved"][0]["chunk"]["doc_id"] == "doc1"

    def test_idempotent_roundtrip(self):
        """Multiple roundtrips produce identical results."""
        chunk = Chunk(doc_id="d", chunk_id="c", text="t")
        original = RunArtifact(
            test_id="id",
            threat="canary",
            query="q",
            answer="a",
            context="c",
            retrieved=[RetrievalHit(chunk=chunk, score=1.0)],
        )

        # First roundtrip
        json1 = original.model_dump_json()
        restored1 = RunArtifact.model_validate_json(json1)

        # Second roundtrip
        json2 = restored1.model_dump_json()
        restored2 = RunArtifact.model_validate_json(json2)

        # Third roundtrip
        json3 = restored2.model_dump_json()

        # All JSON strings should be identical
        assert json1 == json2
        assert json2 == json3

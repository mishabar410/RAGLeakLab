"""Tests for attack harness."""

from pathlib import Path

from ragleaklab.attacks import (
    AttackStrategy,
    RunArtifact,
    TestCase,
    get_strategy,
    load_cases,
    run_all,
    run_case,
)
from ragleaklab.rag import Document, RAGPipeline


class TestSchema:
    """Tests for attack schemas."""

    def test_testcase_minimal(self):
        """TestCase with minimal required fields."""
        case = TestCase(
            test_id="test_01",
            threat="canary",
            query="secret key",
            strategy="direct_ask",
        )
        assert case.test_id == "test_01"
        assert case.threat == "canary"
        assert case.expected is None

    def test_testcase_full(self):
        """TestCase with all fields."""
        case = TestCase(
            test_id="test_02",
            threat="verbatim",
            query="quote this",
            strategy="quote_request",
            expected="some text",
            description="Test description",
            tags=["tag1", "tag2"],
        )
        assert case.expected == "some text"
        assert len(case.tags) == 2

    def test_runartifact_structure(self):
        """RunArtifact has expected structure."""
        artifact = RunArtifact(
            test_id="test_01",
            threat="canary",
            query="test query",
            answer="test answer",
            context="test context",
            retrieved_ids=["doc1:c0", "doc2:c1"],
            scores=[0.8, 0.5],
            metadata={"expected": "answer"},
        )
        assert artifact.test_id == "test_01"
        assert len(artifact.retrieved_ids) == 2
        assert artifact.answer_contains_expected is True


class TestCatalog:
    """Tests for strategy catalog."""

    def test_get_strategy(self):
        """Get strategy by name."""
        strategy = get_strategy("direct_ask")
        assert isinstance(strategy, AttackStrategy)
        assert strategy.name == "direct_ask"

    def test_strategy_transform(self):
        """Strategy transforms query."""
        strategy = get_strategy("role_confusion")
        result = strategy.transform("secret")
        assert "secret" in result
        assert result != "secret"  # Should be transformed

    def test_unknown_strategy(self):
        """Unknown strategy raises KeyError."""
        import pytest

        with pytest.raises(KeyError):
            get_strategy("nonexistent")


class TestYAMLLoading:
    """Tests for YAML loading."""

    def test_load_canary_cases(self):
        """Load canary extraction cases."""
        cases_path = Path(__file__).parent.parent / "data" / "attacks" / "canary_extraction.yaml"
        cases = load_cases(cases_path)

        assert len(cases) == 10
        assert all(isinstance(c, TestCase) for c in cases)
        assert all(c.threat == "canary" for c in cases)

    def test_load_verbatim_cases(self):
        """Load verbatim extraction cases."""
        cases_path = Path(__file__).parent.parent / "data" / "attacks" / "verbatim_extraction.yaml"
        cases = load_cases(cases_path)

        assert len(cases) == 10
        assert all(isinstance(c, TestCase) for c in cases)
        assert all(c.threat == "verbatim" for c in cases)

    def test_load_directory(self):
        """Load all cases from directory."""
        attacks_dir = Path(__file__).parent.parent / "data" / "attacks"
        cases = load_cases(attacks_dir)

        assert len(cases) == 20  # 10 canary + 10 verbatim


class TestRunner:
    """Tests for attack runner."""

    def test_run_case_returns_artifact(self):
        """run_case returns RunArtifact."""
        docs = [Document(doc_id="doc1", text="Test document content.")]
        pipeline = RAGPipeline(top_k=2)
        pipeline.add_documents(docs)

        case = TestCase(
            test_id="test_run",
            threat="canary",
            query="test",
            strategy="direct_ask",
        )

        artifact = run_case(pipeline, case)
        assert isinstance(artifact, RunArtifact)
        assert artifact.test_id == "test_run"

    def test_run_all_returns_n_artifacts(self):
        """run_all returns N artifacts for N cases."""
        docs = [Document(doc_id="doc1", text="Sample text for testing.")]
        pipeline = RAGPipeline(top_k=2)
        pipeline.add_documents(docs)

        cases = [
            TestCase(test_id=f"test_{i}", threat="canary", query="q", strategy="direct_ask")
            for i in range(5)
        ]

        artifacts = run_all(pipeline, cases)
        assert len(artifacts) == 5
        assert all(isinstance(a, RunArtifact) for a in artifacts)

    def test_run_with_real_cases(self):
        """Run with real YAML cases."""
        # Load corpus
        corpus_path = Path(__file__).parent.parent / "data" / "corpus_private_canary"
        from ragleaklab.corpus import load_corpus

        corpus_docs = load_corpus(corpus_path)
        rag_docs = [Document(doc_id=d.doc_id, text=d.text) for d in corpus_docs]

        pipeline = RAGPipeline(top_k=3)
        pipeline.add_documents(rag_docs)

        # Load cases
        attacks_dir = Path(__file__).parent.parent / "data" / "attacks"
        cases = load_cases(attacks_dir)

        # Run all
        artifacts = run_all(pipeline, cases)
        assert len(artifacts) == 20

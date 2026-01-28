"""Tests for consistency-based membership inference."""

import pytest

from ragleaklab.metrics.consistency import (
    ConsistencyResult,
    _calculate_answer_similarity,
    _calculate_retrieval_consistency,
    _find_dominant_doc_id,
    membership_consistency,
)
from ragleaklab.metrics.paraphrase import (
    extract_query_topic,
    generate_paraphrases,
)
from ragleaklab.targets.base import TargetResponse


class TestParaphrases:
    """Tests for paraphrase generation."""

    def test_generates_correct_count(self):
        """Generates requested number of paraphrases."""
        paraphrases = generate_paraphrases("test topic", count=3)
        assert len(paraphrases) == 3

    def test_includes_original(self):
        """First paraphrase is the original."""
        paraphrases = generate_paraphrases("test topic", count=5)
        assert paraphrases[0] == "test topic"

    def test_deterministic(self):
        """Same input produces same output."""
        p1 = generate_paraphrases("database config", count=5)
        p2 = generate_paraphrases("database config", count=5)
        assert p1 == p2

    def test_max_count_capped(self):
        """Count is capped at available templates."""
        paraphrases = generate_paraphrases("topic", count=100)
        assert len(paraphrases) <= 9  # Number of templates


class TestTopicExtraction:
    """Tests for topic extraction."""

    def test_strips_question_prefix(self):
        """Strips common question prefixes."""
        assert extract_query_topic("what is database config?") == "database config"
        assert extract_query_topic("tell me about API keys") == "API keys"
        assert extract_query_topic("explain the system") == "the system"

    def test_plain_topic(self):
        """Returns plain topic as-is."""
        assert extract_query_topic("database config") == "database config"


class TestRetrievalConsistency:
    """Tests for retrieval consistency calculation."""

    def test_perfect_consistency(self):
        """All same doc_id = 1.0 consistency."""
        doc_ids = [["doc1"], ["doc1"], ["doc1"]]
        assert _calculate_retrieval_consistency(doc_ids) == 1.0

    def test_no_consistency(self):
        """All different doc_ids = low consistency."""
        doc_ids = [["doc1"], ["doc2"], ["doc3"]]
        consistency = _calculate_retrieval_consistency(doc_ids)
        assert consistency == pytest.approx(1 / 3)

    def test_partial_consistency(self):
        """Some overlap = partial consistency."""
        doc_ids = [["doc1"], ["doc1"], ["doc2"]]
        consistency = _calculate_retrieval_consistency(doc_ids)
        assert consistency == pytest.approx(2 / 3)

    def test_empty_lists(self):
        """Empty input = 0.0."""
        assert _calculate_retrieval_consistency([]) == 0.0


class TestAnswerSimilarity:
    """Tests for answer similarity calculation."""

    def test_identical_answers(self):
        """Identical answers = 1.0 similarity."""
        answers = ["the answer is X", "the answer is X"]
        assert _calculate_answer_similarity(answers) == 1.0

    def test_different_answers(self):
        """Completely different answers = 0.0."""
        answers = ["apple banana cherry", "dog elephant fox"]
        similarity = _calculate_answer_similarity(answers)
        assert similarity == 0.0

    def test_partial_overlap(self):
        """Partial overlap = partial similarity."""
        answers = ["the database config is here", "the database settings are here"]
        similarity = _calculate_answer_similarity(answers)
        assert 0.0 < similarity < 1.0


class TestDominantDocId:
    """Tests for dominant doc_id finding."""

    def test_finds_most_common(self):
        """Finds most frequently retrieved doc_id."""
        doc_ids = [["doc1", "doc2"], ["doc1", "doc3"], ["doc2", "doc1"]]
        assert _find_dominant_doc_id(doc_ids) == "doc1"

    def test_empty_returns_none(self):
        """Empty input returns None."""
        assert _find_dominant_doc_id([]) is None
        assert _find_dominant_doc_id([[]]) is None


class MockTarget:
    """Mock target for testing consistency."""

    def __init__(self, doc_id: str, answer: str, vary: bool = False):
        self.doc_id = doc_id
        self.answer = answer
        self.vary = vary
        self.call_count = 0

    def ask(self, query: str) -> TargetResponse:
        self.call_count += 1
        if self.vary:
            # Simulate inconsistent retrieval
            doc_id = f"doc{self.call_count}"
            answer = f"answer {self.call_count}: {query}"
        else:
            doc_id = self.doc_id
            answer = self.answer
        return TargetResponse(
            answer=answer,
            context=f"Context for {doc_id}",
            retrieved_ids=[doc_id],
            scores=[0.9],
        )


class TestMembershipConsistency:
    """Tests for full membership consistency function."""

    def test_consistent_retrieval_high_score(self):
        """Consistent retrieval produces high confidence."""
        target = MockTarget("doc1", "The database configuration is here")
        result = membership_consistency(target, "database config", paraphrase_count=3)

        assert isinstance(result, ConsistencyResult)
        assert result.retrieval_consistency == 1.0
        assert result.score > 0.6  # High confidence

    def test_inconsistent_retrieval_low_score(self):
        """Inconsistent retrieval produces lower confidence."""
        target = MockTarget("doc1", "answer", vary=True)
        result = membership_consistency(target, "random topic", paraphrase_count=3)

        assert result.retrieval_consistency < 0.5
        assert result.score < 0.5  # Lower confidence

    def test_finds_dominant_doc(self):
        """Correctly identifies dominant doc_id."""
        target = MockTarget("important_doc", "The answer")
        result = membership_consistency(target, "test query", paraphrase_count=3)

        assert result.dominant_doc_id == "important_doc"

"""Tests for the example metric plugin."""

from __future__ import annotations

from example_plugin.metric import compute_example_metric


class TestExampleMetric:
    """Tests for compute_example_metric."""

    def test_no_overlap(self):
        result = compute_example_metric("hello world", "foo bar baz")
        assert result["name"] == "example_overlap"
        assert result["value"] == 0.0
        assert result["passed"] is True

    def test_full_overlap(self):
        result = compute_example_metric("the cat sat", "the cat sat")
        assert result["value"] == 1.0
        assert result["passed"] is False  # exceeds default 0.5 threshold

    def test_partial_overlap(self):
        result = compute_example_metric("the cat ran away", "the cat sat on mat")
        # overlap: {"the", "cat"} out of {"the", "cat", "sat", "on", "mat"}
        assert result["value"] == 0.4
        assert result["passed"] is True

    def test_custom_threshold(self):
        result = compute_example_metric("the cat", "the cat sat", threshold=0.3)
        # 2/3 overlap = 0.6667 > 0.3
        assert result["passed"] is False

    def test_empty_reference(self):
        result = compute_example_metric("hello world", "")
        assert result["value"] == 0.0
        assert result["passed"] is True

    def test_empty_response(self):
        result = compute_example_metric("", "hello world")
        assert result["value"] == 0.0
        assert result["passed"] is True

    def test_determinism(self):
        """Same inputs must always produce the same output."""
        r1 = compute_example_metric("the quick brown fox", "the lazy brown dog")
        r2 = compute_example_metric("the quick brown fox", "the lazy brown dog")
        assert r1 == r2


class TestExamplePack:
    """Tests for the example pack."""

    def test_get_queries(self):
        from example_plugin.pack import get_queries

        queries = get_queries()
        assert len(queries) == 3
        for q in queries:
            assert "test_id" in q
            assert "query" in q
            assert "reference" in q

    def test_evaluate(self):
        from example_plugin.pack import evaluate

        result = evaluate(
            test_id="test-001",
            response="The project Phoenix is on track",
            reference="The confidential project codenamed Phoenix is scheduled for Q3.",
        )
        assert result["test_id"] == "test-001"
        assert result["pack"] == "example-overlap"
        assert "value" in result
        assert "passed" in result

    def test_evaluate_no_leakage(self):
        from example_plugin.pack import evaluate

        result = evaluate(
            test_id="test-002",
            response="I cannot provide that information.",
            reference="Internal revenue for Q2 was $4.2 million.",
        )
        assert result["passed"] is True

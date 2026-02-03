"""Tests for attribution analysis."""

from ragleaklab.analysis.attribution import (
    AttributionCategory,
    AttributionReason,
    attribute_leak,
)


class TestAttributeLeak:
    """Tests for attribute_leak function."""

    def test_canary_in_retrieved_gives_retrieval_included_secret(self):
        """When canary detected and chunks retrieved, should attribute to retrieval."""
        reasons = attribute_leak(
            canary_detected=True,
            retrieved_ids=["doc1:0", "doc2:1"],
            context_chars=500,
            n_chunks=2,
            verbatim_score=0.0,
            is_http_target=False,
        )

        categories = [r.category for r in reasons]
        assert AttributionCategory.RETRIEVAL_INCLUDED_SECRET in categories

        # Should have hint
        retrieval_reason = next(
            r for r in reasons if r.category == AttributionCategory.RETRIEVAL_INCLUDED_SECRET
        )
        assert retrieval_reason.hint
        assert len(retrieval_reason.hint) > 0

    def test_no_leak_returns_empty_list(self):
        """When no leak detected, should return empty list."""
        reasons = attribute_leak(
            canary_detected=False,
            retrieved_ids=["doc1:0"],
            context_chars=500,
            n_chunks=1,
            verbatim_score=0.05,
            is_http_target=False,
        )

        assert reasons == []

    def test_large_context_gives_context_too_long(self):
        """When context is large, should include context_too_long reason."""
        reasons = attribute_leak(
            canary_detected=True,
            retrieved_ids=["doc1:0"],
            context_chars=15_000,
            n_chunks=3,
            verbatim_score=0.0,
            is_http_target=False,
        )

        categories = [r.category for r in reasons]
        assert AttributionCategory.CONTEXT_TOO_LONG in categories

    def test_high_chunk_count_gives_top_k_too_high(self):
        """When many chunks retrieved, should include top_k_too_high reason."""
        reasons = attribute_leak(
            canary_detected=True,
            retrieved_ids=["doc1:0"] * 10,
            context_chars=500,
            n_chunks=10,
            verbatim_score=0.0,
            is_http_target=False,
        )

        categories = [r.category for r in reasons]
        assert AttributionCategory.TOP_K_TOO_HIGH in categories

    def test_http_target_gives_overexposed_endpoint(self):
        """HTTP target with leak should include target_overexposed_endpoint."""
        reasons = attribute_leak(
            canary_detected=True,
            retrieved_ids=["doc1:0"],
            context_chars=500,
            n_chunks=1,
            verbatim_score=0.0,
            is_http_target=True,
        )

        categories = [r.category for r in reasons]
        assert AttributionCategory.TARGET_OVEREXPOSED_ENDPOINT in categories

    def test_verbatim_leak_triggers_attribution(self):
        """High verbatim score should trigger attribution analysis."""
        reasons = attribute_leak(
            canary_detected=False,
            retrieved_ids=["doc1:0"],
            context_chars=500,
            n_chunks=1,
            verbatim_score=0.25,
            is_http_target=True,
        )

        # Should have at least the HTTP overexposed reason
        categories = [r.category for r in reasons]
        assert AttributionCategory.TARGET_OVEREXPOSED_ENDPOINT in categories


class TestAttributionReason:
    """Tests for AttributionReason model."""

    def test_model_serialization(self):
        """AttributionReason should serialize correctly."""
        reason = AttributionReason(
            category=AttributionCategory.RETRIEVAL_INCLUDED_SECRET,
            description="Test description",
            hint="Test hint",
        )

        data = reason.model_dump()
        assert data["category"] == "retrieval_included_secret"
        assert data["description"] == "Test description"
        assert data["hint"] == "Test hint"

"""Tests for claims layer."""

from pathlib import Path

import pytest

from ragleaklab.corpus import (
    Claim,
    CorpusWithClaims,
    index_claims_by_doc,
    load_claims,
    load_corpus,
    load_corpus_with_claims,
)


class TestClaimModel:
    """Tests for Claim model."""

    def test_claim_required_fields(self):
        """Claim requires doc_id, claim_id, text."""
        claim = Claim(doc_id="doc1", claim_id="C001", text="secret fact")
        assert claim.doc_id == "doc1"
        assert claim.claim_id == "C001"
        assert claim.text == "secret fact"

    def test_claim_defaults(self):
        """Claim has sensible defaults."""
        claim = Claim(doc_id="doc1", claim_id="C001", text="fact")
        assert claim.type == "general"
        assert claim.sensitivity == "medium"
        assert claim.tags == []

    def test_claim_sensitivity_values(self):
        """Claim accepts all sensitivity values."""
        for level in ["high", "medium", "low"]:
            claim = Claim(doc_id="doc1", claim_id="C001", text="fact", sensitivity=level)
            assert claim.sensitivity == level


class TestLoadClaims:
    """Tests for load_claims function."""

    def test_load_claims_from_fixture(self):
        """Load claims from test fixture."""
        claims = load_claims("data/corpus_private_claims/claims.jsonl")
        assert len(claims) >= 20
        for claim in claims:
            assert isinstance(claim, Claim)

    def test_load_claims_not_found(self):
        """FileNotFoundError when claims file missing."""
        with pytest.raises(FileNotFoundError):
            load_claims("nonexistent/claims.jsonl")

    def test_load_claims_parses_fields(self):
        """Claims fields are correctly parsed."""
        claims = load_claims("data/corpus_private_claims/claims.jsonl")
        # Find a known claim
        high_claims = [c for c in claims if c.sensitivity == "high"]
        assert len(high_claims) > 0

        # Check structure
        for claim in claims:
            assert claim.doc_id
            assert claim.claim_id
            assert claim.text


class TestIndexClaimsByDoc:
    """Tests for index_claims_by_doc function."""

    def test_index_empty(self):
        """Empty list returns empty dict."""
        assert index_claims_by_doc([]) == {}

    def test_index_single_doc(self):
        """Claims from single doc grouped together."""
        claims = [
            Claim(doc_id="doc1", claim_id="C1", text="fact1"),
            Claim(doc_id="doc1", claim_id="C2", text="fact2"),
        ]
        index = index_claims_by_doc(claims)
        assert "doc1" in index
        assert len(index["doc1"]) == 2

    def test_index_multiple_docs(self):
        """Claims from multiple docs indexed separately."""
        claims = [
            Claim(doc_id="doc1", claim_id="C1", text="fact1"),
            Claim(doc_id="doc2", claim_id="C2", text="fact2"),
            Claim(doc_id="doc1", claim_id="C3", text="fact3"),
        ]
        index = index_claims_by_doc(claims)
        assert len(index["doc1"]) == 2
        assert len(index["doc2"]) == 1


class TestLoadCorpusWithClaims:
    """Tests for load_corpus_with_claims function."""

    def test_load_with_claims_fixture(self):
        """Load corpus with claims from fixture."""
        result = load_corpus_with_claims("data/corpus_private_claims")
        assert isinstance(result, CorpusWithClaims)
        assert len(result.documents) >= 2
        assert len(result.claims_index) >= 1

    def test_load_without_claims_file(self):
        """Corpus without claims file returns empty index."""
        result = load_corpus_with_claims("data/corpus_private_canary")
        assert isinstance(result, CorpusWithClaims)
        assert len(result.documents) >= 1
        assert result.claims_index == {}

    def test_load_explicit_claims_path(self, tmp_path: Path):
        """Explicit claims_path overrides auto-discovery."""
        # Create a temp claims file
        claims_file = tmp_path / "my_claims.jsonl"
        claims_file.write_text('{"doc_id": "x", "claim_id": "C1", "text": "custom"}\n')

        result = load_corpus_with_claims(
            "data/corpus_private_canary",
            claims_path=claims_file,
        )
        assert len(result.claims_index) == 1
        assert "x" in result.claims_index

    def test_backward_compatible_load_corpus(self):
        """Original load_corpus still works."""
        docs = load_corpus("data/corpus_private_claims")
        assert len(docs) >= 2
        # Returns list, not CorpusWithClaims
        assert isinstance(docs, list)

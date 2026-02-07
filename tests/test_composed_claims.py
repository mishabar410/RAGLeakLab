"""Tests for corpus/composed_claims.py."""

import json
import logging

import pytest

from ragleaklab.corpus.composed_claims import (
    ComposedClaim,
    load_composed_claims,
)


class TestComposedClaim:
    """Tests for ComposedClaim model validation."""

    def _make_components(self, doc_ids: list[str]) -> list[dict]:
        return [
            {"doc_id": did, "fragment": f"fragment from {did}"}
            for did in doc_ids
        ]

    def test_valid_composed_claim(self):
        claim = ComposedClaim(
            claim_id="CC-001",
            text="Combined fact",
            components=self._make_components(["doc1", "doc2"]),
        )
        assert claim.claim_id == "CC-001"
        assert len(claim.components) == 2

    def test_fewer_than_2_components_raises(self):
        with pytest.raises(ValueError, match="at least 2 components"):
            ComposedClaim(
                claim_id="CC-001",
                text="Bad",
                components=self._make_components(["doc1"]),
            )

    def test_same_doc_id_raises(self):
        with pytest.raises(ValueError, match="at least 2 distinct documents"):
            ComposedClaim(
                claim_id="CC-001",
                text="Bad",
                components=self._make_components(["doc1", "doc1"]),
            )

    def test_get_required_doc_ids(self):
        claim = ComposedClaim(
            claim_id="CC-001",
            text="Combined",
            components=self._make_components(["doc1", "doc2", "doc1"]),
        )
        doc_ids = claim.get_required_doc_ids()
        assert set(doc_ids) == {"doc1", "doc2"}

    def test_default_fields(self):
        claim = ComposedClaim(
            claim_id="CC-001",
            text="Test",
            components=self._make_components(["a", "b"]),
        )
        assert claim.type == "composed"
        assert claim.sensitivity == "high"
        assert claim.tags == []


class TestLoadComposedClaims:
    """Tests for load_composed_claims function."""

    def _claim_dict(self, claim_id: str) -> dict:
        return {
            "claim_id": claim_id,
            "text": f"Claim {claim_id}",
            "components": [
                {"doc_id": "doc1", "fragment": "f1"},
                {"doc_id": "doc2", "fragment": "f2"},
            ],
        }

    def test_load_valid_file(self, tmp_path):
        p = tmp_path / "claims.jsonl"
        lines = [json.dumps(self._claim_dict("CC-001")), json.dumps(self._claim_dict("CC-002"))]
        p.write_text("\n".join(lines))

        claims = load_composed_claims(p)
        assert len(claims) == 2
        assert claims[0].claim_id == "CC-001"

    def test_skip_blank_lines(self, tmp_path):
        p = tmp_path / "claims.jsonl"
        p.write_text(json.dumps(self._claim_dict("CC-001")) + "\n\n\n")
        claims = load_composed_claims(p)
        assert len(claims) == 1

    def test_warn_invalid_json(self, tmp_path, caplog):
        p = tmp_path / "claims.jsonl"
        p.write_text("not-json\n")
        with caplog.at_level(logging.WARNING, logger="ragleaklab.corpus.composed_claims"):
            claims = load_composed_claims(p)
        assert len(claims) == 0
        assert "Invalid JSON" in caplog.text

    def test_warn_invalid_claim(self, tmp_path, caplog):
        """A valid JSON line that fails ComposedClaim validation."""
        p = tmp_path / "claims.jsonl"
        # Missing required fields
        p.write_text(json.dumps({"claim_id": "CC-001"}) + "\n")
        with caplog.at_level(logging.WARNING, logger="ragleaklab.corpus.composed_claims"):
            claims = load_composed_claims(p)
        assert len(claims) == 0
        assert "Failed to parse" in caplog.text

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_composed_claims("/nonexistent/path.jsonl")

    def test_accepts_string_path(self, tmp_path):
        p = tmp_path / "claims.jsonl"
        p.write_text(json.dumps(self._claim_dict("CC-001")))
        claims = load_composed_claims(str(p))
        assert len(claims) == 1

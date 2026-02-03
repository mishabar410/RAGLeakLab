"""Tests for synthetic corpus generator."""

import hashlib
from pathlib import Path

from ragleaklab.corpus.generate import generate_synthetic_corpus


def _hash_file(path: Path) -> str:
    """Compute SHA256 hash of file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestDeterminism:
    """Tests for deterministic generation."""

    def test_same_seed_same_claims(self, tmp_path: Path):
        """Same seed produces identical claims."""
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"

        generate_synthetic_corpus(out1, seed=1337, n_docs=5, claims_per_doc=2)
        generate_synthetic_corpus(out2, seed=1337, n_docs=5, claims_per_doc=2)

        hash1 = _hash_file(out1 / "claims.jsonl")
        hash2 = _hash_file(out2 / "claims.jsonl")

        assert hash1 == hash2, "Same seed should produce identical claims"

    def test_different_seed_different_claims(self, tmp_path: Path):
        """Different seeds produce different claims."""
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"

        generate_synthetic_corpus(out1, seed=1337, n_docs=5, claims_per_doc=2)
        generate_synthetic_corpus(out2, seed=9999, n_docs=5, claims_per_doc=2)

        hash1 = _hash_file(out1 / "claims.jsonl")
        hash2 = _hash_file(out2 / "claims.jsonl")

        assert hash1 != hash2, "Different seeds should produce different claims"


class TestGenerateCorpus:
    """Tests for generate_synthetic_corpus function."""

    def test_creates_documents(self, tmp_path: Path):
        """Creates correct number of document files."""
        generate_synthetic_corpus(tmp_path, seed=42, n_docs=5, claims_per_doc=3)

        txt_files = list(tmp_path.glob("*.txt"))
        assert len(txt_files) == 5

    def test_creates_claims_jsonl(self, tmp_path: Path):
        """Creates claims.jsonl with correct number of claims."""
        generate_synthetic_corpus(tmp_path, seed=42, n_docs=5, claims_per_doc=3)

        claims_file = tmp_path / "claims.jsonl"
        assert claims_file.exists()

        lines = claims_file.read_text().strip().split("\n")
        assert len(lines) == 15  # 5 docs * 3 claims

    def test_creates_manifest(self, tmp_path: Path):
        """Creates manifest.json with correct metadata."""
        import json

        generate_synthetic_corpus(tmp_path, seed=42, n_docs=5, claims_per_doc=3)

        manifest_file = tmp_path / "manifest.json"
        assert manifest_file.exists()

        stored = json.loads(manifest_file.read_text())
        assert stored["seed"] == 42
        assert stored["n_docs"] == 5
        assert stored["claims_per_doc"] == 3
        assert stored["total_claims"] == 15
        assert "corpus_hash" in stored

    def test_include_pii_flag(self, tmp_path: Path):
        """include_pii=False excludes EMAIL and PHONE claims."""
        import json

        generate_synthetic_corpus(tmp_path, seed=42, n_docs=10, claims_per_doc=5, include_pii=False)

        claims_file = tmp_path / "claims.jsonl"
        claims = [json.loads(line) for line in claims_file.read_text().strip().split("\n")]

        claim_types = {c["type"] for c in claims}
        assert "EMAIL" not in claim_types
        assert "PHONE" not in claim_types

    def test_claims_have_required_fields(self, tmp_path: Path):
        """Claims have all required fields."""
        import json

        generate_synthetic_corpus(tmp_path, seed=42, n_docs=3, claims_per_doc=2)

        claims_file = tmp_path / "claims.jsonl"
        claims = [json.loads(line) for line in claims_file.read_text().strip().split("\n")]

        for claim in claims:
            assert "doc_id" in claim
            assert "claim_id" in claim
            assert "text" in claim
            assert "type" in claim
            assert "sensitivity" in claim
            assert "tags" in claim

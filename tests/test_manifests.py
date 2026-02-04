"""Tests for asset manifest validation and hashing."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ragleaklab.assets import (
    load_attacks_manifest,
    load_corpus_manifest,
    load_pack_manifest,
    validate_hash,
)
from ragleaklab.assets.hash import compute_tree_hash

# Paths to test assets
DATA_DIR = Path(__file__).parent.parent / "data"
PACKS_DIR = Path(__file__).parent.parent / "src" / "ragleaklab" / "packs" / "v1"


class TestCorpusManifest:
    """Tests for corpus manifest validation."""

    def test_corpus_public_manifest_loads(self):
        """corpus_public/corpus.yaml validates against schema."""
        manifest = load_corpus_manifest(DATA_DIR / "corpus_public" / "corpus.yaml")
        assert manifest.name == "corpus_public"
        assert manifest.version == "1.0.0"
        assert manifest.doc_count == 2

    def test_corpus_private_canary_manifest_loads(self):
        """corpus_private_canary/corpus.yaml validates against schema."""
        manifest = load_corpus_manifest(DATA_DIR / "corpus_private_canary" / "corpus.yaml")
        assert manifest.name == "corpus_private_canary"
        assert manifest.doc_count == 2

    def test_corpus_private_claims_manifest_loads(self):
        """corpus_private_claims/corpus.yaml validates with claims."""
        manifest = load_corpus_manifest(DATA_DIR / "corpus_private_claims" / "corpus.yaml")
        assert manifest.name == "corpus_private_claims"
        assert "EMAIL" in manifest.claims_supported
        assert "ACCOUNT_ID" in manifest.claims_supported

    def test_corpus_hash_validates(self):
        """Hash in corpus manifest matches actual file tree."""
        manifest = load_corpus_manifest(DATA_DIR / "corpus_public" / "corpus.yaml")
        assert validate_hash(manifest, DATA_DIR / "corpus_public")


class TestAttacksManifest:
    """Tests for attacks manifest validation."""

    def test_attacks_manifest_loads(self):
        """data/attacks/attacks.yaml validates against schema."""
        manifest = load_attacks_manifest(DATA_DIR / "attacks" / "attacks.yaml")
        assert manifest.name == "attacks_default"
        assert "canary" in manifest.threat_coverage
        assert "verbatim" in manifest.threat_coverage
        assert manifest.case_count >= 30

    def test_attacks_hash_validates(self):
        """Hash in attacks manifest matches actual file tree."""
        manifest = load_attacks_manifest(DATA_DIR / "attacks" / "attacks.yaml")
        assert validate_hash(manifest, DATA_DIR / "attacks")


class TestPackManifest:
    """Tests for pack manifest validation."""

    @pytest.mark.parametrize(
        "pack_name",
        ["canary-basic", "verbatim-basic", "membership-basic", "semantic-basic"],
    )
    def test_pack_manifest_loads(self, pack_name: str):
        """All pack manifests validate against schema."""
        manifest = load_pack_manifest(PACKS_DIR / f"{pack_name}.pack.yaml")
        assert manifest.name == pack_name
        assert manifest.version == "1.0.0"
        assert manifest.attacks_ref is not None


class TestHashStability:
    """Tests for deterministic hash computation."""

    def test_hash_is_stable_across_runs(self):
        """Same directory produces same hash on repeated calls."""
        h1 = compute_tree_hash(DATA_DIR / "corpus_public")
        h2 = compute_tree_hash(DATA_DIR / "corpus_public")
        assert h1 == h2

    def test_hash_excludes_manifest_file(self):
        """Hash excludes corpus.yaml from computation."""
        # The hash stored in manifest was computed before adding manifest
        # So hash should still match after manifest is created
        manifest = load_corpus_manifest(DATA_DIR / "corpus_public" / "corpus.yaml")
        current_hash = compute_tree_hash(DATA_DIR / "corpus_public", exclude_manifest=True)
        assert manifest.hash == current_hash

    def test_hash_is_deterministic_hex(self):
        """Hash is valid hex string of correct length (SHA-256)."""
        h = compute_tree_hash(DATA_DIR / "corpus_public")
        assert len(h) == 64  # SHA-256 = 256 bits = 64 hex chars
        assert all(c in "0123456789abcdef" for c in h)


class TestManifestValidation:
    """Tests for manifest validation errors."""

    def test_invalid_manifest_raises_error(self, tmp_path: Path):
        """Missing required fields raise ValidationError."""
        invalid_manifest = tmp_path / "corpus.yaml"
        invalid_manifest.write_text("name: test\n")  # Missing version, doc_count, hash

        with pytest.raises(ValidationError):
            load_corpus_manifest(invalid_manifest)

    def test_missing_manifest_raises_file_not_found(self, tmp_path: Path):
        """Non-existent manifest raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_corpus_manifest(tmp_path / "nonexistent.yaml")

"""Tests for asset validation."""

from pathlib import Path

import yaml

from ragleaklab.assets.validate import (
    validate_assets,
    validate_corpus_manifest,
)


class TestValidateAssets:
    """Tests for validate_assets function."""

    def test_valid_project_manifests(self) -> None:
        """All project manifests should validate successfully."""
        # Validate from project root
        project_root = Path(__file__).parent.parent
        result = validate_assets(project_root)

        # Should find manifests
        assert result.manifests_found > 0, "Expected to find manifests"
        assert result.manifests_valid == result.manifests_found
        assert result.passed is True
        assert len(result.errors) == 0

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Validating empty directory should find no manifests."""
        result = validate_assets(tmp_path)
        assert result.manifests_found == 0
        assert result.passed is True

    def test_invalid_manifest_schema(self, tmp_path: Path) -> None:
        """Invalid manifest schema should produce errors."""
        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()

        # Create invalid manifest (missing required fields)
        manifest_path = corpus_dir / "corpus.yaml"
        manifest_path.write_text("invalid: value\n")

        result = validate_assets(tmp_path)

        assert result.passed is False
        assert len(result.errors) > 0
        assert any("Invalid manifest" in e.message for e in result.errors)

    def test_hash_mismatch(self, tmp_path: Path) -> None:
        """Mismatched hash should produce errors."""
        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()

        # Create a file in the corpus
        (corpus_dir / "doc.txt").write_text("Test document content")

        # Create manifest with wrong hash
        manifest = {
            "name": "test-corpus",
            "version": "1.0.0",
            "doc_count": 1,
            "hash": "0000000000000000000000000000000000000000000000000000000000000000",
        }
        manifest_path = corpus_dir / "corpus.yaml"
        manifest_path.write_text(yaml.dump(manifest))

        result = validate_assets(tmp_path)

        assert result.passed is False
        assert len(result.errors) > 0
        assert any("Hash mismatch" in e.message for e in result.errors)

    def test_valid_corpus_manifest(self, tmp_path: Path) -> None:
        """Valid corpus manifest should pass validation."""
        from ragleaklab.assets.hash import compute_tree_hash

        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()

        # Create a document
        (corpus_dir / "doc.txt").write_text("Test content")

        # Compute actual hash
        actual_hash = compute_tree_hash(corpus_dir, exclude_manifest=True)

        # Create valid manifest
        manifest = {
            "name": "test-corpus",
            "version": "1.0.0",
            "doc_count": 1,
            "hash": actual_hash,
        }
        manifest_path = corpus_dir / "corpus.yaml"
        manifest_path.write_text(yaml.dump(manifest))

        result = validate_assets(tmp_path)

        assert result.passed is True
        assert result.manifests_found == 1
        assert result.manifests_valid == 1
        assert len(result.errors) == 0


class TestValidateCorpusManifest:
    """Tests for validate_corpus_manifest function."""

    def test_missing_manifest(self, tmp_path: Path) -> None:
        """Missing manifest should return file not found error."""
        errors = validate_corpus_manifest(tmp_path / "nonexistent.yaml")
        assert len(errors) == 1
        assert "not found" in errors[0].message.lower()

    def test_schema_validation_error(self, tmp_path: Path) -> None:
        """Invalid schema should return validation error."""
        manifest_path = tmp_path / "corpus.yaml"
        manifest_path.write_text("not_a_valid: manifest\n")

        errors = validate_corpus_manifest(manifest_path)
        assert len(errors) > 0


class TestCLIValidate:
    """Tests for CLI validate command."""

    def test_cli_validate_help(self) -> None:
        """CLI validate command should show help."""
        from typer.testing import CliRunner

        from ragleaklab.__main__ import app

        runner = CliRunner()
        result = runner.invoke(app, ["assets", "validate", "--help"])

        assert result.exit_code == 0
        assert "Validate asset manifests" in result.stdout
        assert "--path" in result.stdout
        assert "--strict" in result.stdout

    def test_cli_validate_project(self) -> None:
        """CLI validate should pass for project manifests."""
        from typer.testing import CliRunner

        from ragleaklab.__main__ import app

        runner = CliRunner()
        result = runner.invoke(app, ["assets", "validate", "--path", "."])

        assert result.exit_code == 0
        assert "All manifests valid" in result.stdout

    def test_cli_validate_invalid_path(self) -> None:
        """CLI validate should fail for non-existent path."""
        from typer.testing import CliRunner

        from ragleaklab.__main__ import app

        runner = CliRunner()
        result = runner.invoke(app, ["assets", "validate", "--path", "/nonexistent/path"])

        assert result.exit_code == 1
        # Error message goes to stderr
        assert "not found" in result.output.lower() or "not found" in (result.stderr or "").lower()

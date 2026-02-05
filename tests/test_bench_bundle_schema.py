"""Tests for benchmark bundle schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from ragleaklab.bench.bundle import BundleManifest, load_bundle


class TestBundleSchema:
    """Test bundle manifest schema validation."""

    def test_load_canonical_bundle(self) -> None:
        """Canonical ragleakbench_v1 bundle loads successfully."""
        bundle_path = (
            Path(__file__).parent.parent
            / "benchmarks"
            / "ragleakbench_v1"
            / "bundle.yaml"
        )

        # Skip if bundle doesn't exist yet
        if not bundle_path.exists():
            pytest.skip("Canonical bundle not found")

        manifest = load_bundle(bundle_path)

        assert manifest.name == "ragleakbench_v1"
        assert manifest.version == "1.0.0"
        assert len(manifest.packs) > 0

    def test_bundle_has_required_fields(self) -> None:
        """Bundle manifest requires name, version, packs."""
        valid = {
            "name": "test",
            "version": "1.0.0",
            "packs": [{"name": "test-pack"}],
        }

        manifest = BundleManifest.model_validate(valid)
        assert manifest.name == "test"

    def test_bundle_missing_name_fails(self) -> None:
        """Bundle without name fails validation."""
        invalid = {
            "version": "1.0.0",
            "packs": [],
        }

        with pytest.raises(ValidationError):
            BundleManifest.model_validate(invalid)

    def test_bundle_missing_version_fails(self) -> None:
        """Bundle without version fails validation."""
        invalid = {
            "name": "test",
            "packs": [],
        }

        with pytest.raises(ValidationError):
            BundleManifest.model_validate(invalid)

    def test_bundle_missing_packs_fails(self) -> None:
        """Bundle without packs list fails validation."""
        invalid = {
            "name": "test",
            "version": "1.0.0",
        }

        with pytest.raises(ValidationError):
            BundleManifest.model_validate(invalid)

    def test_pack_spec_defaults(self) -> None:
        """Pack spec has sensible defaults."""
        valid = {
            "name": "test",
            "version": "1.0.0",
            "packs": [{"name": "my-pack"}],
        }

        manifest = BundleManifest.model_validate(valid)
        pack = manifest.packs[0]

        assert pack.name == "my-pack"
        assert pack.type == "standard"
        assert pack.category == "default"
        assert pack.corpus is None

    def test_pack_spec_with_options(self) -> None:
        """Pack spec accepts all valid options."""
        valid = {
            "name": "test",
            "version": "1.0.0",
            "packs": [
                {
                    "name": "canary-basic",
                    "corpus": "data/corpus_private_canary",
                    "type": "standard",
                    "category": "canary",
                }
            ],
        }

        manifest = BundleManifest.model_validate(valid)
        pack = manifest.packs[0]

        assert pack.corpus == "data/corpus_private_canary"
        assert pack.category == "canary"

    def test_scoring_defaults(self) -> None:
        """Scoring config has sensible defaults."""
        valid = {
            "name": "test",
            "version": "1.0.0",
            "packs": [],
        }

        manifest = BundleManifest.model_validate(valid)

        assert manifest.scoring.severity_weights["high"] == 3.0
        assert manifest.scoring.severity_weights["medium"] == 2.0
        assert manifest.scoring.severity_weights["low"] == 1.0

    def test_load_bundle_file_not_found(self, tmp_path: Path) -> None:
        """load_bundle raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_bundle(tmp_path / "nonexistent.yaml")

    def test_load_yaml_bundle(self, tmp_path: Path) -> None:
        """load_bundle handles YAML files."""
        bundle_file = tmp_path / "bundle.yaml"
        bundle_file.write_text(
            yaml.dump(
                {
                    "name": "yaml-test",
                    "version": "1.0.0",
                    "packs": [{"name": "test-pack"}],
                }
            )
        )

        manifest = load_bundle(bundle_file)
        assert manifest.name == "yaml-test"

    def test_load_json_bundle(self, tmp_path: Path) -> None:
        """load_bundle handles JSON files."""
        import json

        bundle_file = tmp_path / "bundle.json"
        bundle_file.write_text(
            json.dumps(
                {
                    "name": "json-test",
                    "version": "1.0.0",
                    "packs": [{"name": "test-pack"}],
                }
            )
        )

        manifest = load_bundle(bundle_file)
        assert manifest.name == "json-test"

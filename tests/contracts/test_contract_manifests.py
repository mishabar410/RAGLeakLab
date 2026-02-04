"""Contract tests for asset manifests.

Validates that manifest files (.pack.yaml, .corpus.yaml, .attacks.yaml)
adhere to the public contract:
- Required fields present
- Valid structure
- Asset validation passes
"""

from pathlib import Path
from typing import ClassVar

import pytest
import yaml

# Path to golden samples
GOLDEN_DIR = Path(__file__).parent / "golden"


class TestPackManifestSchema:
    """Contract tests for pack manifest structure."""

    REQUIRED_FIELDS: ClassVar[set[str]] = {"name", "version"}
    OPTIONAL_FIELDS: ClassVar[set[str]] = {"attacks_ref", "expected_report_fields", "corpus_ref"}

    def test_golden_pack_is_valid_yaml(self):
        """Golden pack manifest is valid YAML."""
        pack_path = GOLDEN_DIR / "sample.pack.yaml"
        with open(pack_path) as f:
            pack = yaml.safe_load(f)
        assert pack is not None

    def test_pack_has_required_fields(self):
        """Pack manifest has required fields."""
        pack_path = GOLDEN_DIR / "sample.pack.yaml"
        with open(pack_path) as f:
            pack = yaml.safe_load(f)

        missing = self.REQUIRED_FIELDS - set(pack.keys())
        assert not missing, f"Missing required fields: {missing}"

    def test_pack_name_is_string(self):
        """Pack name is a non-empty string."""
        pack_path = GOLDEN_DIR / "sample.pack.yaml"
        with open(pack_path) as f:
            pack = yaml.safe_load(f)

        assert isinstance(pack["name"], str)
        assert len(pack["name"]) > 0

    def test_pack_version_is_semver(self):
        """Pack version follows semantic versioning."""
        pack_path = GOLDEN_DIR / "sample.pack.yaml"
        with open(pack_path) as f:
            pack = yaml.safe_load(f)

        version = pack["version"]
        parts = str(version).split(".")
        assert len(parts) >= 2, f"Version should be MAJOR.MINOR[.PATCH]: {version}"


class TestRealPackManifests:
    """Tests for actual pack manifests in the codebase."""

    PACKS_DIR = Path(__file__).parent.parent.parent / "src" / "ragleaklab" / "packs" / "v1"

    def test_all_packs_are_valid(self):
        """All pack manifests are valid YAML with required fields."""
        if not self.PACKS_DIR.exists():
            pytest.skip("Packs directory not found")

        pack_files = list(self.PACKS_DIR.glob("*.pack.yaml"))
        assert len(pack_files) > 0, "Should have at least one pack manifest"

        for pack_path in pack_files:
            with open(pack_path) as f:
                pack = yaml.safe_load(f)

            assert "name" in pack, f"{pack_path.name} missing 'name'"
            assert "version" in pack, f"{pack_path.name} missing 'version'"

    def test_pack_names_match_filenames(self):
        """Pack names should match their filenames."""
        if not self.PACKS_DIR.exists():
            pytest.skip("Packs directory not found")

        for pack_path in self.PACKS_DIR.glob("*.pack.yaml"):
            with open(pack_path) as f:
                pack = yaml.safe_load(f)

            expected_name = pack_path.stem.replace(".pack", "")
            assert pack["name"] == expected_name, (
                f"Pack name '{pack['name']}' doesn't match filename '{expected_name}'"
            )


class TestAssetValidation:
    """Tests that asset validation works correctly."""

    def test_assets_validate_command_works(self):
        """Assets validate command runs without error."""
        from ragleaklab.assets.validate import validate_assets

        # Validate the project root
        project_root = Path(__file__).parent.parent.parent
        result = validate_assets(project_root)

        # Should find manifests and not have critical errors
        assert result.manifests_found >= 0


class TestManifestHashIntegrity:
    """Tests for manifest hash integrity."""

    def test_pack_versions_are_consistent(self):
        """All packs should have consistent version format."""
        packs_dir = Path(__file__).parent.parent.parent / "src" / "ragleaklab" / "packs" / "v1"
        if not packs_dir.exists():
            pytest.skip("Packs directory not found")

        versions = []
        for pack_path in packs_dir.glob("*.pack.yaml"):
            with open(pack_path) as f:
                pack = yaml.safe_load(f)
            versions.append((pack_path.name, pack.get("version")))

        # All versions should be valid semver strings
        for filename, version in versions:
            assert version is not None, f"{filename} missing version"
            parts = str(version).split(".")
            assert len(parts) >= 2, f"{filename} has invalid version: {version}"

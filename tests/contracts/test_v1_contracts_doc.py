"""Contract tests verifying V1 governance docs exist.

These tests ensure that the V1 contracts documentation and stability
policy are present and correctly cross-referenced.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestV1ContractsDocExists:
    """Verify V1 contract governance files are present."""

    def test_v1_contracts_md_exists(self):
        """docs/V1_CONTRACTS.md must exist and be non-empty."""
        path = PROJECT_ROOT / "docs" / "V1_CONTRACTS.md"
        assert path.exists(), "docs/V1_CONTRACTS.md is missing"
        assert path.stat().st_size > 0, "docs/V1_CONTRACTS.md is empty"

    def test_v1_contracts_md_has_required_sections(self):
        """V1_CONTRACTS.md covers all public contract categories."""
        path = PROJECT_ROOT / "docs" / "V1_CONTRACTS.md"
        content = path.read_text()

        expected_sections = [
            "Report JSON",
            "Per-case Runs",
            "SARIF",
            "JUnit",
            "corpus.yaml",
            "attacks.yaml",
            "pack.yaml",
            "bundle.yaml",
            "CLI Surface",
        ]
        for section in expected_sections:
            assert section in content, f"V1_CONTRACTS.md missing section: {section}"

    def test_stability_md_has_v1_policy(self):
        """docs/STABILITY.md contains V1 Breaking Change Policy."""
        path = PROJECT_ROOT / "docs" / "STABILITY.md"
        assert path.exists(), "docs/STABILITY.md is missing"
        content = path.read_text()
        assert "V1 Breaking Change Policy" in content, (
            "STABILITY.md must contain 'V1 Breaking Change Policy' section"
        )

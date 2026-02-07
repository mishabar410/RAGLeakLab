"""Smoke tests for reference integration configs.

Validates that all ragleaklab.yaml files in integrations/ parse
against the config schema. No servers are started; no network
calls are made.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ragleaklab.config import load_config
from ragleaklab.config.schema import ConfigRoot

PROJECT_ROOT = Path(__file__).parent.parent
INTEGRATIONS_DIR = PROJECT_ROOT / "integrations"


def _find_integration_configs() -> list[Path]:
    """Find all ragleaklab.yaml files in integrations/."""
    return sorted(INTEGRATIONS_DIR.glob("*/ragleaklab.yaml"))


def _find_integration_readmes() -> list[Path]:
    """Find all README.md files in integrations/."""
    return sorted(INTEGRATIONS_DIR.glob("*/README.md"))


# ── parametrized fixtures ────────────────────────────────────────────


class TestIntegrationConfigs:
    """Validate all integration config files against the schema."""

    @pytest.mark.parametrize(
        "config_path",
        _find_integration_configs(),
        ids=lambda p: p.parent.name,
    )
    def test_config_parses_as_valid_yaml(self, config_path: Path):
        """Config file is valid YAML."""
        with open(config_path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), f"{config_path} is not a YAML dict"

    @pytest.mark.parametrize(
        "config_path",
        _find_integration_configs(),
        ids=lambda p: p.parent.name,
    )
    def test_config_validates_against_schema(self, config_path: Path):
        """Config file validates against ConfigRoot pydantic model."""
        cfg = load_config(config_path)
        assert isinstance(cfg, ConfigRoot)

    @pytest.mark.parametrize(
        "config_path",
        _find_integration_configs(),
        ids=lambda p: p.parent.name,
    )
    def test_config_has_http_target(self, config_path: Path):
        """Integration config uses HTTP target type."""
        with open(config_path) as f:
            data = yaml.safe_load(f)
        assert data.get("target", {}).get("type") == "http"

    @pytest.mark.parametrize(
        "config_path",
        _find_integration_configs(),
        ids=lambda p: p.parent.name,
    )
    def test_config_has_url(self, config_path: Path):
        """Integration config specifies a target URL."""
        with open(config_path) as f:
            data = yaml.safe_load(f)
        assert "url" in data.get("target", {})

    @pytest.mark.parametrize(
        "config_path",
        _find_integration_configs(),
        ids=lambda p: p.parent.name,
    )
    def test_config_has_query_placeholder(self, config_path: Path):
        """Request template contains {{query}} placeholder."""
        with open(config_path) as f:
            data = yaml.safe_load(f)
        request_json = data.get("target", {}).get("request_json", {})
        values = " ".join(str(v) for v in request_json.values())
        assert "{{query}}" in values


class TestIntegrationDocs:
    """Validate that each integration has required documentation."""

    @pytest.mark.parametrize(
        "readme_path",
        _find_integration_readmes(),
        ids=lambda p: p.parent.name,
    )
    def test_readme_exists_and_nonempty(self, readme_path: Path):
        """Each integration has a non-empty README."""
        assert readme_path.exists()
        assert readme_path.stat().st_size > 100

    @pytest.mark.parametrize(
        "readme_path",
        _find_integration_readmes(),
        ids=lambda p: p.parent.name,
    )
    def test_readme_has_how_to_run(self, readme_path: Path):
        """README contains a 'How to Run' section."""
        content = readme_path.read_text()
        assert "how to run" in content.lower()

    def test_integrations_dir_has_expected_subdirs(self):
        """integrations/ contains all expected integration directories."""
        expected = {"fastapi", "generic_http", "retrieval_traces"}
        actual = {p.name for p in INTEGRATIONS_DIR.iterdir() if p.is_dir()}
        missing = expected - actual
        assert not missing, f"Missing integration directories: {missing}"

    def test_integrations_doc_exists(self):
        """docs/INTEGRATIONS.md exists and references integrations."""
        doc = PROJECT_ROOT / "docs" / "INTEGRATIONS.md"
        assert doc.exists()
        content = doc.read_text()
        assert "fastapi" in content.lower()
        assert "generic_http" in content.lower() or "generic http" in content.lower()
        assert "retrieval" in content.lower()

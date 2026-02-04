"""Smoke tests for case study configurations.

Validates that all case study YAML configs parse correctly
and assets pass validation.
"""

from pathlib import Path

import pytest
import yaml

from ragleaklab.config import load_config


class TestCaseStudyConfigs:
    """Tests for case study configuration validity."""

    CASE_STUDIES_DIR = Path(__file__).parent.parent / "case_studies"

    @pytest.fixture
    def case_dirs(self) -> list[Path]:
        """Get all case study directories."""
        if not self.CASE_STUDIES_DIR.exists():
            pytest.skip("case_studies/ directory not found")
        return [d for d in self.CASE_STUDIES_DIR.iterdir() if d.is_dir()]

    def test_case_studies_exist(self, case_dirs: list[Path]) -> None:
        """At least one case study should exist."""
        assert len(case_dirs) >= 1, "Expected at least one case study"

    def test_each_case_has_config(self, case_dirs: list[Path]) -> None:
        """Each case study should have a config.yaml."""
        for case_dir in case_dirs:
            config_path = case_dir / "config.yaml"
            assert config_path.exists(), f"Missing config.yaml in {case_dir.name}"

    def test_each_case_has_readme(self, case_dirs: list[Path]) -> None:
        """Each case study should have a README.md."""
        for case_dir in case_dirs:
            readme_path = case_dir / "README.md"
            assert readme_path.exists(), f"Missing README.md in {case_dir.name}"

    def test_configs_parse_valid_yaml(self, case_dirs: list[Path]) -> None:
        """All config.yaml files should be valid YAML."""
        for case_dir in case_dirs:
            config_path = case_dir / "config.yaml"
            if config_path.exists():
                content = config_path.read_text()
                try:
                    data = yaml.safe_load(content)
                    assert isinstance(data, dict), f"Config should be a dict: {case_dir.name}"
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {case_dir.name}: {e}")

    def test_configs_load_successfully(self, case_dirs: list[Path]) -> None:
        """All configs should load via ragleaklab.config.load_config."""
        for case_dir in case_dirs:
            config_path = case_dir / "config.yaml"
            if config_path.exists():
                try:
                    config = load_config(config_path)
                    assert config.target is not None, f"Target missing: {case_dir.name}"
                except Exception as e:
                    pytest.fail(f"Failed to load config {case_dir.name}: {e}")

    def test_case1_fastapi_config(self) -> None:
        """Case 1 config should target localhost:8000."""
        config_path = self.CASE_STUDIES_DIR / "case1_fastapi" / "config.yaml"
        if not config_path.exists():
            pytest.skip("case1_fastapi not found")
        config = load_config(config_path)
        assert config.target.type == "http"
        assert "8000" in config.target.url

    def test_case2_blackbox_config(self) -> None:
        """Case 2 config should target localhost:8001."""
        config_path = self.CASE_STUDIES_DIR / "case2_blackbox_http" / "config.yaml"
        if not config_path.exists():
            pytest.skip("case2_blackbox_http not found")
        config = load_config(config_path)
        assert config.target.type == "http"
        assert "8001" in config.target.url

    def test_case3_trace_config(self) -> None:
        """Case 3 config should target localhost:8002."""
        config_path = self.CASE_STUDIES_DIR / "case3_retrieval_trace" / "config.yaml"
        if not config_path.exists():
            pytest.skip("case3_retrieval_trace not found")
        config = load_config(config_path)
        assert config.target.type == "http"
        assert "8002" in config.target.url


class TestCaseStudyAssets:
    """Tests for case study asset files."""

    CASE_STUDIES_DIR = Path(__file__).parent.parent / "case_studies"

    def test_case2_claims_file_valid(self) -> None:
        """Case 2 claims.yaml should be valid YAML."""
        claims_path = self.CASE_STUDIES_DIR / "case2_blackbox_http" / "claims.yaml"
        if not claims_path.exists():
            pytest.skip("claims.yaml not found")
        content = claims_path.read_text()
        data = yaml.safe_load(content)
        assert "claims" in data
        assert len(data["claims"]) > 0

    def test_readme_contains_setup_section(self) -> None:
        """Each README should have Setup section."""
        if not self.CASE_STUDIES_DIR.exists():
            pytest.skip("case_studies/ not found")
        for case_dir in self.CASE_STUDIES_DIR.iterdir():
            if not case_dir.is_dir():
                continue
            readme = case_dir / "README.md"
            if readme.exists():
                content = readme.read_text()
                assert "## Setup" in content, f"Missing Setup section: {case_dir.name}"

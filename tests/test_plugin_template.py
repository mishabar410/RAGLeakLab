"""Smoke tests for the plugin template.

Validates that the template files are syntactically correct and importable.
This does NOT run the template's own tests — it only checks that the
template code won't fail on import.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "plugin"
SRC_DIR = TEMPLATE_DIR / "src" / "example_plugin"


def _load_module_from_path(name: str, path: Path):
    """Load a Python module from a filesystem path without installing it."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None, f"Could not create spec for {path}"
    assert spec.loader is not None, f"No loader for {path}"
    module = importlib.util.module_from_spec(spec)
    return module, spec


class TestPluginTemplateSyntax:
    """Verify all template Python files parse without syntax errors."""

    @pytest.mark.parametrize(
        "filename",
        ["__init__.py", "metric.py", "pack.py"],
    )
    def test_template_src_parses(self, filename: str):
        """Each source file must be valid Python."""
        filepath = SRC_DIR / filename
        assert filepath.exists(), f"Template file missing: {filepath}"
        source = filepath.read_text()
        # ast.parse raises SyntaxError on invalid Python
        tree = ast.parse(source, filename=str(filepath))
        assert tree is not None

    def test_template_test_parses(self):
        """Template test file must be valid Python."""
        filepath = TEMPLATE_DIR / "tests" / "test_example.py"
        assert filepath.exists(), f"Template test file missing: {filepath}"
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
        assert tree is not None


class TestPluginTemplateStructure:
    """Verify the template has the expected file structure."""

    @pytest.mark.parametrize(
        "relpath",
        [
            "pyproject.toml",
            "README.md",
            "src/example_plugin/__init__.py",
            "src/example_plugin/metric.py",
            "src/example_plugin/pack.py",
            "tests/test_example.py",
        ],
    )
    def test_file_exists(self, relpath: str):
        filepath = TEMPLATE_DIR / relpath
        assert filepath.exists(), f"Expected template file missing: {relpath}"

    def test_pyproject_has_entry_points(self):
        """pyproject.toml must declare ragleaklab.metrics entry point."""
        content = (TEMPLATE_DIR / "pyproject.toml").read_text()
        assert "ragleaklab.metrics" in content

    def test_readme_covers_key_topics(self):
        """README must cover registration, testing, determinism, publishing."""
        content = (TEMPLATE_DIR / "README.md").read_text().lower()
        for topic in ["entry_points", "determinism", "publish", "test"]:
            assert topic in content, f"README missing topic: {topic}"


class TestPluginTemplateImport:
    """Verify that template metric.py can be loaded and called."""

    def test_metric_importable_and_callable(self):
        """metric.py must define compute_example_metric that is callable."""
        spec = importlib.util.spec_from_file_location(
            "example_plugin.metric",
            SRC_DIR / "metric.py",
        )
        assert spec is not None
        assert spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        assert hasattr(mod, "compute_example_metric")
        assert callable(mod.compute_example_metric)

        # Actually call it to verify it works
        result = mod.compute_example_metric("hello world", "hello there")
        assert isinstance(result, dict)
        assert "name" in result
        assert "value" in result
        assert "passed" in result

    def test_metric_determinism(self):
        """Metric must be deterministic."""
        spec = importlib.util.spec_from_file_location(
            "example_plugin.metric_det",
            SRC_DIR / "metric.py",
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        r1 = mod.compute_example_metric("the quick brown fox", "the lazy brown dog")
        r2 = mod.compute_example_metric("the quick brown fox", "the lazy brown dog")
        assert r1 == r2

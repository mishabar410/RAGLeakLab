"""Tests for report schema versioning."""

from ragleaklab.core.version import compute_config_hash, get_tool_version
from ragleaklab.reporting.schema import SCHEMA_VERSION, Report


class TestReportVersioning:
    """Tests for version fields in reports."""

    def test_report_has_schema_version(self):
        """Report includes schema_version field."""
        report = Report(
            total_cases=1,
            canary_extracted=False,
            canary_count=0,
            verbatim_leakage_rate=0.0,
            membership_confidence=0.0,
            overall_pass=True,
            failures=[],
            corpus_path="/path",
            attacks_path="/path",
        )
        assert report.schema_version == SCHEMA_VERSION
        assert report.schema_version == "2.0.0"

    def test_report_has_tool_version(self):
        """Report includes tool_version field."""
        report = Report(
            tool_version="0.1.0",
            total_cases=1,
            canary_extracted=False,
            canary_count=0,
            verbatim_leakage_rate=0.0,
            membership_confidence=0.0,
            overall_pass=True,
            failures=[],
            corpus_path="/path",
            attacks_path="/path",
        )
        assert report.tool_version == "0.1.0"

    def test_report_has_config_hash(self):
        """Report includes config_hash field."""
        report = Report(
            total_cases=1,
            canary_extracted=False,
            canary_count=0,
            verbatim_leakage_rate=0.0,
            membership_confidence=0.0,
            overall_pass=True,
            failures=[],
            corpus_path="/path",
            attacks_path="/path",
            config_hash="abc123def456",
        )
        assert report.config_hash == "abc123def456"

    def test_report_json_contains_versions(self):
        """Serialized report.json contains version fields."""
        report = Report(
            tool_version="0.2.0",
            total_cases=1,
            canary_extracted=False,
            canary_count=0,
            verbatim_leakage_rate=0.0,
            membership_confidence=0.0,
            overall_pass=True,
            failures=[],
            corpus_path="/path",
            attacks_path="/path",
            config_hash="xyz789",
        )

        data = report.model_dump()
        assert "schema_version" in data
        assert "tool_version" in data
        assert "config_hash" in data
        assert data["schema_version"] == "2.0.0"
        assert data["tool_version"] == "0.2.0"
        assert data["config_hash"] == "xyz789"


class TestVersionHelpers:
    """Tests for version utility functions."""

    def test_get_tool_version_returns_string(self):
        """get_tool_version returns a string."""
        ver = get_tool_version()
        assert isinstance(ver, str)
        assert len(ver) > 0

    def test_compute_config_hash_deterministic(self):
        """Same config produces same hash."""
        h1 = compute_config_hash(a="1", b="2")
        h2 = compute_config_hash(a="1", b="2")
        assert h1 == h2

    def test_compute_config_hash_different(self):
        """Different config produces different hash."""
        h1 = compute_config_hash(a="1", b="2")
        h2 = compute_config_hash(a="1", b="3")
        assert h1 != h2

    def test_compute_config_hash_order_independent(self):
        """Argument order doesn't affect hash."""
        h1 = compute_config_hash(a="1", b="2")
        h2 = compute_config_hash(b="2", a="1")
        assert h1 == h2

    def test_compute_config_hash_length(self):
        """Hash is 12 characters."""
        h = compute_config_hash(foo="bar")
        assert len(h) == 12

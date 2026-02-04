"""Contract tests for SARIF export format.

Validates that SARIF output adheres to the SARIF 2.1.0 specification:
- Required structure elements
- Valid version string
- Tool and results structure
"""

import json
from pathlib import Path

# Path to golden samples
GOLDEN_DIR = Path(__file__).parent / "golden"


class TestSarifSchema:
    """Contract tests for SARIF export structure."""

    def test_golden_sarif_is_valid_json(self):
        """Golden SARIF file is valid JSON."""
        sarif_path = GOLDEN_DIR / "sample.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)
        assert sarif is not None

    def test_sarif_has_required_top_level_fields(self):
        """SARIF has required top-level fields."""
        sarif_path = GOLDEN_DIR / "sample.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        assert "version" in sarif, "SARIF must have 'version' field"
        assert "runs" in sarif, "SARIF must have 'runs' field"

    def test_sarif_version_is_2_1_0(self):
        """SARIF version is 2.1.0."""
        sarif_path = GOLDEN_DIR / "sample.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        assert sarif["version"] == "2.1.0", f"SARIF version should be 2.1.0, got {sarif['version']}"

    def test_sarif_runs_is_array(self):
        """SARIF runs is an array."""
        sarif_path = GOLDEN_DIR / "sample.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        assert isinstance(sarif["runs"], list)

    def test_sarif_run_has_tool(self):
        """Each SARIF run has a tool object."""
        sarif_path = GOLDEN_DIR / "sample.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        for run in sarif["runs"]:
            assert "tool" in run, "Each run must have 'tool'"
            assert "driver" in run["tool"], "Tool must have 'driver'"

    def test_sarif_tool_driver_has_name_and_version(self):
        """SARIF tool driver has name and version."""
        sarif_path = GOLDEN_DIR / "sample.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        for run in sarif["runs"]:
            driver = run["tool"]["driver"]
            assert "name" in driver, "Driver must have 'name'"
            assert "version" in driver, "Driver must have 'version'"

    def test_sarif_run_has_results(self):
        """Each SARIF run has results array."""
        sarif_path = GOLDEN_DIR / "sample.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        for run in sarif["runs"]:
            assert "results" in run, "Each run must have 'results'"
            assert isinstance(run["results"], list)

    def test_sarif_result_has_required_fields(self):
        """SARIF results have required fields."""
        sarif_path = GOLDEN_DIR / "sample.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        for run in sarif["runs"]:
            for result in run["results"]:
                assert "ruleId" in result, "Result must have 'ruleId'"
                assert "message" in result, "Result must have 'message'"

    def test_sarif_result_message_has_text(self):
        """SARIF result message has text."""
        sarif_path = GOLDEN_DIR / "sample.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        for run in sarif["runs"]:
            for result in run["results"]:
                assert "text" in result["message"], "Message must have 'text'"

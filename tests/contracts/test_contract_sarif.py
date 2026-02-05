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


class TestIntegritySarifSchema:
    """Contract tests for integrity SARIF with RAGLEAKLAB-INTEGRITY-* rules."""

    def test_integrity_sarif_is_valid_json(self):
        """Golden integrity SARIF file is valid JSON."""
        sarif_path = GOLDEN_DIR / "integrity.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)
        assert sarif is not None

    def test_integrity_sarif_has_integrity_rules(self):
        """Integrity SARIF contains RAGLEAKLAB-INTEGRITY-* rules."""
        sarif_path = GOLDEN_DIR / "integrity.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = [r["id"] for r in rules]

        assert "RAGLEAKLAB-INTEGRITY-RETRIEVAL-HIJACK" in rule_ids
        assert "RAGLEAKLAB-INTEGRITY-CLAIM-CORRUPTION" in rule_ids
        assert "RAGLEAKLAB-INTEGRITY-SENTINEL-TAKEOVER" in rule_ids

    def test_integrity_results_have_pack_and_query_location(self):
        """Integrity SARIF results have pack_id and query_id in locations."""
        sarif_path = GOLDEN_DIR / "integrity.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        results = sarif["runs"][0]["results"]
        for result in results:
            # Check location structure
            assert "locations" in result, "Result must have 'locations'"
            assert len(result["locations"]) > 0, "Result must have at least one location"

            location = result["locations"][0]
            assert "physicalLocation" in location
            assert "artifactLocation" in location["physicalLocation"]

            uri = location["physicalLocation"]["artifactLocation"]["uri"]
            assert uri.startswith("assets/"), f"URI should start with 'assets/', got {uri}"

    def test_integrity_results_have_properties(self):
        """Integrity SARIF results have pack_id/query_id/severity/confidence in properties."""
        sarif_path = GOLDEN_DIR / "integrity.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        results = sarif["runs"][0]["results"]
        for result in results:
            props = result.get("properties", {})
            assert "pack_id" in props, "Result properties must have 'pack_id'"
            assert "query_id" in props, "Result properties must have 'query_id'"
            assert "severity" in props, "Result properties must have 'severity'"
            assert "confidence" in props, "Result properties must have 'confidence'"

    def test_integrity_rule_ids_match_results(self):
        """All integrity result ruleIds are defined in rules."""
        sarif_path = GOLDEN_DIR / "integrity.sarif"
        with open(sarif_path) as f:
            sarif = json.load(f)

        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        defined_rule_ids = {r["id"] for r in rules}

        results = sarif["runs"][0]["results"]
        for result in results:
            rule_id = result["ruleId"]
            assert rule_id in defined_rule_ids, f"ruleId '{rule_id}' not defined in rules"

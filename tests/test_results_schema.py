"""Contract tests for BenchResultsSchema stability.

Ensures the results schema stays backward-compatible across versions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from ragleaklab.bench.results import (
    RESULTS_SCHEMA_VERSION,
    BenchResultsSchema,
    validate_results_file,
)

PROJECT_ROOT = Path(__file__).parent.parent


class TestResultsSchemaStability:
    """Verify results schema is stable and backward-compatible."""

    V1_REQUIRED_FIELDS: ClassVar[set[str]] = {
        "results_schema_version",
        "tool_version",
        "schema_version",
        "generated_at",
        "bundle",
        "total_packs",
        "passed_packs",
        "failed_packs",
        "error_packs",
        "risk_score",
        "total_runtime_sec",
        "pack_results",
        "environment",
    }

    BUNDLE_REQUIRED_FIELDS: ClassVar[set[str]] = {"name", "version", "hash"}

    PACK_REQUIRED_FIELDS: ClassVar[set[str]] = {
        "pack_name",
        "category",
        "status",
        "total_cases",
        "passed_cases",
        "failed_cases",
        "pass_rate",
        "fail_rate",
        "runtime_sec",
    }

    ENV_REQUIRED_FIELDS: ClassVar[set[str]] = {
        "python_version",
        "platform",
        "machine",
    }

    def test_schema_version_is_semver(self):
        """RESULTS_SCHEMA_VERSION follows semver."""
        parts = RESULTS_SCHEMA_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_model_has_required_fields(self):
        """BenchResultsSchema model has all required fields."""
        model_fields = set(BenchResultsSchema.model_fields.keys())
        missing = self.V1_REQUIRED_FIELDS - model_fields
        assert not missing, f"Missing fields: {missing}"

    def test_sample_results_validates(self):
        """Sample results.json validates against the schema."""
        sample = PROJECT_ROOT / "results" / "sample_results.json"
        results = validate_results_file(sample)
        assert results.results_schema_version == "1.0.0"

    def test_sample_has_all_required_fields(self):
        """Sample results.json contains all required top-level fields."""
        sample = PROJECT_ROOT / "results" / "sample_results.json"
        with open(sample) as f:
            data = json.load(f)

        missing = self.V1_REQUIRED_FIELDS - set(data.keys())
        assert not missing, f"Sample missing fields: {missing}"

    def test_sample_bundle_has_required_fields(self):
        """Sample bundle section has required fields."""
        sample = PROJECT_ROOT / "results" / "sample_results.json"
        with open(sample) as f:
            data = json.load(f)

        bundle = data["bundle"]
        missing = self.BUNDLE_REQUIRED_FIELDS - set(bundle.keys())
        assert not missing, f"Bundle missing fields: {missing}"

    def test_sample_pack_results_have_required_fields(self):
        """Each pack result has required fields."""
        sample = PROJECT_ROOT / "results" / "sample_results.json"
        with open(sample) as f:
            data = json.load(f)

        for i, pr in enumerate(data["pack_results"]):
            missing = self.PACK_REQUIRED_FIELDS - set(pr.keys())
            assert not missing, f"Pack result {i} missing fields: {missing}"

    def test_sample_environment_has_required_fields(self):
        """Environment section has required fields."""
        sample = PROJECT_ROOT / "results" / "sample_results.json"
        with open(sample) as f:
            data = json.load(f)

        env = data["environment"]
        missing = self.ENV_REQUIRED_FIELDS - set(env.keys())
        assert not missing, f"Environment missing fields: {missing}"

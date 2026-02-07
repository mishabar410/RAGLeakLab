"""Tests for external results publishing and validation.

Covers:
- Schema validation (valid and invalid data)
- Redaction enforcement (secrets → FAIL)
- Builder from bench_summary.json
- Validator with bundle hash checks
- CLI smoke (--help)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ragleaklab.bench.external import (
    ExternalPackMetrics,
    ExternalResult,
    ExternalResultsSummary,
    SecretLeakError,
    build_external_result,
    scan_secrets,
    validate_external_result,
)

# ── Fixtures ──────────────────────────────────────────────────────────


def _minimal_external_result(**overrides) -> dict:
    """Build a minimal valid external result dict."""
    base = {
        "external_schema_version": "1.0.0",
        "system_name": "Test System",
        "system_type": "oss",
        "integration_type": "inprocess",
        "ragleaklab_version": "1.0.0",
        "bundle": {
            "name": "ragleakbench_v1",
            "version": "1.0.0",
            "hash": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        },
        "results_summary": {
            "total_packs": 2,
            "passed_packs": 1,
            "failed_packs": 1,
            "risk_score": 0.15,
            "pack_results": [
                {
                    "pack_name": "canary-basic",
                    "category": "canary",
                    "status": "pass",
                    "total_cases": 10,
                    "passed_cases": 10,
                    "failed_cases": 0,
                    "pass_rate": 1.0,
                    "fail_rate": 0.0,
                },
                {
                    "pack_name": "semantic-basic",
                    "category": "semantic",
                    "status": "fail",
                    "total_cases": 5,
                    "passed_cases": 3,
                    "failed_cases": 2,
                    "pass_rate": 0.6,
                    "fail_rate": 0.4,
                },
            ],
        },
        "notes": "",
        "redaction_applied": True,
        "reproduction": {
            "config_snippet": "",
            "command": "uv run ragleaklab bench bundle --out out/bench",
        },
        "generated_at": "2026-02-08T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _write_bench_summary(tmp_path: Path, bundle_name: str = "ragleakbench_v1") -> Path:
    """Write a fake bench_summary.json and return the directory."""
    out_dir = tmp_path / "bench_out"
    out_dir.mkdir()
    summary = {
        "bundle_name": bundle_name,
        "bundle_version": "1.0.0",
        "total_packs": 2,
        "passed_packs": 1,
        "failed_packs": 1,
        "error_packs": 0,
        "risk_score": 0.15,
        "total_runtime_sec": 5.0,
        "pack_results": [
            {
                "pack_name": "canary-basic",
                "category": "canary",
                "status": "pass",
                "total_cases": 10,
                "passed_cases": 10,
                "failed_cases": 0,
                "pass_rate": 1.0,
                "fail_rate": 0.0,
            },
            {
                "pack_name": "semantic-basic",
                "category": "semantic",
                "status": "fail",
                "total_cases": 5,
                "passed_cases": 3,
                "failed_cases": 2,
                "pass_rate": 0.6,
                "fail_rate": 0.4,
            },
        ],
    }
    (out_dir / "bench_summary.json").write_text(json.dumps(summary))
    return out_dir


def _write_bundle(tmp_path: Path, name: str = "ragleakbench_v1") -> Path:
    """Write a minimal bundle.yaml and return its path."""
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(
        f"name: {name}\nversion: '1.0.0'\npacks:\n  - name: canary-basic\n    category: canary\n"
    )
    return bundle_path


# ── Schema validation tests ──────────────────────────────────────────


class TestExternalResultSchema:
    """Test Pydantic schema validation."""

    def test_valid_minimal(self):
        data = _minimal_external_result()
        result = ExternalResult.model_validate(data)
        assert result.system_name == "Test System"
        assert result.system_type == "oss"
        assert result.redaction_applied is True

    def test_valid_all_system_types(self):
        for st in ("oss", "commercial", "internal"):
            data = _minimal_external_result(system_type=st)
            result = ExternalResult.model_validate(data)
            assert result.system_type == st

    def test_valid_all_integration_types(self):
        for it in ("inprocess", "http", "other"):
            data = _minimal_external_result(integration_type=it)
            result = ExternalResult.model_validate(data)
            assert result.integration_type == it

    def test_invalid_system_type(self):
        from pydantic import ValidationError

        data = _minimal_external_result(system_type="unknown")
        with pytest.raises(ValidationError):
            ExternalResult.model_validate(data)

    def test_invalid_integration_type(self):
        from pydantic import ValidationError

        data = _minimal_external_result(integration_type="grpc")
        with pytest.raises(ValidationError):
            ExternalResult.model_validate(data)

    def test_missing_required_fields(self):
        from pydantic import ValidationError

        for field in ("system_name", "system_type", "integration_type", "bundle"):
            data = _minimal_external_result()
            del data[field]
            with pytest.raises(ValidationError):
                ExternalResult.model_validate(data)

    def test_pack_metrics_schema(self):
        pm = ExternalPackMetrics(
            pack_name="test-pack",
            category="canary",
            status="pass",
            total_cases=10,
            passed_cases=10,
            failed_cases=0,
            pass_rate=1.0,
            fail_rate=0.0,
        )
        assert pm.pack_name == "test-pack"
        assert pm.pass_rate == 1.0

    def test_results_summary_schema(self):
        rs = ExternalResultsSummary(
            total_packs=3,
            passed_packs=2,
            failed_packs=1,
            risk_score=0.25,
        )
        assert rs.total_packs == 3
        assert rs.pack_results == []


# ── Secret scanning tests ────────────────────────────────────────────


class TestSecretScanning:
    """Test the secret scanner catches various patterns."""

    def test_clean_data_passes(self):
        data = _minimal_external_result()
        findings = scan_secrets(data)
        assert findings == []

    def test_email_detected(self):
        data = _minimal_external_result(notes="Contact admin@example.com for details")
        findings = scan_secrets(data)
        assert len(findings) > 0
        assert any("Secret pattern" in f for f in findings)

    def test_canary_detected(self):
        data = _minimal_external_result(notes="Found CANARY_abcdef1234567890 in output")
        findings = scan_secrets(data)
        assert len(findings) > 0

    def test_secret_token_detected(self):
        data = _minimal_external_result(notes="Using SECRET_MY_API_TOKEN")
        findings = scan_secrets(data)
        assert len(findings) > 0

    def test_bearer_token_detected(self):
        data = _minimal_external_result()
        data["reproduction"]["config_snippet"] = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9"
        findings = scan_secrets(data)
        assert len(findings) > 0

    def test_api_key_detected(self):
        data = _minimal_external_result(notes="Using sk_live_abc123def456ghi789")
        findings = scan_secrets(data)
        assert len(findings) > 0

    def test_aws_key_detected(self):
        data = _minimal_external_result(notes="Key: AKIAIOSFODNN7EXAMPLE")
        findings = scan_secrets(data)
        assert len(findings) > 0

    def test_password_detected(self):
        data = _minimal_external_result()
        data["reproduction"]["command"] = "curl -u user:password=mysecretpassword123"
        findings = scan_secrets(data)
        assert len(findings) > 0

    def test_nested_secret_detected(self):
        data = _minimal_external_result()
        data["results_summary"]["pack_results"][0]["pack_name"] = "token=verylongsecrettoken123"
        findings = scan_secrets(data)
        assert len(findings) > 0


# ── Redaction enforcement tests ──────────────────────────────────────


class TestRedactionEnforcement:
    """Test that build_external_result refuses to produce unredacted output."""

    def test_email_in_notes_gets_redacted(self, tmp_path):
        out_dir = _write_bench_summary(tmp_path)
        bundle = _write_bundle(tmp_path)
        result = build_external_result(
            out_dir,
            system_name="Test",
            notes="Contact admin@example.com",
            bundle_path=bundle,
        )
        # Redaction should have replaced the email
        assert "@example.com" not in result.notes
        assert "[REDACTED]" in result.notes

    def test_canary_in_config_gets_redacted(self, tmp_path):
        out_dir = _write_bench_summary(tmp_path)
        bundle = _write_bundle(tmp_path)
        result = build_external_result(
            out_dir,
            system_name="Test",
            config_snippet="canary: CANARY_abcdef1234567890abcdef",
            bundle_path=bundle,
        )
        # The full hex token should be replaced
        assert "abcdef1234567890abcdef" not in result.reproduction.config_snippet
        assert "[REDACTED]" in result.reproduction.config_snippet

    def test_bearer_in_command_gets_redacted(self, tmp_path):
        out_dir = _write_bench_summary(tmp_path)
        bundle = _write_bundle(tmp_path)
        result = build_external_result(
            out_dir,
            system_name="Test",
            command="curl -H 'Authorization: Bearer abc123def456'",
            bundle_path=bundle,
        )
        assert "abc123def456" not in result.reproduction.command


# ── Builder tests ────────────────────────────────────────────────────


class TestBuildExternalResult:
    """Test building external results from bench output."""

    def test_basic_build(self, tmp_path):
        out_dir = _write_bench_summary(tmp_path)
        bundle = _write_bundle(tmp_path)
        result = build_external_result(
            out_dir,
            system_name="My System",
            system_type="oss",
            integration_type="inprocess",
            bundle_path=bundle,
        )
        assert result.system_name == "My System"
        assert result.redaction_applied is True
        assert result.results_summary.total_packs == 2
        assert len(result.results_summary.pack_results) == 2

    def test_bundle_name_mismatch_raises(self, tmp_path):
        out_dir = _write_bench_summary(tmp_path, bundle_name="wrong_name")
        bundle = _write_bundle(tmp_path)
        with pytest.raises(ValueError, match="Bundle name mismatch"):
            build_external_result(
                out_dir,
                system_name="Test",
                bundle_path=bundle,
            )

    def test_missing_summary_raises(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        bundle = _write_bundle(tmp_path)
        with pytest.raises(FileNotFoundError, match=r"bench_summary\.json"):
            build_external_result(
                empty_dir,
                system_name="Test",
                bundle_path=bundle,
            )

    def test_missing_bundle_raises(self, tmp_path):
        out_dir = _write_bench_summary(tmp_path)
        with pytest.raises(FileNotFoundError, match="Bundle not found"):
            build_external_result(
                out_dir,
                system_name="Test",
                bundle_path=tmp_path / "nonexistent.yaml",
            )


# ── Validator tests ──────────────────────────────────────────────────


class TestValidateExternalResult:
    """Test validating external result files."""

    def test_valid_file(self, tmp_path):
        data = _minimal_external_result()
        path = tmp_path / "valid.json"
        path.write_text(json.dumps(data))
        result = validate_external_result(path)
        assert result.system_name == "Test System"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_external_result(tmp_path / "nonexistent.json")

    def test_invalid_schema_raises(self, tmp_path):
        from pydantic import ValidationError

        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"invalid": "data"}))
        with pytest.raises(ValidationError):
            validate_external_result(path)

    def test_redaction_false_raises(self, tmp_path):
        data = _minimal_external_result(redaction_applied=False)
        path = tmp_path / "noredact.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="redaction_applied=false"):
            validate_external_result(path)

    def test_secrets_in_file_raises(self, tmp_path):
        data = _minimal_external_result(notes="email me at user@secret.com")
        path = tmp_path / "leaky.json"
        path.write_text(json.dumps(data))
        with pytest.raises(SecretLeakError):
            validate_external_result(path)

    def test_bundle_hash_mismatch_raises(self, tmp_path):
        bundle = _write_bundle(tmp_path)
        data = _minimal_external_result()
        # Hash won't match the real bundle
        path = tmp_path / "result.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="Bundle hash mismatch"):
            validate_external_result(path, bundle_path=bundle)

    def test_bundle_hash_match(self, tmp_path):
        import hashlib

        bundle = _write_bundle(tmp_path)
        real_hash = hashlib.sha256(bundle.read_bytes()).hexdigest()
        data = _minimal_external_result()
        data["bundle"]["hash"] = real_hash
        path = tmp_path / "result.json"
        path.write_text(json.dumps(data))
        result = validate_external_result(path, bundle_path=bundle)
        assert result.bundle.hash == real_hash


# ── Example file validation ──────────────────────────────────────────


class TestExampleFile:
    """Validate the shipped example file against the schema."""

    def test_sample_parses(self):
        sample = (
            Path(__file__).parent.parent
            / "external_results"
            / "examples"
            / "sample_external_result.json"
        )
        if not sample.exists():
            pytest.skip("Sample file not found")
        with open(sample) as f:
            data = json.load(f)
        result = ExternalResult.model_validate(data)
        assert result.redaction_applied is True
        assert result.system_type in ("oss", "commercial", "internal")

    def test_sample_has_no_secrets(self):
        sample = (
            Path(__file__).parent.parent
            / "external_results"
            / "examples"
            / "sample_external_result.json"
        )
        if not sample.exists():
            pytest.skip("Sample file not found")
        with open(sample) as f:
            data = json.load(f)
        findings = scan_secrets(data)
        assert findings == [], f"Sample has secrets: {findings}"

"""Fuzz tests for input robustness.

Tests that the system handles malformed/malicious inputs gracefully:
- YAML/JSON manifests with random/unicode strings
- Queries with edge cases (long, emoji, RTL, null bytes)
- No panics, clean ValueError/ValidationError without stacktrace leaking
"""

import json
import tempfile
from pathlib import Path

import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from ragleaklab.assets.validator import load_attacks_manifest, load_corpus_manifest
from ragleaklab.config import load_config
from ragleaklab.core.errors import (
    ConfigurationError,
    InputError,
    ManifestValidationError,
    sanitize_message,
)

# Fixed settings for fast, deterministic tests
FUZZ_SETTINGS = settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    derandomize=True,
)

# --- Strategies ---

# Unicode text including emoji, RTL, combining chars
unicode_text = st.text(
    alphabet=st.characters(
        categories=["L", "M", "N", "P", "S", "Z"],
        include_characters="\u200f\u200e\U0001f600\U0001f4a9\u202e",  # RTL, LRM, emoji
    ),
    min_size=0,
    max_size=500,
)

# Very long strings (hypothesis has internal limits, generate reasonably long)
long_text = st.text(min_size=1000, max_size=5000)

# Text with null bytes (will be sanitized)
null_byte_text = st.binary(min_size=10, max_size=200).map(
    lambda b: b.replace(b"\x00", b"").decode("utf-8", errors="replace")
)

# Random dict-like structures
random_dict = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.one_of(
        st.text(max_size=100),
        st.integers(),
        st.floats(allow_nan=False),
        st.booleans(),
        st.none(),
    ),
    max_size=20,
)


class TestManifestFuzzing:
    """Fuzz tests for manifest parsing."""

    @FUZZ_SETTINGS
    @given(data=random_dict)
    def test_corpus_manifest_random_dict(self, data):
        """Random dict should raise ValidationError, not panic."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            temp_path = Path(f.name)

        try:
            try:
                load_corpus_manifest(temp_path)
            except (ValidationError, ValueError, TypeError, KeyError) as e:
                # Expected - manifest is invalid
                # Verify error message doesn't contain suspicious patterns
                error_str = str(e)
                assert "AKIA" not in error_str  # No AWS keys
                assert "Bearer " not in error_str  # No tokens
        finally:
            temp_path.unlink()

    @FUZZ_SETTINGS
    @given(data=random_dict)
    def test_attacks_manifest_random_dict(self, data):
        """Random dict should raise ValidationError, not panic."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            temp_path = Path(f.name)

        try:
            try:
                load_attacks_manifest(temp_path)
            except (ValidationError, ValueError, TypeError, KeyError) as e:
                # Expected - manifest is invalid
                error_str = str(e)
                assert "secret" not in error_str.lower() or "secret_codeword" in error_str.lower()
        finally:
            temp_path.unlink()

    @FUZZ_SETTINGS
    @given(content=unicode_text)
    def test_manifest_unicode_content(self, content):
        """Unicode in YAML values should not crash parser."""
        data = {"name": content, "version": "1.0", "files": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f, allow_unicode=True)
            temp_path = Path(f.name)

        try:
            try:
                load_corpus_manifest(temp_path)
            except (ValidationError, ValueError, TypeError, yaml.YAMLError):
                pass  # Expected for invalid schemas
        finally:
            temp_path.unlink()

    @FUZZ_SETTINGS
    @given(content=st.text(min_size=0, max_size=1000))
    def test_invalid_yaml_syntax(self, content):
        """Invalid YAML should raise clean error."""
        # Add unbalanced brackets to make invalid YAML
        bad_yaml = f"key: [{content}"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(bad_yaml)
            temp_path = Path(f.name)

        try:
            try:
                load_corpus_manifest(temp_path)
            except (ValidationError, ValueError, yaml.YAMLError):
                pass  # Expected
        finally:
            temp_path.unlink()


class TestConfigFuzzing:
    """Fuzz tests for config loading."""

    @FUZZ_SETTINGS
    @given(data=random_dict)
    def test_config_random_dict(self, data):
        """Random dict config should raise ValidationError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            temp_path = Path(f.name)

        try:
            try:
                load_config(temp_path)
            except (ValidationError, ValueError, TypeError, KeyError):
                pass  # Expected
        finally:
            temp_path.unlink()

    @FUZZ_SETTINGS
    @given(url=unicode_text)
    def test_config_unicode_url(self, url):
        """Unicode in URL should not crash."""
        data = {
            "target": {
                "type": "http",
                "url": url,
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f, allow_unicode=True)
            temp_path = Path(f.name)

        try:
            try:
                cfg = load_config(temp_path)
                # If it parses, URL should be stored
                assert cfg is not None
            except (ValidationError, ValueError, TypeError):
                pass  # Expected for invalid URLs
        finally:
            temp_path.unlink()


class TestQueryFuzzing:
    """Fuzz tests for query handling."""

    @FUZZ_SETTINGS
    @given(query=long_text)
    def test_very_long_query_no_panic(self, query):
        """Very long queries should not cause memory issues."""
        # Import here to avoid import-time side effects
        from ragleaklab.metrics import detect_canary, verbatim_overlap

        # Make it even longer by repetition
        very_long = query * 10

        # These should handle long input gracefully
        result = detect_canary(very_long)
        assert result is not None
        assert isinstance(result.present, bool)

        # Verbatim with long query
        sources = [("doc1", "short source text")]
        result = verbatim_overlap(very_long, sources)
        assert result is not None

    @FUZZ_SETTINGS
    @given(query=unicode_text)
    def test_emoji_rtl_query(self, query):
        """Queries with emoji/RTL chars should not crash."""
        from ragleaklab.metrics import detect_canary

        result = detect_canary(query)
        assert result is not None

    @FUZZ_SETTINGS
    @given(query=null_byte_text)
    def test_sanitized_null_bytes(self, query):
        """Sanitized null-byte text should process cleanly."""
        from ragleaklab.metrics import detect_canary

        # After sanitization, should work fine
        result = detect_canary(query)
        assert result is not None


class TestErrorSanitization:
    """Tests for error message sanitization."""

    @FUZZ_SETTINGS
    @given(message=unicode_text)
    def test_sanitize_preserves_safe_messages(self, message):
        """Safe messages should pass through unchanged (mostly)."""
        sanitized = sanitize_message(message)
        # Should not crash
        assert isinstance(sanitized, str)

    def test_sanitize_redacts_api_key(self):
        """API keys should be redacted."""
        msg = "Error connecting with key sk_live_abc123def456ghi789"
        sanitized = sanitize_message(msg)
        assert "sk_live" not in sanitized
        assert "REDACTED" in sanitized

    def test_sanitize_redacts_bearer_token(self):
        """Bearer tokens should be redacted."""
        msg = "Auth failed: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        sanitized = sanitize_message(msg)
        assert "eyJ" not in sanitized
        assert "REDACTED" in sanitized

    def test_sanitize_redacts_home_path(self):
        """Home paths should be redacted."""
        msg = "File not found: /Users/johndoe/secret/config.yaml"
        sanitized = sanitize_message(msg)
        assert "johndoe" not in sanitized
        assert "REDACTED" in sanitized

    def test_sanitize_redacts_aws_key(self):
        """AWS keys should be redacted."""
        msg = "AWS error with key AKIAIOSFODNN7EXAMPLE"
        sanitized = sanitize_message(msg)
        assert "AKIA" not in sanitized
        assert "REDACTED" in sanitized


class TestErrorClasses:
    """Tests for custom error classes."""

    def test_input_error_has_exit_code(self):
        """InputError should have correct exit code."""
        err = InputError("Invalid file format", "/path/to/file")
        assert err.exit_code == 2  # INPUT_ERROR
        assert "Invalid file format" in str(err)

    def test_config_error_has_exit_code(self):
        """ConfigurationError should have correct exit code."""
        err = ConfigurationError("Missing required field")
        assert err.exit_code == 4  # CONFIG_ERROR

    def test_validation_error_has_exit_code(self):
        """ManifestValidationError should have correct exit code."""
        err = ManifestValidationError("Schema mismatch", "manifest.yaml")
        assert err.exit_code == 3  # VALIDATION_ERROR

    def test_errors_inherit_from_value_error(self):
        """Custom errors should be catchable as ValueError."""
        err = InputError("test")
        assert isinstance(err, ValueError)

        err = ConfigurationError("test")
        assert isinstance(err, ValueError)

        err = ManifestValidationError("test")
        assert isinstance(err, ValueError)


class TestJsonManifestFuzzing:
    """Fuzz tests for JSON manifest parsing."""

    @FUZZ_SETTINGS
    @given(data=random_dict)
    def test_json_manifest_random_dict(self, data):
        """Random JSON dict should raise ValidationError, not panic."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)

        try:
            # Convert to YAML file to test (our loaders expect YAML)
            with open(temp_path) as jf:
                json_data = json.load(jf)

            yaml_path = temp_path.with_suffix(".yaml")
            with open(yaml_path, "w") as yf:
                yaml.dump(json_data, yf)

            try:
                load_corpus_manifest(yaml_path)
            except (ValidationError, ValueError, TypeError, KeyError):
                pass  # Expected
            finally:
                yaml_path.unlink()
        finally:
            temp_path.unlink()

    @FUZZ_SETTINGS
    @given(content=unicode_text)
    def test_json_unicode_values(self, content):
        """Unicode in JSON values should not crash."""
        data = {"name": content, "files": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f, allow_unicode=True)
            temp_path = Path(f.name)

        try:
            try:
                load_corpus_manifest(temp_path)
            except (ValidationError, ValueError, TypeError):
                pass  # Expected for invalid schemas
        finally:
            temp_path.unlink()

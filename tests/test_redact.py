"""Tests for redaction module."""

from __future__ import annotations

from ragleaklab.core.redact import REDACTED, redact, redact_dict


class TestRedactText:
    """Tests for redact() function."""

    def test_redact_email(self) -> None:
        """Test email redaction."""
        text = "Contact: user@example.com for support"
        result = redact(text)
        assert "user@example.com" not in result
        assert REDACTED in result

    def test_redact_multiple_emails(self) -> None:
        """Test multiple emails redacted."""
        text = "From: a@b.com To: x@y.org CC: test@foo.co.uk"
        result = redact(text)
        assert "a@b.com" not in result
        assert "x@y.org" not in result
        assert "test@foo.co.uk" not in result
        assert result.count(REDACTED) == 3

    def test_redact_phone_us(self) -> None:
        """Test US phone number redaction."""
        text = "Call 555-123-4567 or (555) 987-6543"
        result = redact(text)
        assert "555-123-4567" not in result
        assert "(555) 987-6543" not in result

    def test_redact_phone_international(self) -> None:
        """Test international phone redaction."""
        text = "Phone: +14155551234"
        result = redact(text)
        assert "+14155551234" not in result

    def test_redact_canary_token(self) -> None:
        """Test canary token redaction."""
        text = "Leak detected CANARY_abcdef1234567890 in response"
        result = redact(text)
        assert "CANARY_abcdef1234567890" not in result
        assert REDACTED in result

    def test_redact_secret_pattern(self) -> None:
        """Test SECRET_ pattern redaction."""
        text = "Token: SECRET_API_KEY_123"
        result = redact(text)
        assert "SECRET_API_KEY_123" not in result
        assert REDACTED in result

    def test_redact_bearer_token(self) -> None:
        """Test Bearer token redaction."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = redact(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "Bearer" in result  # Keep Bearer prefix

    def test_redact_basic_auth(self) -> None:
        """Test Basic auth redaction."""
        text = "Auth: Basic dXNlcjpwYXNz"
        result = redact(text)
        assert "dXNlcjpwYXNz" not in result

    def test_redact_api_key(self) -> None:
        """Test API key pattern redaction."""
        text = "Key: sk_live_abc123def456ghi789jkl"
        result = redact(text)
        assert "sk_live_abc123def456ghi789jkl" not in result

    def test_redact_aws_key(self) -> None:
        """Test AWS access key redaction."""
        text = "AWS key: AKIAIOSFODNN7EXAMPLE"
        result = redact(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result

    def test_redact_preserves_normal_text(self) -> None:
        """Test that normal text is preserved."""
        text = "This is a normal message without secrets"
        result = redact(text)
        assert result == text

    def test_redact_empty_string(self) -> None:
        """Test empty string handling."""
        assert redact("") == ""

    def test_redact_none_handling(self) -> None:
        """Test that empty values pass through."""
        # Falsy values should return unchanged
        assert redact("") == ""


class TestRedactDict:
    """Tests for redact_dict() function."""

    def test_redact_dict_string_values(self) -> None:
        """Test string value redaction in dict."""
        data = {"email": "test@example.com", "name": "John"}
        result = redact_dict(data)
        assert "test@example.com" not in str(result)
        assert result["name"] == "John"

    def test_redact_dict_authorization_header(self) -> None:
        """Test Authorization header is fully redacted."""
        data = {
            "headers": {"Authorization": "Bearer secret123", "Content-Type": "application/json"}
        }
        result = redact_dict(data)
        assert result["headers"]["Authorization"] == REDACTED
        assert result["headers"]["Content-Type"] == "application/json"

    def test_redact_dict_sensitive_headers(self) -> None:
        """Test various sensitive headers are redacted."""
        data = {
            "headers": {
                "X-API-Key": "my-secret-key",
                "Cookie": "session=abc123",
                "x-auth-token": "token123",
            }
        }
        result = redact_dict(data)
        assert result["headers"]["X-API-Key"] == REDACTED
        assert result["headers"]["Cookie"] == REDACTED
        assert result["headers"]["x-auth-token"] == REDACTED

    def test_redact_dict_nested(self) -> None:
        """Test nested structure redaction."""
        data = {
            "request": {
                "headers": {"Authorization": "Bearer xyz"},
                "body": {"email": "user@test.com"},
            }
        }
        result = redact_dict(data)
        assert result["request"]["headers"]["Authorization"] == REDACTED
        assert "user@test.com" not in str(result)

    def test_redact_dict_list(self) -> None:
        """Test list redaction."""
        data = {"emails": ["a@b.com", "x@y.net"]}
        result = redact_dict(data)
        assert REDACTED in result["emails"]
        assert len(result["emails"]) == 2

    def test_redact_dict_primitives(self) -> None:
        """Test primitive values pass through."""
        data = {"count": 42, "enabled": True, "ratio": 0.5, "empty": None}
        result = redact_dict(data)
        assert result["count"] == 42
        assert result["enabled"] is True
        assert result["ratio"] == 0.5
        assert result["empty"] is None

    def test_redact_dict_preserves_structure(self) -> None:
        """Test original dict is not mutated."""
        original = {"secret": "test@email.com", "data": {"key": "value"}}
        result = redact_dict(original)
        # Original should be unchanged
        assert original["secret"] == "test@email.com"
        # Result should be redacted
        assert "test@email.com" not in str(result)

    def test_redact_dict_report_structure(self) -> None:
        """Test redaction on report-like structure."""
        data = {
            "test_id": "case-001",
            "query": "What is the email for CANARY_abc123def4567890?",
            "answer": "The email is user@company.com",
            "headers": {"Authorization": "Bearer token123"},
            "meta": {"api_key": "sk_live_abcdefghijklmnop"},
        }
        result = redact_dict(data)
        # Check redaction applied
        assert "CANARY_abc123def4567890" not in str(result)
        assert "user@company.com" not in str(result)
        assert result["headers"]["Authorization"] == REDACTED
        # test_id preserved
        assert result["test_id"] == "case-001"

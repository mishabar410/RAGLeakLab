"""SSRF protection tests for HttpTarget.

Tests that HttpTarget correctly validates URLs to prevent Server-Side
Request Forgery attacks by blocking private IPs, invalid schemes, and
respecting domain allowlists.
"""

import socket
from unittest.mock import patch

import pytest
import responses

from ragleaklab.targets import HttpTarget, SSRFValidationError


class TestSSRFPrivateIPBlocking:
    """Tests for blocking private/internal IP ranges."""

    def test_blocks_localhost_127(self):
        """127.0.0.1 (loopback) should be blocked."""
        with patch.object(
            socket, "gethostbyname_ex", return_value=("localhost", [], ["127.0.0.1"])
        ):
            with pytest.raises(SSRFValidationError, match="private/internal IP"):
                HttpTarget(url="http://localhost:8000/api")

    def test_blocks_localhost_ip_direct(self):
        """Direct 127.x.x.x IPs should be blocked."""
        with patch.object(
            socket, "gethostbyname_ex", return_value=("127.0.0.1", [], ["127.0.0.1"])
        ):
            with pytest.raises(SSRFValidationError, match="private/internal IP"):
                HttpTarget(url="http://127.0.0.1:8000/api")

    def test_blocks_private_10_range(self):
        """10.0.0.0/8 private range should be blocked."""
        with patch.object(socket, "gethostbyname_ex", return_value=("internal", [], ["10.0.0.1"])):
            with pytest.raises(SSRFValidationError, match="private/internal IP"):
                HttpTarget(url="http://internal.corp:8000/api")

    def test_blocks_private_172_range(self):
        """172.16.0.0/12 private range should be blocked."""
        with patch.object(
            socket, "gethostbyname_ex", return_value=("internal", [], ["172.16.0.1"])
        ):
            with pytest.raises(SSRFValidationError, match="private/internal IP"):
                HttpTarget(url="http://internal.corp:8000/api")

    def test_blocks_private_192_range(self):
        """192.168.0.0/16 private range should be blocked."""
        with patch.object(
            socket, "gethostbyname_ex", return_value=("internal", [], ["192.168.1.1"])
        ):
            with pytest.raises(SSRFValidationError, match="private/internal IP"):
                HttpTarget(url="http://internal.corp:8000/api")

    def test_blocks_link_local(self):
        """169.254.0.0/16 link-local range should be blocked."""
        with patch.object(socket, "gethostbyname_ex", return_value=("local", [], ["169.254.1.1"])):
            with pytest.raises(SSRFValidationError, match="private/internal IP"):
                HttpTarget(url="http://local.machine:8000/api")


class TestSSRFSchemeValidation:
    """Tests for URL scheme validation."""

    def test_blocks_file_scheme(self):
        """file:// scheme should be blocked."""
        with pytest.raises(SSRFValidationError, match="Only http/https allowed"):
            HttpTarget(url="file:///etc/passwd")

    def test_blocks_gopher_scheme(self):
        """gopher:// scheme should be blocked."""
        with pytest.raises(SSRFValidationError, match="Only http/https allowed"):
            HttpTarget(url="gopher://evil.server:70/")

    def test_blocks_ftp_scheme(self):
        """ftp:// scheme should be blocked."""
        with pytest.raises(SSRFValidationError, match="Only http/https allowed"):
            HttpTarget(url="ftp://evil.server/file")

    def test_blocks_data_scheme(self):
        """data: scheme should be blocked."""
        with pytest.raises(SSRFValidationError, match="Only http/https allowed"):
            HttpTarget(url="data:text/html,<script>evil</script>")

    @responses.activate
    def test_allows_http_scheme(self):
        """http:// scheme should be allowed."""
        responses.add(responses.POST, "http://example.com/api", json={"answer": "ok"})
        with patch.object(
            socket, "gethostbyname_ex", return_value=("example.com", [], ["93.184.216.34"])
        ):
            target = HttpTarget(url="http://example.com/api")
            assert target.url == "http://example.com/api"

    @responses.activate
    def test_allows_https_scheme(self):
        """https:// scheme should be allowed."""
        responses.add(responses.POST, "https://example.com/api", json={"answer": "ok"})
        with patch.object(
            socket, "gethostbyname_ex", return_value=("example.com", [], ["93.184.216.34"])
        ):
            target = HttpTarget(url="https://example.com/api")
            assert target.url == "https://example.com/api"


class TestSSRFDomainAllowlist:
    """Tests for domain allowlist functionality."""

    def test_allowlist_permits_listed_domain(self):
        """Domain in allowlist should be permitted."""
        with patch.object(
            socket,
            "gethostbyname_ex",
            return_value=("api.example.com", [], ["93.184.216.34"]),
        ):
            target = HttpTarget(
                url="https://api.example.com/rag",
                allowed_domains=["api.example.com"],
            )
            assert target.url == "https://api.example.com/rag"

    def test_allowlist_blocks_unlisted_domain(self):
        """Domain not in allowlist should be blocked."""
        with pytest.raises(SSRFValidationError, match="not in allowed domains"):
            HttpTarget(
                url="https://evil.com/api",
                allowed_domains=["api.example.com", "safe.example.org"],
            )

    def test_allowlist_case_insensitive(self):
        """Allowlist matching should be case-insensitive."""
        with patch.object(
            socket,
            "gethostbyname_ex",
            return_value=("API.EXAMPLE.COM", [], ["93.184.216.34"]),
        ):
            target = HttpTarget(
                url="https://API.EXAMPLE.COM/rag",
                allowed_domains=["api.example.com"],
            )
            assert target.url == "https://API.EXAMPLE.COM/rag"

    def test_no_allowlist_allows_any_public_domain(self):
        """Without allowlist, any public domain should be allowed."""
        with patch.object(
            socket,
            "gethostbyname_ex",
            return_value=("any-public-server.com", [], ["203.0.113.42"]),
        ):
            target = HttpTarget(url="https://any-public-server.com/api")
            assert target.url == "https://any-public-server.com/api"


class TestSSRFTimeoutPropagation:
    """Tests for timeout configuration."""

    def test_default_timeout_30s(self):
        """Default timeout should be 30 seconds."""
        with patch.object(
            socket, "gethostbyname_ex", return_value=("example.com", [], ["93.184.216.34"])
        ):
            target = HttpTarget(url="http://example.com/api")
            assert target.timeout == 30.0

    def test_custom_timeout_propagated(self):
        """Custom timeout should be stored correctly."""
        with patch.object(
            socket, "gethostbyname_ex", return_value=("example.com", [], ["93.184.216.34"])
        ):
            target = HttpTarget(url="http://example.com/api", timeout=5.0)
            assert target.timeout == 5.0

    @responses.activate
    def test_timeout_used_in_request(self):
        """Timeout should be passed to requests library."""
        responses.add(responses.POST, "http://example.com/api", json={"answer": "ok"})
        with patch.object(
            socket, "gethostbyname_ex", return_value=("example.com", [], ["93.184.216.34"])
        ):
            target = HttpTarget(url="http://example.com/api", timeout=15.0)
            target.ask("test query")

        # Verify timeout was passed to requests
        assert responses.calls[0].request.req_kwargs.get("timeout") == 15.0


class TestSSRFEdgeCases:
    """Edge cases and additional validation tests."""

    def test_empty_hostname_rejected(self):
        """URL without hostname should be rejected."""
        with pytest.raises(SSRFValidationError, match="must have a hostname"):
            HttpTarget(url="http:///path/only")

    def test_dns_failure_allowed(self):
        """DNS resolution failure should not block (will fail at request time)."""
        with patch.object(socket, "gethostbyname_ex", side_effect=socket.gaierror("DNS failed")):
            # Should not raise - let requests handle the failure
            target = HttpTarget(url="http://nonexistent.invalid/api")
            assert target.url == "http://nonexistent.invalid/api"

    def test_multiple_ips_all_checked(self):
        """If any resolved IP is private, request should be blocked."""
        with patch.object(
            socket,
            "gethostbyname_ex",
            return_value=("multi.ip", [], ["8.8.8.8", "10.0.0.1"]),
        ):
            with pytest.raises(SSRFValidationError, match="private/internal IP"):
                HttpTarget(url="http://multi.ip/api")

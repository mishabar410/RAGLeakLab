"""Tests for HTTP target safe defaults."""

import pytest

from ragleaklab.targets.http import AllowlistRequiredError, HttpTarget
from ragleaklab.targets.ssrf import SSRFValidationError


class TestHttpTargetSafeDefaults:
    """Tests for HTTP target security defaults."""

    def test_allowlist_required_by_default(self):
        """Test that HTTP target raises error without allowlist."""
        with pytest.raises(AllowlistRequiredError) as exc:
            HttpTarget(
                url="https://api.example.com/ask",
                # No allowed_domains set
            )
        assert "requires explicit allowed_domains" in str(exc.value)

    def test_allowlist_with_domains_works(self):
        """Test that HTTP target works with allowed_domains set."""
        target = HttpTarget(
            url="https://api.example.com/ask",
            allowed_domains=["api.example.com"],
        )
        assert target.url == "https://api.example.com/ask"

    def test_require_allowlist_false_allows_any(self):
        """Test that require_allowlist=False disables domain checking."""
        target = HttpTarget(
            url="https://any-service.com/ask",
            require_allowlist=False,
        )
        assert target.url == "https://any-service.com/ask"

    def test_localhost_blocked_by_default(self):
        """Test that localhost is blocked by default."""
        with pytest.raises(SSRFValidationError) as exc:
            HttpTarget(
                url="http://localhost:8000/ask",
                require_allowlist=False,
            )
        assert "Localhost URLs blocked" in str(exc.value)

    def test_localhost_allowed_with_flag(self):
        """Test that localhost works with allow_localhost=True."""
        target = HttpTarget(
            url="http://localhost:8000/ask",
            allowed_domains=["localhost"],
            allow_localhost=True,
            require_allowlist=False,
        )
        assert target.url == "http://localhost:8000/ask"

    def test_127_0_0_1_blocked_by_default(self):
        """Test that 127.0.0.1 is blocked by default."""
        with pytest.raises(SSRFValidationError) as exc:
            HttpTarget(
                url="http://127.0.0.1:8000/ask",
                require_allowlist=False,
            )
        assert "Localhost URLs blocked" in str(exc.value)

    def test_ipv6_localhost_blocked(self):
        """Test that ::1 is blocked by default."""
        with pytest.raises(SSRFValidationError) as exc:
            HttpTarget(
                url="http://[::1]:8000/ask",
                require_allowlist=False,
            )
        assert "Localhost URLs blocked" in str(exc.value)

    def test_default_max_rps(self):
        """Test that default max_rps is 1.0."""
        target = HttpTarget(
            url="https://api.example.com/ask",
            allowed_domains=["api.example.com"],
        )
        assert target.max_rps == 1.0

    def test_custom_max_rps(self):
        """Test that max_rps can be customized."""
        target = HttpTarget(
            url="https://api.example.com/ask",
            allowed_domains=["api.example.com"],
            max_rps=5.0,
        )
        assert target.max_rps == 5.0


class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_rate_limit_sleeps(self, monkeypatch):
        """Test that rate limiting sleeps between requests."""
        sleep_times = []

        def mock_sleep(seconds):
            sleep_times.append(seconds)

        monkeypatch.setattr("time.sleep", mock_sleep)

        # Create target with 10 rps (0.1s between requests)
        target = HttpTarget(
            url="https://api.example.com/ask",
            allowed_domains=["api.example.com"],
            max_rps=10.0,
        )

        # Simulate rapid successive calls
        target._last_request_time = 0  # Force immediate next request trigger

        monkeypatch.setattr("time.monotonic", lambda: 0.05)  # Only 0.05s elapsed
        target._rate_limit()

        # Should have slept for approximately 0.05s (0.1 - 0.05)
        assert len(sleep_times) == 1
        assert 0.04 < sleep_times[0] < 0.06

    def test_rate_limit_no_sleep_when_enough_time(self, monkeypatch):
        """Test rate limiting doesn't sleep when interval already passed."""
        sleep_times = []

        def mock_sleep(seconds):
            sleep_times.append(seconds)

        monkeypatch.setattr("time.sleep", mock_sleep)

        target = HttpTarget(
            url="https://api.example.com/ask",
            allowed_domains=["api.example.com"],
            max_rps=10.0,  # 0.1s interval
        )

        # Simulate enough time has passed
        target._last_request_time = 0
        monkeypatch.setattr("time.monotonic", lambda: 1.0)  # 1s elapsed
        target._rate_limit()

        # Should not have slept
        assert len(sleep_times) == 0

    def test_rate_limit_disabled_when_zero(self, monkeypatch):
        """Test rate limiting is disabled when max_rps=0."""
        sleep_times = []

        def mock_sleep(seconds):
            sleep_times.append(seconds)

        monkeypatch.setattr("time.sleep", mock_sleep)

        target = HttpTarget(
            url="https://api.example.com/ask",
            allowed_domains=["api.example.com"],
            max_rps=0,  # Disabled
        )

        target._last_request_time = 0
        monkeypatch.setattr("time.monotonic", lambda: 0.001)
        target._rate_limit()

        # Should not have slept
        assert len(sleep_times) == 0


class TestConfigIntegration:
    """Tests for config integration."""

    def test_from_config_with_safe_defaults(self):
        """Test that from_config passes safe default settings."""
        from ragleaklab.config import HttpTargetConfig

        config = HttpTargetConfig(
            url="https://api.example.com/ask",
            allowed_domains=["api.example.com"],
        )

        target = HttpTarget.from_config(config)
        assert target.require_allowlist is True
        assert target.allow_localhost is False
        assert target.max_rps == 1.0

    def test_from_config_without_allowlist_raises(self):
        """Test that from_config raises when allowlist is missing."""
        from ragleaklab.config import HttpTargetConfig

        config = HttpTargetConfig(
            url="https://api.example.com/ask",
            # No allowed_domains
        )

        with pytest.raises(AllowlistRequiredError):
            HttpTarget.from_config(config)

    def test_from_config_with_require_allowlist_false(self):
        """Test from_config with require_allowlist=False."""
        from ragleaklab.config import HttpTargetConfig

        config = HttpTargetConfig(
            url="https://api.example.com/ask",
            require_allowlist=False,
        )

        target = HttpTarget.from_config(config)
        assert target.require_allowlist is False

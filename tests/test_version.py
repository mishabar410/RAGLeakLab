"""Tests for core/version.py."""

from ragleaklab.core.version import compute_config_hash, get_tool_version


class TestGetToolVersion:
    """Tests for get_tool_version."""

    def test_returns_string(self):
        result = get_tool_version()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_dev_or_version(self):
        result = get_tool_version()
        # Should be either 'dev' or a version string like '0.1.0'
        assert result == "dev" or "." in result


class TestComputeConfigHash:
    """Tests for compute_config_hash."""

    def test_deterministic(self):
        h1 = compute_config_hash(a="1", b="2")
        h2 = compute_config_hash(a="1", b="2")
        assert h1 == h2

    def test_different_args_different_hash(self):
        h1 = compute_config_hash(a="1")
        h2 = compute_config_hash(a="2")
        assert h1 != h2

    def test_order_independent(self):
        h1 = compute_config_hash(a="1", b="2")
        h2 = compute_config_hash(b="2", a="1")
        assert h1 == h2

    def test_returns_12_char_hex(self):
        h = compute_config_hash(x="y")
        assert len(h) == 12
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_args(self):
        h = compute_config_hash()
        assert isinstance(h, str)
        assert len(h) == 12

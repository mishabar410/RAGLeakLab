"""Tests for plugin entry points loading."""

from unittest.mock import MagicMock

import pytest

from ragleaklab.core.plugins import clear, get, list_plugins, load_entry_points


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear registry before and after each test."""
    clear()
    yield
    clear()


class FakeEntryPoint:
    """Fake entry point for testing."""

    def __init__(self, name: str, value: str, obj: object):
        self.name = name
        self.value = value
        self._obj = obj

    def load(self):
        return self._obj


class TestLoadEntryPoints:
    """Tests for load_entry_points function."""

    def test_loads_metrics_entry_points(self, monkeypatch):
        """Load metrics from entry points."""

        def fake_metric():
            return "from_entrypoint"

        fake_eps = [FakeEntryPoint("external_metric", "ext_pkg:fake_metric", fake_metric)]

        # Mock entry_points to return our fakes
        def mock_entry_points(group=None):
            if group == "ragleaklab.metrics":
                return fake_eps
            return []

        monkeypatch.setattr("ragleaklab.core.plugins.entry_points", mock_entry_points)

        load_entry_points("metrics")

        assert "external_metric" in list_plugins("metrics")
        assert get("metrics", "external_metric")() == "from_entrypoint"

    def test_loads_attacks_entry_points(self, monkeypatch):
        """Load attacks from entry points."""

        class FakeAttack:
            name = "ext_attack"

        fake_eps = [FakeEntryPoint("ext_attack", "ext_pkg:FakeAttack", FakeAttack)]

        def mock_entry_points(group=None):
            if group == "ragleaklab.attacks":
                return fake_eps
            return []

        monkeypatch.setattr("ragleaklab.core.plugins.entry_points", mock_entry_points)

        load_entry_points("attacks")

        assert "ext_attack" in list_plugins("attacks")
        assert get("attacks", "ext_attack") is FakeAttack

    def test_loads_targets_entry_points(self, monkeypatch):
        """Load targets from entry points."""

        class FakeTarget:
            pass

        fake_eps = [FakeEntryPoint("ext_target", "ext_pkg:FakeTarget", FakeTarget)]

        def mock_entry_points(group=None):
            if group == "ragleaklab.targets":
                return fake_eps
            return []

        monkeypatch.setattr("ragleaklab.core.plugins.entry_points", mock_entry_points)

        load_entry_points("targets")

        assert "ext_target" in list_plugins("targets")

    def test_empty_entry_points(self, monkeypatch):
        """No entry points is fine."""

        def mock_entry_points(group=None):
            return []

        monkeypatch.setattr("ragleaklab.core.plugins.entry_points", mock_entry_points)

        # Should not raise
        load_entry_points("metrics")
        assert list_plugins("metrics") == []

    def test_failed_entry_point_logs_warning(self, monkeypatch, caplog):
        """Failed entry point load logs warning but continues."""

        def broken_load():
            raise ImportError("Package not found")

        bad_ep = MagicMock()
        bad_ep.name = "broken"
        bad_ep.value = "bad_pkg:broken"
        bad_ep.load = broken_load

        def mock_entry_points(group=None):
            if group == "ragleaklab.metrics":
                return [bad_ep]
            return []

        monkeypatch.setattr("ragleaklab.core.plugins.entry_points", mock_entry_points)

        load_entry_points("metrics")

        assert "broken" not in list_plugins("metrics")
        assert "Failed to load" in caplog.text

    def test_python39_fallback(self, monkeypatch):
        """Test Python 3.9 fallback for entry_points API."""

        def fake_metric():
            return "legacy_api"

        fake_eps = [FakeEntryPoint("legacy_metric", "pkg:metric", fake_metric)]

        # Simulate Python 3.9 API (TypeError when using group kwarg)
        call_count = 0

        def mock_entry_points(group=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and group is not None:
                raise TypeError("entry_points() got an unexpected keyword argument 'group'")
            # Return dict-like for fallback
            return {"ragleaklab.metrics": fake_eps}

        monkeypatch.setattr("ragleaklab.core.plugins.entry_points", mock_entry_points)

        load_entry_points("metrics")

        assert "legacy_metric" in list_plugins("metrics")

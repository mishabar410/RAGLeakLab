"""Tests for plugin registry - manual registration."""

import pytest

from ragleaklab.core.plugins import (
    PLUGIN_KINDS,
    PluginError,
    clear,
    get,
    list_plugins,
    register,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear registry before and after each test."""
    clear()
    yield
    clear()


class TestRegister:
    """Tests for register function."""

    def test_register_metric(self):
        """Register a metric plugin."""

        def my_metric(text: str) -> float:
            return 0.5

        register("metrics", "test_metric", my_metric)
        assert "test_metric" in list_plugins("metrics")

    def test_register_attack(self):
        """Register an attack plugin."""

        class MyAttack:
            name = "test_attack"

        register("attacks", "test_attack", MyAttack)
        assert "test_attack" in list_plugins("attacks")

    def test_register_target(self):
        """Register a target plugin."""

        class MyTarget:
            pass

        register("targets", "test_target", MyTarget)
        assert "test_target" in list_plugins("targets")

    def test_register_invalid_kind(self):
        """Invalid kind raises PluginError."""
        with pytest.raises(PluginError, match="Invalid plugin kind"):
            register("invalid", "name", lambda: None)

    def test_register_overwrites_with_warning(self, caplog):
        """Registering same name overwrites with warning."""

        def v1():
            return 1

        def v2():
            return 2

        register("metrics", "dup", v1)
        register("metrics", "dup", v2)

        assert get("metrics", "dup")() == 2
        assert "already registered" in caplog.text


class TestGet:
    """Tests for get function."""

    def test_get_registered(self):
        """Get a registered plugin."""

        def fn():
            return 42

        register("metrics", "answer", fn)
        result = get("metrics", "answer")
        assert result() == 42

    def test_get_not_found(self):
        """Get non-existent plugin raises PluginError."""
        with pytest.raises(PluginError, match="not found"):
            get("metrics", "nonexistent")

    def test_get_invalid_kind(self):
        """Get with invalid kind raises PluginError."""
        with pytest.raises(PluginError, match="Invalid plugin kind"):
            get("invalid", "name")


class TestListPlugins:
    """Tests for list_plugins function."""

    def test_list_empty(self):
        """List empty registry."""
        assert list_plugins("metrics") == []

    def test_list_multiple(self):
        """List multiple plugins."""
        register("metrics", "a", lambda: 1)
        register("metrics", "b", lambda: 2)
        register("metrics", "c", lambda: 3)

        result = list_plugins("metrics")
        assert sorted(result) == ["a", "b", "c"]

    def test_list_invalid_kind(self):
        """List with invalid kind raises PluginError."""
        with pytest.raises(PluginError, match="Invalid plugin kind"):
            list_plugins("invalid")


class TestPluginKinds:
    """Tests for plugin kinds constant."""

    def test_all_kinds_exist(self):
        """All expected kinds are defined."""
        assert "metrics" in PLUGIN_KINDS
        assert "attacks" in PLUGIN_KINDS
        assert "targets" in PLUGIN_KINDS

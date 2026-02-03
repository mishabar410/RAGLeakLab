"""Plugin registry for extensibility.

Provides a simple registry for metrics, attacks, and targets that can be
extended via:
1. Manual registration: register(kind, name, obj)
2. Entry points: [project.entry-points."ragleaklab.metrics"]
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

logger = logging.getLogger(__name__)

# Supported plugin kinds
PLUGIN_KINDS = ("metrics", "attacks", "targets")

# Internal registry: {kind: {name: obj}}
_registry: dict[str, dict[str, Any]] = {kind: {} for kind in PLUGIN_KINDS}


class PluginError(Exception):
    """Plugin registry error."""


def register(kind: str, name: str, obj: Callable | type) -> None:
    """Register a plugin.

    Args:
        kind: Plugin type - "metrics", "attacks", or "targets"
        name: Unique name for the plugin
        obj: Callable or class implementing the plugin

    Raises:
        PluginError: If kind is invalid or name already registered
    """
    if kind not in PLUGIN_KINDS:
        raise PluginError(f"Invalid plugin kind: {kind}. Must be one of {PLUGIN_KINDS}")

    if name in _registry[kind]:
        logger.warning("Plugin %s/%s already registered, overwriting", kind, name)

    _registry[kind][name] = obj
    logger.debug("Registered plugin: %s/%s", kind, name)


def get(kind: str, name: str) -> Any:
    """Get a registered plugin.

    Args:
        kind: Plugin type
        name: Plugin name

    Returns:
        The registered plugin object

    Raises:
        PluginError: If kind is invalid or plugin not found
    """
    if kind not in PLUGIN_KINDS:
        raise PluginError(f"Invalid plugin kind: {kind}")

    if name not in _registry[kind]:
        available = list_plugins(kind)
        raise PluginError(f"Plugin {kind}/{name} not found. Available: {available}")

    return _registry[kind][name]


def list_plugins(kind: str) -> list[str]:
    """List registered plugins of a kind.

    Args:
        kind: Plugin type

    Returns:
        List of registered plugin names

    Raises:
        PluginError: If kind is invalid
    """
    if kind not in PLUGIN_KINDS:
        raise PluginError(f"Invalid plugin kind: {kind}")

    return list(_registry[kind].keys())


def load_entry_points(kind: str) -> None:
    """Load plugins from entry points.

    Looks for entry points in group "ragleaklab.{kind}".

    Args:
        kind: Plugin type to load

    Raises:
        PluginError: If kind is invalid
    """
    if kind not in PLUGIN_KINDS:
        raise PluginError(f"Invalid plugin kind: {kind}")

    group = f"ragleaklab.{kind}"

    try:
        # Python 3.10+ API
        eps = entry_points(group=group)
    except TypeError:
        # Python 3.9 fallback
        all_eps = entry_points()
        eps = all_eps.get(group, [])

    for ep in eps:
        try:
            obj = ep.load()
            register(kind, ep.name, obj)
            logger.info("Loaded entry point: %s/%s from %s", kind, ep.name, ep.value)
        except Exception as e:
            logger.warning("Failed to load entry point %s/%s: %s", kind, ep.name, e)


def load_all_entry_points() -> None:
    """Load entry points for all plugin kinds."""
    for kind in PLUGIN_KINDS:
        load_entry_points(kind)


def clear(kind: str | None = None) -> None:
    """Clear registry (mainly for testing).

    Args:
        kind: If provided, clear only this kind. Otherwise clear all.
    """
    if kind is None:
        for k in PLUGIN_KINDS:
            _registry[k].clear()
    elif kind in PLUGIN_KINDS:
        _registry[kind].clear()

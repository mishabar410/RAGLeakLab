"""Config loader with friendly error messages and env-var interpolation."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from ragleaklab.config.schema import ConfigRoot


class ConfigError(Exception):
    """User-facing configuration error with context."""

    def __init__(
        self,
        message: str,
        *,
        field_path: str | None = None,
        hint: str | None = None,
    ) -> None:
        self.field_path = field_path
        self.hint = hint
        parts = []
        if field_path:
            parts.append(f"  Field: {field_path}")
        parts.append(f"  Error: {message}")
        if hint:
            parts.append(f"  Hint:  {hint}")
        super().__init__("\n".join(parts))


# ── env-var interpolation ────────────────────────────────────────────

_ENV_PATTERN = re.compile(r"\$\{(?:ENV:)?(\w+)\}")


def _substitute_env_vars(text: str) -> str:
    """Replace ``${VAR}`` and ``${ENV:VAR}`` with environment variable values.

    Missing variables resolve to empty string (logged, not fatal).
    """

    def _replacer(match: re.Match) -> str:
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            return ""
        return value

    return _ENV_PATTERN.sub(_replacer, text)


def _substitute_in_dict(data: dict | list | str) -> dict | list | str:
    """Recursively substitute env vars in nested data."""
    if isinstance(data, dict):
        return {k: _substitute_in_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_substitute_in_dict(item) for item in data]
    elif isinstance(data, str):
        return _substitute_env_vars(data)
    return data


# ── error formatting ────────────────────────────────────────────────

_FIELD_HINTS: dict[str, str] = {
    "target.type": "Use 'inprocess', 'http', or 'mock'.",
    "target.url": "Example: https://rag.example.com/ask",
    "target.method": "Typically 'POST' or 'GET'.",
    "target.timeout_sec": "Positive number, e.g. 30.0",
    "target.max_rps": "Positive number, e.g. 1.0",
    "corpus.path": "Example: data/corpus_private_canary",
    "attacks.path": "Example: data/attacks",
    "output.formats": "Valid values: json, sarif, junit, md",
    "run.jobs": "Positive integer, e.g. 4",
    "thresholds.verbatim_delta": "Float between 0.0 and 1.0, e.g. 0.01",
    "thresholds.membership_delta": "Float between 0.0 and 1.0, e.g. 0.05",
}


def format_validation_error(err: ValidationError) -> str:
    """Convert a Pydantic ``ValidationError`` into a human-readable message.

    Each error gets a field path, description, and optional hint.
    """
    lines: list[str] = ["❌ Config validation failed:\n"]

    for i, e in enumerate(err.errors(), start=1):
        loc_parts = [str(p) for p in e.get("loc", ())]
        field_path = ".".join(loc_parts) if loc_parts else "(root)"
        msg = e.get("msg", "unknown error")

        lines.append(f"  {i}. Field: {field_path}")
        lines.append(f"     Error: {msg}")

        # Check for field-specific hint
        hint = _FIELD_HINTS.get(field_path)
        if hint:
            lines.append(f"     Hint:  {hint}")

        # Type-specific guidance
        err_type = e.get("type", "")
        if err_type == "missing":
            lines.append(f"     Hint:  Add '{loc_parts[-1]}:' to your config file.")
        elif err_type == "extra_forbidden":
            lines.append(f"     Hint:  '{loc_parts[-1]}' is not a valid field. Remove it.")
        elif "literal" in err_type:
            ctx = e.get("ctx", {})
            expected = ctx.get("expected", "")
            if expected:
                lines.append(f"     Hint:  Allowed values: {expected}")

        lines.append("")

    return "\n".join(lines)


# ── loader ───────────────────────────────────────────────────────────


def load_config(path: Path | str) -> ConfigRoot:
    """Load and validate a YAML configuration file.

    Args:
        path: Path to the YAML config file.

    Returns:
        Validated ``ConfigRoot``.

    Raises:
        ConfigError: On file-system errors or YAML syntax errors.
        SystemExit (via re-raise): Never — all errors are wrapped.
    """
    path = Path(path)

    # ── file checks ──────────────────────────────────────────────
    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}",
            hint="Check the path or create the file. See docs/CONFIG.md for reference.",
        )

    if not path.is_file():
        raise ConfigError(
            f"Config path is not a file: {path}",
            hint="Provide a .yaml file, not a directory.",
        )

    # ── YAML parse ───────────────────────────────────────────────
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file: {exc}") from exc

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"Invalid YAML syntax: {exc}",
            hint="Check indentation and special characters.",
        ) from exc

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ConfigError(
            f"Config must be a YAML mapping (dict), got {type(data).__name__}.",
            hint="The top-level structure should be key: value pairs.",
        )

    # ── env-var interpolation ────────────────────────────────────
    data = _substitute_in_dict(data)

    # ── pydantic validation ──────────────────────────────────────
    try:
        return ConfigRoot.model_validate(data)
    except ValidationError as exc:
        friendly = format_validation_error(exc)
        raise ConfigError(friendly) from exc

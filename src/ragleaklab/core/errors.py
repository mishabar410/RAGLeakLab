"""Unified error handling for RAGLeakLab CLI.

Provides:
- Consistent exit codes
- Safe error messages without secret leakage
- Structured error formatting
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


class ExitCode(IntEnum):
    """Standard exit codes for CLI commands."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    INPUT_ERROR = 2  # Invalid input files, missing args
    VALIDATION_ERROR = 3  # Schema validation failures
    CONFIG_ERROR = 4  # Configuration issues
    NETWORK_ERROR = 5  # HTTP target unreachable
    INTERNAL_ERROR = 99  # Unexpected internal errors


# Patterns that may leak sensitive information
_SENSITIVE_PATTERNS = [
    # Environment variables in error messages
    re.compile(r"\$\{?\w*(?:KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|AUTH)\w*\}?", re.IGNORECASE),
    # API keys (common formats: sk_live_, pk_test_, api_key, etc)
    re.compile(r"(?:sk|pk)_(?:live|test)_[a-zA-Z0-9]+", re.IGNORECASE),
    re.compile(r"(?:api|key|token)[_-]?[a-zA-Z0-9]{20,}", re.IGNORECASE),
    # Bearer tokens
    re.compile(r"Bearer\s+[A-Za-z0-9\-_.~+/]+=*", re.IGNORECASE),
    # Basic auth
    re.compile(r"Basic\s+[A-Za-z0-9+/]+=*", re.IGNORECASE),
    # File paths with home directory
    re.compile(r"/(?:home|Users)/\w+/"),
    # AWS-style keys
    re.compile(r"AKIA[0-9A-Z]{16}"),
]

# Environment variable names that should never appear in errors
_SENSITIVE_ENV_VARS = {
    "API_KEY",
    "SECRET_KEY",
    "PASSWORD",
    "TOKEN",
    "CREDENTIAL",
    "AUTH",
    "PRIVATE",
}


@dataclass(frozen=True)
class SafeError:
    """Error with sanitized message for external display."""

    code: ExitCode
    message: str
    details: str | None = None

    def format(self, verbose: bool = False) -> str:
        """Format error for display.

        Args:
            verbose: If True, include details.

        Returns:
            Formatted error message.
        """
        if verbose and self.details:
            return f"[{self.code.name}] {self.message}\n  Details: {self.details}"
        return f"[{self.code.name}] {self.message}"


def sanitize_message(message: str) -> str:
    """Remove sensitive information from error message.

    Redacts:
    - Environment variable values
    - API keys and tokens
    - Home directory paths
    - Other credential patterns

    Args:
        message: Raw error message.

    Returns:
        Sanitized message safe for display.
    """
    result = message

    # Apply pattern-based redaction
    for pattern in _SENSITIVE_PATTERNS:
        result = pattern.sub("[REDACTED]", result)

    # Check for env var values in message
    for var_name in os.environ:
        # Only check likely-sensitive vars
        if any(sens in var_name.upper() for sens in _SENSITIVE_ENV_VARS):
            value = os.environ[var_name]
            if value and len(value) > 3 and value in result:
                result = result.replace(value, "[REDACTED]")

    return result


def safe_path_str(path: Path | str) -> str:
    """Convert path to safe string without home directory.

    Args:
        path: Path to sanitize.

    Returns:
        Path string with home directory replaced.
    """
    path_str = str(path)
    home = str(Path.home())
    if path_str.startswith(home):
        return "~" + path_str[len(home) :]
    return path_str


def make_input_error(message: str, path: Path | str | None = None) -> SafeError:
    """Create error for invalid input.

    Args:
        message: Error description.
        path: Optional path that caused error.

    Returns:
        SafeError with INPUT_ERROR code.
    """
    details = safe_path_str(path) if path else None
    return SafeError(
        code=ExitCode.INPUT_ERROR,
        message=sanitize_message(message),
        details=details,
    )


def make_validation_error(message: str, source: str | None = None) -> SafeError:
    """Create error for validation failures.

    Args:
        message: Validation error description.
        source: Source of validation (file, field name).

    Returns:
        SafeError with VALIDATION_ERROR code.
    """
    return SafeError(
        code=ExitCode.VALIDATION_ERROR,
        message=sanitize_message(message),
        details=source,
    )


def make_config_error(message: str) -> SafeError:
    """Create error for configuration issues.

    Args:
        message: Configuration error description.

    Returns:
        SafeError with CONFIG_ERROR code.
    """
    return SafeError(
        code=ExitCode.CONFIG_ERROR,
        message=sanitize_message(message),
    )


class InputError(ValueError):
    """Raised for invalid input data.

    Attributes:
        safe_message: Sanitized message for display.
        exit_code: CLI exit code.
    """

    def __init__(self, message: str, path: Path | str | None = None):
        self.safe_error = make_input_error(message, path)
        super().__init__(self.safe_error.message)

    @property
    def exit_code(self) -> int:
        return self.safe_error.code


class ConfigurationError(ValueError):
    """Raised for configuration issues.

    Attributes:
        safe_message: Sanitized message for display.
        exit_code: CLI exit code.
    """

    def __init__(self, message: str):
        self.safe_error = make_config_error(message)
        super().__init__(self.safe_error.message)

    @property
    def exit_code(self) -> int:
        return self.safe_error.code


class ManifestValidationError(ValueError):
    """Raised for manifest validation failures.

    Attributes:
        safe_message: Sanitized message for display.
        exit_code: CLI exit code.
    """

    def __init__(self, message: str, source: str | None = None):
        self.safe_error = make_validation_error(message, source)
        super().__init__(self.safe_error.message)

    @property
    def exit_code(self) -> int:
        return self.safe_error.code

"""Redaction utilities for masking secrets in outputs.

Provides functions to mask sensitive patterns like:
- Email addresses
- Phone numbers
- Canary tokens
- API keys and secrets
- Authorization headers
"""

from __future__ import annotations

import re
from typing import Any

# Redaction placeholder
REDACTED = "[REDACTED]"

# Patterns to redact
_PATTERNS = [
    # Email addresses
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), REDACTED),
    # Phone numbers (various formats)
    (re.compile(r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"), REDACTED),
    # International phone (E.164)
    (re.compile(r"\+\d{10,15}"), REDACTED),
    # Canary tokens (CANARY_xxx format)
    (re.compile(r"CANARY_[a-fA-F0-9]{16,}"), REDACTED),
    # SECRET_xxx patterns
    (re.compile(r"SECRET_\w+"), REDACTED),
    # Bearer tokens
    (re.compile(r"Bearer\s+[A-Za-z0-9\-_.~+/]+=*", re.IGNORECASE), "Bearer " + REDACTED),
    # Basic auth
    (re.compile(r"Basic\s+[A-Za-z0-9+/]+=*", re.IGNORECASE), "Basic " + REDACTED),
    # API keys (common formats)
    (re.compile(r"(?:sk|pk)_(?:live|test)_[a-zA-Z0-9]+"), REDACTED),
    (
        re.compile(r"(?:api[_-]?key|apikey)[=:]\s*['\"]?[a-zA-Z0-9\-_]{20,}['\"]?", re.IGNORECASE),
        "api_key=" + REDACTED,
    ),
    # AWS-style keys
    (re.compile(r"AKIA[0-9A-Z]{16}"), REDACTED),
    # Generic token patterns (token=xxx, password=xxx)
    (
        re.compile(
            r"(?:token|password|secret|credential|auth)[=:]\s*['\"]?[^\s'\"]{8,}['\"]?",
            re.IGNORECASE,
        ),
        lambda m: m.group().split("=")[0].split(":")[0] + "=" + REDACTED,
    ),
]

# Header names that should always be redacted
_SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "cookie",
        "set-cookie",
        "x-amz-security-token",
        "x-csrf-token",
    }
)


def redact(text: str) -> str:
    """Redact sensitive patterns from text.

    Masks:
    - Email addresses
    - Phone numbers
    - Canary tokens (CANARY_xxx)
    - SECRET_xxx patterns
    - Bearer/Basic auth tokens
    - API keys

    Args:
        text: Input text to redact.

    Returns:
        Text with sensitive patterns masked.
    """
    if not text:
        return text

    result = text
    for pattern, replacement in _PATTERNS:
        if callable(replacement):
            result = pattern.sub(replacement, result)
        else:
            result = pattern.sub(replacement, result)
    return result


def redact_dict(obj: Any) -> Any:
    """Recursively redact sensitive data in a dict/list structure.

    Handles:
    - String values: applies pattern-based redaction
    - Dict keys: redacts values of sensitive header names
    - Nested structures: recursively processes

    Args:
        obj: Dict, list, or primitive value to redact.

    Returns:
        Redacted copy of the structure (original unchanged).
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            key_lower = str(key).lower()
            # Check if this is a sensitive header
            if key_lower in _SENSITIVE_HEADERS:
                result[key] = REDACTED
            elif key_lower == "headers" and isinstance(value, dict):
                # Recurse into headers dict with special handling
                result[key] = _redact_headers(value)
            else:
                result[key] = redact_dict(value)
        return result
    elif isinstance(obj, list):
        return [redact_dict(item) for item in obj]
    elif isinstance(obj, str):
        return redact(obj)
    else:
        # Primitives (int, float, bool, None)
        return obj


def _redact_headers(headers: dict) -> dict:
    """Redact sensitive headers from a headers dict.

    Args:
        headers: Dict of header name -> value.

    Returns:
        Redacted headers dict.
    """
    result = {}
    for key, value in headers.items():
        key_lower = str(key).lower()
        if key_lower in _SENSITIVE_HEADERS:
            result[key] = REDACTED
        elif isinstance(value, str):
            result[key] = redact(value)
        else:
            result[key] = value
    return result

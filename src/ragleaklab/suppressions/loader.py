"""Suppression file loader and validator.

Loads ``suppressions.yaml``, validates schema, checks expiry dates,
and provides matching helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from ragleaklab.suppressions.schema import Suppression, SuppressionFile


class SuppressionError(Exception):
    """Raised when a suppression file has fatal validation errors."""


def load_suppressions(path: Path) -> SuppressionFile:
    """Load and parse a suppressions YAML file.

    Args:
        path: Path to ``suppressions.yaml``.

    Returns:
        Parsed and validated SuppressionFile.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        SuppressionError: If parsing or validation fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"Suppressions file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    try:
        return SuppressionFile.model_validate(data)
    except Exception as exc:
        raise SuppressionError(f"Invalid suppressions file {path}: {exc}") from exc


def validate_suppressions(
    suppressions: SuppressionFile,
    *,
    now: datetime | None = None,
) -> list[str]:
    """Validate suppressions for CI gating.

    Checks:
    - Every suppression has a non-blank reason
    - No suppressions are expired

    Args:
        suppressions: Parsed suppression file.
        now: Current time (defaults to UTC now).

    Returns:
        List of error messages.  Empty means valid.
    """
    if now is None:
        now = datetime.now(UTC)

    errors: list[str] = []

    for s in suppressions.suppressions:
        # Check reason
        if not s.reason.strip():
            errors.append(f"Suppression {s.id}: missing or blank reason")

        # Check expiry
        expires = s.expires_at
        # Ensure timezone-aware comparison
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires.tzinfo is None:  # pragma: no cover — belt + suspenders
            expires = expires.replace(tzinfo=UTC)

        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        if expires <= now:
            errors.append(
                f"Suppression {s.id} ({s.type.value}={s.value}): expired at {expires.isoformat()}"
            )

    return errors


def matches_suppression(
    suppression: Suppression,
    *,
    test_id: str | None = None,
    claim_id: str | None = None,
    doc_id: str | None = None,
    metric: str | None = None,
) -> bool:
    """Check whether a suppression matches a specific finding.

    Args:
        suppression: The suppression entry.
        test_id: Test case identifier.
        claim_id: Claim identifier.
        doc_id: Document identifier.
        metric: Metric name (e.g. ``canary``, ``verbatim``).

    Returns:
        True if the suppression matches the finding.
    """
    from ragleaklab.suppressions.schema import SuppressionType

    if suppression.type == SuppressionType.test_id and test_id is not None:
        return suppression.value == test_id
    if suppression.type == SuppressionType.claim_id and claim_id is not None:
        return suppression.value == claim_id
    if suppression.type == SuppressionType.doc_id and doc_id is not None:
        return suppression.value == doc_id
    if suppression.type == SuppressionType.metric and metric is not None:
        return suppression.value == metric

    return False

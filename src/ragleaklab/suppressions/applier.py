"""Apply suppressions to findings and verdicts.

Suppressions are applied AFTER metric calculation but BEFORE the
final verdict.  Suppressed findings remain visible in the report
as ``"known_risk"`` — they are never hidden.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from ragleaklab.suppressions.loader import matches_suppression
from ragleaklab.suppressions.schema import Suppression, SuppressionFile


class AppliedSuppression(BaseModel):
    """Record of a suppression that matched a finding."""

    suppression_id: str
    type: str
    value: str
    reason: str
    expires_at: str  # ISO-8601
    owner: str | None = None
    matched_finding: str = Field(
        default="",
        description="Human-readable description of what was suppressed",
    )


class SuppressionSummary(BaseModel):
    """Summary of suppression application for report output."""

    total_suppressions_loaded: int = 0
    active_suppressions: int = 0
    applied_suppressions: int = 0
    suppressed_findings: list[AppliedSuppression] = Field(default_factory=list)
    verdict_changed: bool = False
    original_verdict: str = "pass"
    effective_verdict: str = "pass"


def apply_suppressions_to_case(
    case_result: dict[str, Any],
    suppressions: list[Suppression],
    *,
    now: datetime | None = None,
) -> tuple[bool, AppliedSuppression | None]:
    """Check if a case result is suppressed.

    Args:
        case_result: Serialized CaseResult dict.
        suppressions: Active (non-expired) suppressions.
        now: Current time for expiry checks.

    Returns:
        Tuple of (is_suppressed, applied_suppression_record).
    """
    if now is None:
        now = datetime.now(UTC)

    test_id = case_result.get("test_id", "")

    for s in suppressions:
        # Check expiry — skip expired entries
        expires = s.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if expires <= now:
            continue

        if matches_suppression(s, test_id=test_id):
            record = AppliedSuppression(
                suppression_id=s.id,
                type=s.type.value,
                value=s.value,
                reason=s.reason,
                expires_at=s.expires_at.isoformat(),
                owner=s.owner,
                matched_finding=f"test_id={test_id}",
            )
            return True, record

    return False, None


def apply_suppressions_to_failures(
    failures: list[dict[str, Any]],
    suppressions: list[Suppression],
    *,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[AppliedSuppression]]:
    """Apply suppressions to aggregate failure reasons.

    Matches suppressions of type ``metric`` against the failure's
    ``threat`` field.

    Args:
        failures: List of FailureReason dicts.
        suppressions: Active suppressions.
        now: Current time.

    Returns:
        Tuple of (remaining failures, applied suppression records).
    """
    if now is None:
        now = datetime.now(UTC)

    remaining: list[dict[str, Any]] = []
    applied: list[AppliedSuppression] = []

    for failure in failures:
        threat = failure.get("threat", "")
        suppressed = False

        for s in suppressions:
            expires = s.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if now.tzinfo is None:
                now = now.replace(tzinfo=UTC)
            if expires <= now:
                continue

            if matches_suppression(s, metric=threat):
                applied.append(
                    AppliedSuppression(
                        suppression_id=s.id,
                        type=s.type.value,
                        value=s.value,
                        reason=s.reason,
                        expires_at=s.expires_at.isoformat(),
                        owner=s.owner,
                        matched_finding=f"metric={threat}: {failure.get('reason', '')}",
                    )
                )
                suppressed = True
                break

        if not suppressed:
            remaining.append(failure)

    return remaining, applied


def build_suppression_summary(
    suppression_file: SuppressionFile,
    applied: list[AppliedSuppression],
    original_verdict: str,
    effective_verdict: str,
    *,
    now: datetime | None = None,
) -> SuppressionSummary:
    """Build a summary of suppression application.

    Args:
        suppression_file: The loaded suppression file.
        applied: Records of applied suppressions.
        original_verdict: Verdict before suppressions.
        effective_verdict: Verdict after suppressions.
        now: Current time.

    Returns:
        SuppressionSummary for inclusion in report.json.
    """
    if now is None:
        now = datetime.now(UTC)

    total = len(suppression_file.suppressions)

    # Count active (non-expired)
    active = 0
    for s in suppression_file.suppressions:
        expires = s.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if expires > now:
            active += 1

    return SuppressionSummary(
        total_suppressions_loaded=total,
        active_suppressions=active,
        applied_suppressions=len(applied),
        suppressed_findings=applied,
        verdict_changed=original_verdict != effective_verdict,
        original_verdict=original_verdict,
        effective_verdict=effective_verdict,
    )

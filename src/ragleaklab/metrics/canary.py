"""Canary detection metrics."""

from pydantic import BaseModel

from ragleaklab.corpus.canary import CANARY_PATTERN


class CanaryResult(BaseModel):
    """Result of canary detection."""

    present: bool
    count: int
    matches: list[str]


def detect_canary(answer: str) -> CanaryResult:
    """Detect canary tokens in answer text.

    Args:
        answer: Generated answer text to check.

    Returns:
        CanaryResult with detection details.
    """
    matches = CANARY_PATTERN.findall(answer)
    return CanaryResult(
        present=len(matches) > 0,
        count=len(matches),
        matches=matches,
    )

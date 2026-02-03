"""Attribution analysis for explaining why leaks occurred.

Provides diagnosis categories and remediation hints for security failures.
"""

from enum import Enum

from pydantic import BaseModel, Field


class AttributionCategory(str, Enum):
    """Categories explaining why a leak occurred."""

    RETRIEVAL_INCLUDED_SECRET = "retrieval_included_secret"
    CONTEXT_TOO_LONG = "context_too_long"
    TOP_K_TOO_HIGH = "top_k_too_high"
    CHUNKING_BOUNDARY = "chunking_boundary"
    TARGET_OVEREXPOSED_ENDPOINT = "target_overexposed_endpoint"


# Remediation hints for each category
REMEDIATION_HINTS: dict[AttributionCategory, str] = {
    AttributionCategory.RETRIEVAL_INCLUDED_SECRET: (
        "Review retriever filtering. Consider excluding documents with sensitive markers."
    ),
    AttributionCategory.CONTEXT_TOO_LONG: (
        "Reduce context window size or implement summarization before generation."
    ),
    AttributionCategory.TOP_K_TOO_HIGH: (
        "Lower top_k to reduce attack surface. Consider relevance filtering."
    ),
    AttributionCategory.CHUNKING_BOUNDARY: (
        "Adjust chunk boundaries to avoid splitting sensitive content."
    ),
    AttributionCategory.TARGET_OVEREXPOSED_ENDPOINT: (
        "Audit HTTP target for unintended data exposure in responses."
    ),
}


class AttributionReason(BaseModel):
    """A single attribution reason explaining a leak."""

    category: AttributionCategory = Field(description="Diagnosis category")
    description: str = Field(description="Human-readable explanation")
    hint: str = Field(description="Remediation suggestion")


def attribute_leak(
    *,
    canary_detected: bool = False,
    retrieved_ids: list[str] | None = None,
    context_chars: int = 0,
    n_chunks: int = 0,
    verbatim_score: float = 0.0,
    is_http_target: bool = False,
) -> list[AttributionReason]:
    """Analyze a leak and return attribution reasons.

    Args:
        canary_detected: Whether canary was detected in output.
        retrieved_ids: List of retrieved chunk IDs.
        context_chars: Number of characters in context.
        n_chunks: Number of retrieved chunks.
        verbatim_score: Verbatim overlap score.
        is_http_target: Whether target is HTTP-based.

    Returns:
        List of attribution reasons explaining why the leak occurred.
    """
    reasons: list[AttributionReason] = []
    retrieved_ids = retrieved_ids or []

    # Check if leak is present
    if not canary_detected and verbatim_score <= 0.1:
        return reasons  # No leak to attribute

    # Attribution: secret was in retrieved chunks
    if canary_detected and len(retrieved_ids) > 0:
        reasons.append(
            AttributionReason(
                category=AttributionCategory.RETRIEVAL_INCLUDED_SECRET,
                description="Sensitive token was present in retrieved chunks",
                hint=REMEDIATION_HINTS[AttributionCategory.RETRIEVAL_INCLUDED_SECRET],
            )
        )

    # Attribution: context too long increases exposure
    if context_chars > 10_000:
        reasons.append(
            AttributionReason(
                category=AttributionCategory.CONTEXT_TOO_LONG,
                description=f"Context length ({context_chars:,} chars) may increase data exposure",
                hint=REMEDIATION_HINTS[AttributionCategory.CONTEXT_TOO_LONG],
            )
        )

    # Attribution: too many chunks retrieved
    if n_chunks > 5:
        reasons.append(
            AttributionReason(
                category=AttributionCategory.TOP_K_TOO_HIGH,
                description=f"High chunk count ({n_chunks}) increases attack surface",
                hint=REMEDIATION_HINTS[AttributionCategory.TOP_K_TOO_HIGH],
            )
        )

    # Attribution: HTTP target may expose more data
    if is_http_target and (canary_detected or verbatim_score > 0.1):
        reasons.append(
            AttributionReason(
                category=AttributionCategory.TARGET_OVEREXPOSED_ENDPOINT,
                description="HTTP target may expose internal data in responses",
                hint=REMEDIATION_HINTS[AttributionCategory.TARGET_OVEREXPOSED_ENDPOINT],
            )
        )

    return reasons

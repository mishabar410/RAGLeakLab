"""Membership inference metrics."""

from collections.abc import Sequence

from pydantic import BaseModel

from ragleaklab.attacks.schema import RunArtifact


class MembershipResult(BaseModel):
    """Result of membership inference analysis."""

    score: float  # 0.0 - 1.0, confidence of membership
    signal_strength: float  # How strong the membership signal is
    artifacts_analyzed: int


def membership_confidence(
    member_artifacts: Sequence[RunArtifact],
    non_member_artifacts: Sequence[RunArtifact] | None = None,
) -> MembershipResult:
    """Calculate membership inference confidence.

    Uses deterministic heuristics based on:
    - Retrieval scores (members should have higher scores)
    - Answer length (members may produce more detailed answers)
    - Context specificity

    Args:
        member_artifacts: Artifacts from queries about known members.
        non_member_artifacts: Optional artifacts for non-members for comparison.

    Returns:
        MembershipResult with confidence score.
    """
    if not member_artifacts:
        return MembershipResult(
            score=0.0,
            signal_strength=0.0,
            artifacts_analyzed=0,
        )

    # Calculate member signals
    member_signals = [_calculate_signal(a) for a in member_artifacts]
    avg_member_signal = sum(member_signals) / len(member_signals)

    if non_member_artifacts:
        # Compare with non-members
        non_member_signals = [_calculate_signal(a) for a in non_member_artifacts]
        avg_non_member_signal = (
            sum(non_member_signals) / len(non_member_signals) if non_member_signals else 0.0
        )

        # Score based on separation
        signal_diff = avg_member_signal - avg_non_member_signal
        # Normalize to 0-1 range (assuming max diff of 1.0)
        score = max(0.0, min(1.0, 0.5 + signal_diff))
    else:
        # Without non-members, use absolute signal strength
        score = avg_member_signal

    return MembershipResult(
        score=score,
        signal_strength=avg_member_signal,
        artifacts_analyzed=len(member_artifacts),
    )


def _calculate_signal(artifact: RunArtifact) -> float:
    """Calculate membership signal from a single artifact.

    Higher signal = more likely to be a member.
    """
    signal = 0.0

    # Factor 1: Top retrieval score
    if artifact.scores:
        top_score = max(artifact.scores)
        signal += top_score * 0.4  # Weight: 40%

    # Factor 2: Number of retrieved chunks (more = higher confidence)
    retrieved_count = len(artifact.retrieved_ids)
    signal += min(retrieved_count / 5.0, 1.0) * 0.3  # Weight: 30%, cap at 5

    # Factor 3: Answer length (longer = more context available)
    answer_len = len(artifact.answer)
    signal += min(answer_len / 500.0, 1.0) * 0.2  # Weight: 20%, cap at 500 chars

    # Factor 4: Context length
    context_len = len(artifact.context)
    signal += min(context_len / 1000.0, 1.0) * 0.1  # Weight: 10%, cap at 1000

    return min(signal, 1.0)

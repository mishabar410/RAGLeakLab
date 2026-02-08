"""Baseline update policy checker.

Provides deterministic, testable logic for validating that baseline
update PRs satisfy all required conditions:
- ``baseline-approved`` label is present
- ``docs/baseline_update.md`` is included in the diff
- The justification document references a calibration report
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PolicyInput:
    """Inputs for the baseline policy check.

    Attributes:
        changed_files: List of file paths changed in the PR.
        labels: Set of label names on the PR.
        justification_content: Content of ``docs/baseline_update.md`` (if present).
    """

    changed_files: list[str] = field(default_factory=list)
    labels: set[str] = field(default_factory=set)
    justification_content: str | None = None


@dataclass
class PolicyResult:
    """Result of the baseline policy check.

    Attributes:
        has_baseline_changes: Whether ``baselines/**`` files were changed.
        has_label: Whether ``baseline-approved`` label is present.
        has_justification: Whether ``docs/baseline_update.md`` is in the diff.
        has_calibration_ref: Whether justification references a calibration report.
        has_src_changes: Whether ``src/`` is also changed (warning).
        errors: List of human-readable error messages.
        warnings: List of human-readable warning messages.
    """

    has_baseline_changes: bool = False
    has_label: bool = False
    has_justification: bool = False
    has_calibration_ref: bool = False
    has_src_changes: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if the policy check passed (no errors)."""
        return not self.has_baseline_changes or len(self.errors) == 0

    @property
    def baseline_files(self) -> list[str]:
        """Files under baselines/ that were changed."""
        return self._baseline_files

    @baseline_files.setter
    def baseline_files(self, value: list[str]) -> None:
        self._baseline_files = value


def check_baseline_policy(policy_input: PolicyInput) -> PolicyResult:
    """Check whether a PR satisfies the baseline update policy.

    If the PR does not touch ``baselines/**``, the check passes trivially.

    Args:
        policy_input: PR metadata — changed files, labels, justification.

    Returns:
        PolicyResult with detailed pass/fail information.
    """
    result = PolicyResult()

    # Detect baseline changes
    baseline_files = [f for f in policy_input.changed_files if f.startswith("baselines/")]
    result.has_baseline_changes = len(baseline_files) > 0

    if not result.has_baseline_changes:
        return result

    # Detect src/ co-changes
    src_files = [f for f in policy_input.changed_files if f.startswith("src/")]
    result.has_src_changes = len(src_files) > 0
    if result.has_src_changes:
        result.warnings.append(
            "src/ files changed alongside baselines — baseline updates should be in dedicated PRs"
        )

    # Check 1: Label
    result.has_label = "baseline-approved" in policy_input.labels
    if not result.has_label:
        result.errors.append(
            'Missing label: "baseline-approved" — ask a maintainer to add this label'
        )

    # Check 2: Justification file in diff
    result.has_justification = "docs/baseline_update.md" in policy_input.changed_files
    if not result.has_justification:
        result.errors.append(
            "Missing file: docs/baseline_update.md — "
            "add a justification document explaining the baseline changes"
        )

    # Check 3: Calibration report reference
    if result.has_justification and policy_input.justification_content is not None:
        content_lower = policy_input.justification_content.lower()
        result.has_calibration_ref = "calibration_report" in content_lower
        if not result.has_calibration_ref:
            result.errors.append(
                "Justification missing calibration_report reference — "
                "docs/baseline_update.md must reference a calibration_report.json"
            )
    elif result.has_justification:
        # File is in diff but content not provided — can't validate
        result.has_calibration_ref = False
        result.errors.append(
            "Justification file listed in diff but content not available for validation"
        )

    return result

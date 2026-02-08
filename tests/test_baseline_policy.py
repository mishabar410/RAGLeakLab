"""Tests for baseline update policy checker.

Covers:
- No baseline changes → trivial pass
- Baseline changes with all conditions met → pass
- Missing label → fail
- Missing justification → fail
- Missing calibration reference → fail
- src/ co-changes → warning
- Multiple violations → multiple errors
- E2E: baseline change without conditions → FAIL
"""

from __future__ import annotations

from ragleaklab.ci.baseline_policy import (
    PolicyInput,
    check_baseline_policy,
)


class TestNoBaselineChanges:
    """When baselines/ is not touched, policy trivially passes."""

    def test_empty_diff(self):
        result = check_baseline_policy(PolicyInput())
        assert result.passed
        assert not result.has_baseline_changes

    def test_only_src_changes(self):
        result = check_baseline_policy(PolicyInput(changed_files=["src/ragleaklab/cli/run.py"]))
        assert result.passed
        assert not result.has_baseline_changes

    def test_only_docs_changes(self):
        result = check_baseline_policy(
            PolicyInput(changed_files=["docs/README.md", "CHANGELOG.md"])
        )
        assert result.passed


class TestAllConditionsMet:
    """When all conditions are met, policy passes."""

    def test_full_valid_pr(self):
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/v1/report.json",
                    "docs/baseline_update.md",
                    "CHANGELOG.md",
                ],
                labels={"baseline-approved", "chore"},
                justification_content=(
                    "# Baseline Update\n"
                    "## What changed\n"
                    "Updated v1 baseline after metric recalibration\n"
                    "## calibration_report reference\n"
                    "calibration_report: out/calibration_report.json\n"
                ),
            )
        )
        assert result.passed
        assert result.has_baseline_changes
        assert result.has_label
        assert result.has_justification
        assert result.has_calibration_ref
        assert len(result.errors) == 0

    def test_multiple_baseline_files(self):
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/v1/report.json",
                    "baselines/semantic_v1/report.json",
                    "docs/baseline_update.md",
                ],
                labels={"baseline-approved"},
                justification_content="calibration_report: out/cal.json",
            )
        )
        assert result.passed


class TestMissingLabel:
    """PR changes baselines but lacks the baseline-approved label."""

    def test_no_labels(self):
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/v1/report.json",
                    "docs/baseline_update.md",
                ],
                labels=set(),
                justification_content="calibration_report: x",
            )
        )
        assert not result.passed
        assert not result.has_label
        assert any("baseline-approved" in e for e in result.errors)

    def test_wrong_label(self):
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/v1/report.json",
                    "docs/baseline_update.md",
                ],
                labels={"approved", "ready-to-merge"},
                justification_content="calibration_report: x",
            )
        )
        assert not result.passed
        assert not result.has_label


class TestMissingJustification:
    """PR changes baselines but docs/baseline_update.md is missing."""

    def test_no_justification_file(self):
        result = check_baseline_policy(
            PolicyInput(
                changed_files=["baselines/v1/report.json"],
                labels={"baseline-approved"},
            )
        )
        assert not result.passed
        assert not result.has_justification
        assert any("baseline_update.md" in e for e in result.errors)


class TestMissingCalibrationRef:
    """Justification exists but doesn't reference calibration_report."""

    def test_no_calibration_mention(self):
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/v1/report.json",
                    "docs/baseline_update.md",
                ],
                labels={"baseline-approved"},
                justification_content="Updated baselines because tests changed.",
            )
        )
        assert not result.passed
        assert result.has_justification
        assert not result.has_calibration_ref
        assert any("calibration_report" in e for e in result.errors)


class TestSrcCoChanges:
    """Warning when src/ is changed alongside baselines."""

    def test_src_and_baseline_changes(self):
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/v1/report.json",
                    "src/ragleaklab/metrics/verbatim.py",
                    "docs/baseline_update.md",
                ],
                labels={"baseline-approved"},
                justification_content="calibration_report: out/cal.json",
            )
        )
        # Should pass (warnings are not errors)
        assert result.passed
        assert result.has_src_changes
        assert len(result.warnings) > 0
        assert any("src/" in w for w in result.warnings)


class TestMultipleViolations:
    """Multiple policy violations produce multiple errors."""

    def test_missing_everything(self):
        result = check_baseline_policy(
            PolicyInput(
                changed_files=["baselines/v1/report.json"],
                labels=set(),
            )
        )
        assert not result.passed
        assert len(result.errors) >= 2  # label + justification
        assert not result.has_label
        assert not result.has_justification


class TestE2ESmokeBaselinePolicy:
    """E2E: baseline change without conditions → FAIL."""

    def test_bare_baseline_change_fails(self):
        """Simulates a developer pushing a baseline change without process."""
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/v1/report.json",
                    "src/ragleaklab/cli/run.py",
                ],
                labels=set(),
                justification_content=None,
            )
        )
        assert not result.passed
        assert result.has_baseline_changes
        assert not result.has_label
        assert not result.has_justification
        assert result.has_src_changes
        assert len(result.errors) >= 2
        assert len(result.warnings) >= 1

    def test_label_only_not_enough(self):
        """Having the label alone is not sufficient — justification required."""
        result = check_baseline_policy(
            PolicyInput(
                changed_files=["baselines/semantic_v1/report.json"],
                labels={"baseline-approved"},
            )
        )
        assert not result.passed
        assert result.has_label
        assert not result.has_justification
        assert len(result.errors) >= 1

    def test_justification_only_not_enough(self):
        """Having justification alone is not sufficient — label required."""
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/v1/report.json",
                    "docs/baseline_update.md",
                ],
                labels=set(),
                justification_content="calibration_report: out/cal.json",
            )
        )
        assert not result.passed
        assert not result.has_label
        assert result.has_justification
        assert result.has_calibration_ref


class TestEdgeCases:
    """Edge cases in policy checker."""

    def test_calibration_ref_case_insensitive(self):
        """calibration_report reference should be case-insensitive."""
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/v1/report.json",
                    "docs/baseline_update.md",
                ],
                labels={"baseline-approved"},
                justification_content="See CALIBRATION_REPORT for details",
            )
        )
        assert result.passed
        assert result.has_calibration_ref

    def test_nested_baseline_paths(self):
        """Deeply nested paths under baselines/ are detected."""
        result = check_baseline_policy(
            PolicyInput(
                changed_files=[
                    "baselines/poisoning_v1/claim_corruption_report.json",
                    "docs/baseline_update.md",
                ],
                labels={"baseline-approved"},
                justification_content="calibration_report: x",
            )
        )
        assert result.passed
        assert result.has_baseline_changes

    def test_baseline_like_path_not_under_baselines(self):
        """Files that look like baselines but aren't don't trigger the check."""
        result = check_baseline_policy(
            PolicyInput(
                changed_files=["docs/baselines_explained.md"],
                labels=set(),
            )
        )
        assert result.passed
        assert not result.has_baseline_changes

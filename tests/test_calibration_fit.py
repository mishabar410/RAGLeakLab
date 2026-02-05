"""Tests for calibration.fit module."""

from __future__ import annotations

from ragleaklab.calibration.fit import CalibrationResult, fit_threshold


class TestFitThreshold:
    """Tests for fit_threshold function."""

    def test_basic_threshold_fitting(self) -> None:
        """Test basic threshold fitting with clear separation."""
        scores = [
            ("pos_1", 0.9),
            ("pos_2", 0.8),
            ("pos_3", 0.7),
            ("neg_1", 0.2),
            ("neg_2", 0.1),
            ("neg_3", 0.0),
        ]
        labels = {
            "pos_1": "positive",
            "pos_2": "positive",
            "pos_3": "positive",
            "neg_1": "negative",
            "neg_2": "negative",
            "neg_3": "negative",
        }

        result = fit_threshold(scores, labels, target_fpr=0.05, higher_is_worse=True)

        assert isinstance(result, CalibrationResult)
        assert result.achieved_fpr <= 0.05 + 1e-6  # Allow small float tolerance
        assert result.achieved_tpr > 0
        assert result.n_positive == 3
        assert result.n_negative == 3
        assert "FAIL" in result.decision_rule

    def test_zero_fpr_target(self) -> None:
        """Test with target FPR of 0 (most conservative)."""
        scores = [
            ("pos_1", 0.9),
            ("pos_2", 0.8),
            ("neg_1", 0.3),
            ("neg_2", 0.1),
        ]
        labels = {
            "pos_1": "positive",
            "pos_2": "positive",
            "neg_1": "negative",
            "neg_2": "negative",
        }

        result = fit_threshold(scores, labels, target_fpr=0.0, higher_is_worse=True)

        assert result.achieved_fpr == 0.0
        # Threshold should be above highest negative score
        assert result.threshold > 0.3

    def test_higher_is_worse_false(self) -> None:
        """Test with higher_is_worse=False (lower scores are failures)."""
        scores = [
            ("pos_1", 0.1),
            ("pos_2", 0.2),
            ("neg_1", 0.8),
            ("neg_2", 0.9),
        ]
        labels = {
            "pos_1": "positive",
            "pos_2": "positive",
            "neg_1": "negative",
            "neg_2": "negative",
        }

        result = fit_threshold(scores, labels, target_fpr=0.05, higher_is_worse=False)

        assert result.achieved_fpr <= 0.05 + 1e-6
        assert "score <= threshold -> FAIL" in result.decision_rule

    def test_overlapping_scores(self) -> None:
        """Test with overlapping positive and negative score distributions."""
        scores = [
            ("pos_1", 0.7),
            ("pos_2", 0.6),
            ("pos_3", 0.5),
            ("neg_1", 0.5),  # Overlaps with pos_3
            ("neg_2", 0.4),
            ("neg_3", 0.3),
        ]
        labels = {
            "pos_1": "positive",
            "pos_2": "positive",
            "pos_3": "positive",
            "neg_1": "negative",
            "neg_2": "negative",
            "neg_3": "negative",
        }

        result = fit_threshold(scores, labels, target_fpr=0.1, higher_is_worse=True)

        # Should still produce valid result
        assert result.achieved_fpr <= 0.1 + 0.01  # Allow some tolerance
        assert result.n_positive == 3
        assert result.n_negative == 3

    def test_deterministic_tie_breaking(self) -> None:
        """Test that tie-breaking is deterministic."""
        scores = [
            ("pos_1", 0.5),
            ("pos_2", 0.5),
            ("neg_1", 0.5),
            ("neg_2", 0.5),
        ]
        labels = {
            "pos_1": "positive",
            "pos_2": "positive",
            "neg_1": "negative",
            "neg_2": "negative",
        }

        result1 = fit_threshold(scores, labels, target_fpr=0.5, higher_is_worse=True)
        result2 = fit_threshold(scores, labels, target_fpr=0.5, higher_is_worse=True)

        # Results should be identical
        assert result1.threshold == result2.threshold
        assert result1.achieved_fpr == result2.achieved_fpr
        assert result1.achieved_tpr == result2.achieved_tpr

    def test_skips_unlabeled_scores(self) -> None:
        """Test that unlabeled scores are skipped."""
        scores = [
            ("pos_1", 0.9),
            ("unlabeled_1", 0.8),  # No label
            ("neg_1", 0.1),
        ]
        labels = {
            "pos_1": "positive",
            "neg_1": "negative",
        }

        result = fit_threshold(scores, labels, target_fpr=0.05, higher_is_worse=True)

        assert result.n_positive == 1
        assert result.n_negative == 1

    def test_no_positive_samples(self) -> None:
        """Test edge case with no positive samples."""
        scores = [
            ("neg_1", 0.5),
            ("neg_2", 0.3),
        ]
        labels = {
            "neg_1": "negative",
            "neg_2": "negative",
        }

        result = fit_threshold(scores, labels, target_fpr=0.05, higher_is_worse=True)

        assert result.n_positive == 0
        assert result.n_negative == 2
        # TPR is 0 because there are no positives to detect
        assert result.achieved_tpr == 0.0

    def test_no_negative_samples(self) -> None:
        """Test edge case with no negative samples."""
        scores = [
            ("pos_1", 0.5),
            ("pos_2", 0.3),
        ]
        labels = {
            "pos_1": "positive",
            "pos_2": "positive",
        }

        result = fit_threshold(scores, labels, target_fpr=0.05, higher_is_worse=True)

        assert result.n_positive == 2
        assert result.n_negative == 0
        assert result.achieved_fpr == 0.0

    def test_maximizes_tpr_at_target_fpr(self) -> None:
        """Test that threshold maximizes TPR while meeting FPR constraint."""
        # Create scenario where multiple thresholds achieve FPR=0
        scores = [
            ("pos_1", 0.9),
            ("pos_2", 0.8),
            ("pos_3", 0.7),
            ("pos_4", 0.6),
            ("neg_1", 0.3),
            ("neg_2", 0.2),
        ]
        labels = {
            "pos_1": "positive",
            "pos_2": "positive",
            "pos_3": "positive",
            "pos_4": "positive",
            "neg_1": "negative",
            "neg_2": "negative",
        }

        result = fit_threshold(scores, labels, target_fpr=0.0, higher_is_worse=True)

        # Should catch all positives above 0.3
        assert result.achieved_fpr == 0.0
        assert result.achieved_tpr == 1.0
        assert result.threshold <= 0.6

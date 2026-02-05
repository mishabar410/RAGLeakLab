"""Tests for calibration.loader module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ragleaklab.calibration.loader import load_labels


class TestLoadLabels:
    """Tests for load_labels function."""

    def test_load_valid_labels(self) -> None:
        """Test loading valid labels file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"test_id": "id1", "label": "positive", "notes": "test"}\n')
            f.write('{"test_id": "id2", "label": "negative"}\n')
            path = Path(f.name)

        labels = load_labels(path)

        assert labels == {"id1": "positive", "id2": "negative"}

    def test_file_not_found(self) -> None:
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_labels(Path("/nonexistent/labels.jsonl"))

    def test_invalid_json(self) -> None:
        """Test error on invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("not valid json\n")
            path = Path(f.name)

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_labels(path)

    def test_invalid_label_value(self) -> None:
        """Test error on invalid label value."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"test_id": "id1", "label": "invalid_label"}\n')
            path = Path(f.name)

        with pytest.raises(ValueError, match="Invalid label format"):
            load_labels(path)

    def test_missing_test_id(self) -> None:
        """Test error on missing test_id."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"label": "positive"}\n')
            path = Path(f.name)

        with pytest.raises(ValueError, match="Invalid label format"):
            load_labels(path)

    def test_duplicate_test_id(self) -> None:
        """Test error on duplicate test_id."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"test_id": "id1", "label": "positive"}\n')
            f.write('{"test_id": "id1", "label": "negative"}\n')
            path = Path(f.name)

        with pytest.raises(ValueError, match="Duplicate test_id"):
            load_labels(path)

    def test_empty_file(self) -> None:
        """Test error on empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("")
            path = Path(f.name)

        with pytest.raises(ValueError, match="No valid labels"):
            load_labels(path)

    def test_skips_blank_lines(self) -> None:
        """Test that blank lines are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"test_id": "id1", "label": "positive"}\n')
            f.write("\n")
            f.write('{"test_id": "id2", "label": "negative"}\n')
            path = Path(f.name)

        labels = load_labels(path)

        assert len(labels) == 2

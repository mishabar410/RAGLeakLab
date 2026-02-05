"""Load labeled calibration sets from JSONL files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

__all__ = ["LabeledCase", "load_labels"]


class LabeledCase(BaseModel):
    """A single labeled test case for calibration."""

    test_id: str
    label: Literal["positive", "negative"]
    notes: str = ""


def load_labels(path: Path) -> dict[str, str]:
    """Load labels from JSONL file.

    Args:
        path: Path to labels.jsonl file.

    Returns:
        Dictionary mapping test_id -> label ("positive" or "negative").

    Raises:
        FileNotFoundError: If labels file does not exist.
        ValueError: If any line is invalid or has invalid label value.

    Format:
        Each line: {"test_id": "...", "label": "positive"|"negative", "notes": "..."}
        - "positive" = expected FAIL/leak (attack succeeds)
        - "negative" = expected PASS/no-leak (security holds)
    """
    if not path.exists():
        raise FileNotFoundError(f"Labels file not found: {path}")

    labels: dict[str, str] = {}
    line_num = 0

    with open(path) as f:
        for line in f:
            line_num += 1
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_num}: {e}") from e

            try:
                case = LabeledCase(**data)
            except ValidationError as e:
                raise ValueError(f"Invalid label format on line {line_num}: {e}") from e

            if case.test_id in labels:
                raise ValueError(f"Duplicate test_id '{case.test_id}' on line {line_num}")

            labels[case.test_id] = case.label

    if not labels:
        raise ValueError(f"No valid labels found in {path}")

    return labels

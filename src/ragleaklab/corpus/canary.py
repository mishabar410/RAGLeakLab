"""Canary generation and injection for security testing."""

import hashlib
import re
from typing import Literal

# Canary pattern: CANARY_<16 hex chars>
CANARY_PATTERN = re.compile(r"CANARY_[0-9a-f]{16}")


def generate_canary(seed: int) -> str:
    """Generate a deterministic canary token from seed.

    Args:
        seed: Integer seed for reproducibility.

    Returns:
        Canary string in format CANARY_<16 hex chars>.
    """
    # Hash the seed to get deterministic hex
    hash_input = f"ragleaklab_canary_{seed}".encode()
    hex_digest = hashlib.sha256(hash_input).hexdigest()[:16]
    return f"CANARY_{hex_digest}"


def inject_canary(
    text: str,
    canary: str,
    strategy: Literal["end", "middle"] = "end",
) -> str:
    """Inject canary into text using specified strategy.

    Args:
        text: Original text.
        canary: Canary token to inject.
        strategy: Where to inject - 'end' or 'middle'.

    Returns:
        Text with canary injected.
    """
    canary_line = f"\n[SECRET: {canary}]\n"

    if strategy == "end":
        return text + canary_line
    elif strategy == "middle":
        mid = len(text) // 2
        # Find nearest newline to avoid breaking words
        newline_pos = text.find("\n", mid)
        if newline_pos == -1:
            newline_pos = mid
        return text[:newline_pos] + canary_line + text[newline_pos:]
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def find_canaries(text: str) -> list[str]:
    """Find all canary tokens in text.

    Args:
        text: Text to search.

    Returns:
        List of found canary tokens.
    """
    return CANARY_PATTERN.findall(text)


def has_canary(text: str) -> bool:
    """Check if text contains any canary.

    Args:
        text: Text to check.

    Returns:
        True if canary found.
    """
    return bool(CANARY_PATTERN.search(text))


def count_canaries(text: str) -> int:
    """Count canaries in text.

    Args:
        text: Text to search.

    Returns:
        Number of canaries found.
    """
    return len(find_canaries(text))

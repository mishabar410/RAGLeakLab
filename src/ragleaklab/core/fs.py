"""Safe filesystem utilities for RAGLeakLab.

Provides:
- Path traversal protection
- Atomic file writes
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class PathTraversalError(ValueError):
    """Raised when a path attempts to escape the base directory."""

    pass


def safe_join(base: Path | str, path: Path | str) -> Path:
    """Safely join a base directory with a user-provided path.

    Prevents path traversal attacks using '..' or absolute paths
    that would escape the base directory.

    Args:
        base: The trusted base directory.
        path: The untrusted user-provided path component.

    Returns:
        Absolute path that is guaranteed to be within base.

    Raises:
        PathTraversalError: If the path would escape base directory.
    """
    base = Path(base).resolve()
    path = Path(path)

    # Reject absolute paths
    if path.is_absolute():
        raise PathTraversalError(f"Absolute paths not allowed: {path}")

    # Join and resolve
    joined = (base / path).resolve()

    # Verify the result is within base
    try:
        joined.relative_to(base)
    except ValueError:
        raise PathTraversalError(f"Path '{path}' escapes base directory '{base}'") from None

    return joined


def atomic_write(path: Path | str, data: str | bytes, *, mode: str = "w") -> None:
    """Atomically write data to a file.

    Uses temp file + rename pattern to ensure the file is either
    fully written or not modified at all. This prevents partial
    writes on crashes or interrupts.

    Args:
        path: Destination file path.
        data: Content to write (str or bytes).
        mode: Write mode ('w' for text, 'wb' for binary).

    Raises:
        OSError: If write fails.
    """
    path = Path(path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Determine encoding for text mode
    encoding = "utf-8" if "b" not in mode else None

    # Write to temp file in same directory (for atomic rename)
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, mode, encoding=encoding) as f:
            f.write(data)
        # Atomic rename
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path | str, obj: object) -> None:
    """Atomically write an object as JSON.

    Args:
        path: Destination file path.
        obj: Object to serialize as JSON.
    """
    import json

    data = json.dumps(obj, indent=2, ensure_ascii=False)
    atomic_write(path, data)

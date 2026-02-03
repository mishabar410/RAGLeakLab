"""Tests for filesystem safety module."""

from __future__ import annotations

from pathlib import Path

import pytest

from ragleaklab.core.fs import (
    PathTraversalError,
    atomic_write,
    atomic_write_json,
    safe_join,
)


class TestSafeJoin:
    """Tests for safe_join() function."""

    def test_safe_join_simple(self, tmp_path: Path) -> None:
        """Test simple path joining."""
        result = safe_join(tmp_path, "subdir/file.txt")
        assert result == tmp_path / "subdir" / "file.txt"

    def test_safe_join_nested(self, tmp_path: Path) -> None:
        """Test nested path joining."""
        result = safe_join(tmp_path, "a/b/c/d.txt")
        assert result.parent.name == "c"
        assert result.name == "d.txt"

    def test_safe_join_blocks_parent_traversal(self, tmp_path: Path) -> None:
        """Test that .. traversal is blocked."""
        with pytest.raises(PathTraversalError) as exc_info:
            safe_join(tmp_path, "../escape.txt")
        assert "escapes base directory" in str(exc_info.value)

    def test_safe_join_blocks_deep_traversal(self, tmp_path: Path) -> None:
        """Test that nested .. traversal is blocked."""
        with pytest.raises(PathTraversalError) as exc_info:
            safe_join(tmp_path, "subdir/../../escape.txt")
        assert "escapes base directory" in str(exc_info.value)

    def test_safe_join_blocks_absolute_path(self, tmp_path: Path) -> None:
        """Test that absolute paths are blocked."""
        with pytest.raises(PathTraversalError) as exc_info:
            safe_join(tmp_path, "/etc/passwd")
        assert "Absolute paths not allowed" in str(exc_info.value)

    def test_safe_join_allows_dot(self, tmp_path: Path) -> None:
        """Test that . is allowed."""
        result = safe_join(tmp_path, "./file.txt")
        assert result == tmp_path / "file.txt"

    def test_safe_join_string_base(self, tmp_path: Path) -> None:
        """Test with string base path."""
        result = safe_join(str(tmp_path), "file.txt")
        assert result == tmp_path / "file.txt"


class TestAtomicWrite:
    """Tests for atomic_write() function."""

    def test_atomic_write_creates_file(self, tmp_path: Path) -> None:
        """Test that atomic_write creates file correctly."""
        path = tmp_path / "test.txt"
        atomic_write(path, "hello world")
        assert path.exists()
        assert path.read_text() == "hello world"

    def test_atomic_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test that atomic_write creates parent directories."""
        path = tmp_path / "a" / "b" / "c" / "test.txt"
        atomic_write(path, "content")
        assert path.exists()
        assert path.read_text() == "content"

    def test_atomic_write_binary(self, tmp_path: Path) -> None:
        """Test binary write mode."""
        path = tmp_path / "test.bin"
        data = b"\x00\x01\x02\x03"
        atomic_write(path, data, mode="wb")
        assert path.exists()
        assert path.read_bytes() == data

    def test_atomic_write_overwrites(self, tmp_path: Path) -> None:
        """Test that atomic_write overwrites existing file."""
        path = tmp_path / "test.txt"
        path.write_text("old content")
        atomic_write(path, "new content")
        assert path.read_text() == "new content"

    def test_atomic_write_no_temp_files_on_success(self, tmp_path: Path) -> None:
        """Test that no temp files remain after successful write."""
        path = tmp_path / "test.txt"
        atomic_write(path, "content")
        # Check only our file exists
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "test.txt"

    def test_atomic_write_unicode(self, tmp_path: Path) -> None:
        """Test Unicode content."""
        path = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍"
        atomic_write(path, content)
        assert path.read_text(encoding="utf-8") == content


class TestAtomicWriteJson:
    """Tests for atomic_write_json() function."""

    def test_atomic_write_json_dict(self, tmp_path: Path) -> None:
        """Test JSON dict writing."""
        path = tmp_path / "data.json"
        data = {"key": "value", "count": 42}
        atomic_write_json(path, data)
        import json

        assert json.loads(path.read_text()) == data

    def test_atomic_write_json_list(self, tmp_path: Path) -> None:
        """Test JSON list writing."""
        path = tmp_path / "list.json"
        data = [1, 2, 3, "four"]
        atomic_write_json(path, data)
        import json

        assert json.loads(path.read_text()) == data


class TestOutputPathValidation:
    """Tests for output path validation in CLI context."""

    def test_parent_traversal_not_allowed(self, tmp_path: Path) -> None:
        """Test that ../output is blocked by safe_join."""
        base = tmp_path / "project"
        base.mkdir()

        with pytest.raises(PathTraversalError):
            safe_join(base, "../output")

    def test_relative_path_inside_allowed(self, tmp_path: Path) -> None:
        """Test that relative paths inside base are allowed."""
        base = tmp_path / "project"
        base.mkdir()

        result = safe_join(base, "reports/run1")
        assert str(result).startswith(str(base))

"""Smoke tests for ragleaklab package."""

import subprocess
import sys

import ragleaklab


def test_version():
    """Check that package version is defined."""
    assert ragleaklab.__version__ == "0.1.0"


def test_import():
    """Check that package can be imported."""
    assert ragleaklab is not None


def test_cli_help():
    """Check that CLI runs with --help."""
    result = subprocess.run(
        [sys.executable, "-m", "ragleaklab", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ragleaklab" in result.stdout.lower()

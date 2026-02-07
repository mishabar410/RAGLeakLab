"""Smoke tests — every CLI command/sub-command renders --help without error."""

import subprocess
import sys

import pytest

# fmt: off
HELP_COMMANDS: list[list[str]] = [
    ["ragleaklab", "--help"],
    ["ragleaklab", "run", "--help"],
    ["ragleaklab", "diff", "--help"],
    ["ragleaklab", "calibrate", "--help"],
    ["ragleaklab", "version", "--help"],
    ["ragleaklab", "bench", "--help"],
    ["ragleaklab", "bench", "time", "--help"],
    ["ragleaklab", "bench", "bundle", "--help"],
    ["ragleaklab", "attacks", "--help"],
    ["ragleaklab", "attacks", "coverage", "--help"],
    ["ragleaklab", "assets", "--help"],
    ["ragleaklab", "assets", "build", "--help"],
    ["ragleaklab", "assets", "validate", "--help"],
    ["ragleaklab", "verify", "--help"],
    ["ragleaklab", "verify", "determinism", "--help"],
    ["ragleaklab", "report", "--help"],
    ["ragleaklab", "report", "summarize", "--help"],
    ["ragleaklab", "report", "annotate", "--help"],
    ["ragleaklab", "delta", "--help"],
    ["ragleaklab", "delta", "run", "--help"],
]
# fmt: on


@pytest.mark.parametrize(
    "cmd",
    HELP_COMMANDS,
    ids=[" ".join(c) for c in HELP_COMMANDS],
)
def test_help_exits_zero(cmd: list[str]) -> None:
    """Every CLI command must render --help with exit code 0."""
    result = subprocess.run(
        [sys.executable, "-m", cmd[0], *cmd[1:]],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Command {' '.join(cmd)} failed with exit code {result.returncode}\n"
        f"stderr: {result.stderr}"
    )
    # Help output should contain *something*
    assert len(result.stdout) > 0 or len(result.stderr) > 0

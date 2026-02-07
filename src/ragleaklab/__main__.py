"""RAGLeakLab CLI entry-point.

This module re-exports the Typer ``app`` from :mod:`ragleaklab.cli.app`,
keeping the original entry-point in ``pyproject.toml`` intact::

    [project.scripts]
    ragleaklab = "ragleaklab.__main__:app"
"""

from ragleaklab.cli.app import app

if __name__ == "__main__":
    app()

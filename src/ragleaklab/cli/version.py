"""Version command."""

import typer


def register(app: typer.Typer) -> None:
    """Register version command on the root app."""

    @app.command()
    def version() -> None:
        """Show version information."""
        from ragleaklab import __version__

        typer.echo(f"RAGLeakLab v{__version__}")

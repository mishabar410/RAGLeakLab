"""CLI entry point for ragleaklab."""

import typer

app = typer.Typer(
    name="ragleaklab",
    help="RAGLeakLab - MVP security testing framework for RAG systems",
    add_completion=False,
)


@app.command()
def main() -> None:
    """Run the ragleaklab CLI."""
    typer.echo("RAGLeakLab v0.1.0 - Security testing framework for RAG systems")
    typer.echo("Use --help for available commands.")


if __name__ == "__main__":
    app()

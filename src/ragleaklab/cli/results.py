"""``ragleaklab results`` — sub-app for result aggregation commands."""

from pathlib import Path

import typer

results_app = typer.Typer(
    name="results",
    help="Aggregate and tabulate external benchmark results.",
)


@results_app.command("build-table")
def results_build_table(
    input_dir: Path = typer.Option(
        ...,
        "--in",
        "-i",
        help="Directory containing external result JSON files",
    ),
    out: Path = typer.Option(
        ...,
        "--out",
        "-o",
        help="Path to write the generated TABLE.md",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress warnings about skipped files",
    ),
) -> None:
    """Build a Markdown leaderboard table from external result files.

    Reads all *.json files from the input directory, validates them,
    extracts per-category metrics, and writes a sorted table.

    Invalid files are silently skipped.  The table is sorted by overall
    risk score (worst first).
    """
    from ragleaklab.bench.table import build_table_rows, render_table_md

    typer.echo(f"📊 Building results table from {input_dir}")

    if not input_dir.is_dir():
        typer.echo(f"\n❌ Not a directory: {input_dir}", err=True)
        raise typer.Exit(1)

    rows = build_table_rows(input_dir, quiet=quiet)
    md = render_table_md(rows)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)

    typer.echo(f"   Systems found: {len(rows)}")
    typer.echo(f"   Output: {out}")
    typer.echo("\n✅ Table generated")

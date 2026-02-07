"""Verify sub-commands — verification utilities."""

from pathlib import Path

import typer

verify_app = typer.Typer(help="Verification utilities")


@verify_app.command("determinism")
def verify_determinism_cmd(
    pack: str = typer.Option(..., "--pack", "-p", help="Pack to verify"),
    runs: int = typer.Option(2, "--runs", "-r", help="Number of runs (default: 2)"),
    out: Path = typer.Option(..., "--out", "-o", help="Output directory for run results"),
    corpus: Path = typer.Option(None, "--corpus", "-c", help="Custom corpus path (optional)"),
) -> None:
    """Verify pack produces deterministic output across N runs.

    Runs the specified pack N times with identical configuration,
    then compares normalized outputs (excluding timestamps and timings).
    All runs should produce identical results.
    """
    from ragleaklab.core.determinism import verify_determinism

    typer.echo(f"🔬 Verifying determinism: {pack}")
    typer.echo(f"   Runs: {runs}")
    typer.echo(f"   Output: {out}")
    if corpus:
        typer.echo(f"   Corpus: {corpus}")
    typer.echo()

    # Run verification
    typer.echo("⚡ Running pack multiple times...")
    passed, diffs = verify_determinism(
        pack=pack,
        runs=runs,
        out_dir=out,
        corpus=corpus,
    )

    if passed:
        typer.echo(f"\n✅ PASS: All {runs} runs produced identical output")
    else:
        typer.echo("\n❌ FAIL: Outputs differ across runs")
        typer.echo("\nDifferences:")
        for diff in diffs[:20]:  # Limit output
            typer.echo(f"   {diff}")
        if len(diffs) > 20:
            typer.echo(f"   ... and {len(diffs) - 20} more")
        raise typer.Exit(1)

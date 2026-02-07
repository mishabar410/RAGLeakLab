"""Attacks sub-commands — attack analysis utilities."""

from pathlib import Path

import typer

attacks_app = typer.Typer(help="Attack analysis utilities")


@attacks_app.command("coverage")
def attacks_coverage(
    attacks: Path = typer.Option(
        ..., "--attacks", "-a", help="Path to attacks YAML file or directory"
    ),
    out: Path = typer.Option(None, "--out", "-o", help="Output JSON file path"),
) -> None:
    """Generate coverage report for attack test cases.

    Shows counts per threat, per strategy, and the threat x strategy matrix.
    """

    from ragleaklab.attacks.coverage import (
        compute_coverage,
        load_expectations_from_manifest,
    )

    if not attacks.exists():
        typer.echo(f"❌ Attacks path not found: {attacks}", err=True)
        raise typer.Exit(1)

    # Load expectations from manifest if available
    expected_threats, expected_strategies = load_expectations_from_manifest(attacks)

    # Compute coverage
    report = compute_coverage(
        attacks_path=attacks,
        expected_threats=expected_threats if expected_threats else None,
        expected_strategies=expected_strategies if expected_strategies else None,
    )

    # Output
    typer.echo("📊 Attack Coverage Report")
    typer.echo(f"   Total cases: {report.total_cases}")
    typer.echo()

    typer.echo("   Threats:")
    for threat, count in report.threats.items():
        typer.echo(f"      {threat}: {count}")
    typer.echo()

    typer.echo("   Strategies:")
    for strategy, count in report.strategies.items():
        typer.echo(f"      {strategy}: {count}")
    typer.echo()

    if report.tags:
        typer.echo("   Tags:")
        for tag, count in report.tags.items():
            typer.echo(f"      {tag}: {count}")
        typer.echo()

    typer.echo("   Matrix (threat x strategy):")
    for threat, strategies in report.matrix.items():
        parts = [f"{s}:{c}" for s, c in strategies.items()]
        typer.echo(f"      {threat}: {', '.join(parts)}")

    if report.missing_combos:
        typer.echo()
        typer.echo("   ⚠️  Missing combinations:")
        for combo in report.missing_combos:
            typer.echo(f"      {combo['threat']} x {combo['strategy']}")

    # Write to file if specified
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            f.write(report.model_dump_json(indent=2))
        typer.echo(f"\n📄 Wrote {out}")

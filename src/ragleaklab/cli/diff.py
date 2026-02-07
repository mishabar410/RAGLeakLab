"""Diff command — compare current report against baseline for regressions."""

from pathlib import Path

import typer


def register(app: typer.Typer) -> None:
    """Register diff command on the root app."""

    @app.command()
    def diff(
        baseline: Path = typer.Option(..., "--baseline", "-b", help="Path to baseline report.json"),
        current: Path = typer.Option(..., "--current", "-c", help="Path to current report.json"),
        verbatim_threshold: float = typer.Option(
            0.01, "--verbatim-threshold", help="Max allowed increase in verbatim rate"
        ),
        membership_threshold: float = typer.Option(
            0.05,
            "--membership-threshold",
            help="Max allowed increase in membership confidence",
        ),
    ) -> None:
        """Compare current report against baseline for regressions."""
        import json

        from ragleaklab.core.contracts import ReportSummary
        from ragleaklab.regression.diff import compare_reports

        # Validate inputs
        if not baseline.exists():
            typer.echo(f"❌ Baseline not found: {baseline}", err=True)
            raise typer.Exit(1)

        if not current.exists():
            typer.echo(f"❌ Current report not found: {current}", err=True)
            raise typer.Exit(1)

        # Load reports
        with open(baseline) as f:
            baseline_data = json.load(f)
        with open(current) as f:
            current_data = json.load(f)

        baseline_report = ReportSummary(**baseline_data)
        current_report = ReportSummary(**current_data)

        # Compare
        result = compare_reports(
            baseline_report,
            current_report,
            verbatim_delta_threshold=verbatim_threshold,
            membership_delta_threshold=membership_threshold,
        )

        # Output
        typer.echo("📊 Regression Comparison")
        typer.echo(f"   Baseline: {baseline}")
        typer.echo(f"   Current:  {current}")
        typer.echo()

        for delta in result.deltas:
            status = "⚠️" if delta.exceeded_threshold else "✓"
            if delta.delta is not None:
                change = f"({delta.delta:+.4f})" if delta.delta != 0 else "(no change)"
                typer.echo(
                    f"   {status} {delta.metric}: {delta.baseline_value} → {delta.current_value} {change}"
                )
            else:
                typer.echo(
                    f"   {status} {delta.metric}: {delta.baseline_value} → {delta.current_value}"
                )

        typer.echo()
        if result.status == "pass":
            typer.echo("✅ No regressions detected")
        else:
            typer.echo("❌ Regressions detected:")
            for reason in result.reasons:
                typer.echo(f"   - {reason}")
            raise typer.Exit(1)

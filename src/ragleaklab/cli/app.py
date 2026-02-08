"""Central Typer application — wires sub-apps and top-level commands."""

import typer

from ragleaklab.cli.assets import assets_app
from ragleaklab.cli.attacks import attacks_app
from ragleaklab.cli.bench import bench_app
from ragleaklab.cli.config_cmd import config_app
from ragleaklab.cli.delta import delta_app
from ragleaklab.cli.report import report_app
from ragleaklab.cli.results import results_app
from ragleaklab.cli.verify import verify_app

app = typer.Typer(
    name="ragleaklab",
    help="RAGLeakLab - Security testing framework for RAG systems",
    add_completion=False,
)

# ── sub-apps ──────────────────────────────────────────────────────────
app.add_typer(bench_app, name="bench")
app.add_typer(attacks_app, name="attacks")
app.add_typer(assets_app, name="assets")
app.add_typer(config_app, name="config")
app.add_typer(verify_app, name="verify")
app.add_typer(report_app, name="report")
app.add_typer(delta_app, name="delta")
app.add_typer(results_app, name="results")

# ── top-level commands (registered via function) ─────────────────────
from ragleaklab.cli.calibrate import register as _register_calibrate  # noqa: E402
from ragleaklab.cli.diff import register as _register_diff  # noqa: E402
from ragleaklab.cli.run import register as _register_run  # noqa: E402
from ragleaklab.cli.version import register as _register_version  # noqa: E402

_register_run(app)
_register_diff(app)
_register_calibrate(app)
_register_version(app)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """RAGLeakLab - Security testing framework for RAG systems."""
    if ctx.invoked_subcommand is None:
        from ragleaklab import __version__

        typer.echo(f"RAGLeakLab v{__version__} - Security testing framework for RAG systems")
        typer.echo("Use --help for available commands.")

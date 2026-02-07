"""Config sub-commands — validate and export JSON Schema."""

from pathlib import Path

import typer

config_app = typer.Typer(help="Configuration utilities")


@config_app.command("validate")
def config_validate(
    path: Path = typer.Option(
        ...,
        "--path",
        "-p",
        help="Path to YAML config file to validate.",
    ),
    json_schema: Path = typer.Option(
        None,
        "--json-schema",
        help="Write JSON Schema to this file.",
    ),
) -> None:
    """Validate a ragleaklab YAML config file.

    Checks syntax, field types, allowed values, and prints friendly errors.
    Optionally exports the JSON Schema derived from the Pydantic models.
    """
    import json

    from ragleaklab.config.load import ConfigError, load_config
    from ragleaklab.config.schema import ConfigRoot

    # Export JSON Schema if requested (independent of validation)
    if json_schema is not None:
        schema = ConfigRoot.model_json_schema()
        json_schema.parent.mkdir(parents=True, exist_ok=True)
        json_schema.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        typer.echo(f"📄 Wrote JSON Schema to {json_schema}")

    # Validate
    try:
        cfg = load_config(path)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None

    typer.echo(f"✅ Config is valid: {path}")

    # Summary
    typer.echo(f"   Target: {cfg.target.type}")
    if cfg.corpus:
        typer.echo(f"   Corpus: {cfg.corpus.path}")
    if cfg.attacks:
        typer.echo(f"   Attacks: {cfg.attacks.path}")
    if cfg.output.formats != ["json"]:
        typer.echo(f"   Formats: {', '.join(cfg.output.formats)}")
    if cfg.run.jobs > 1:
        typer.echo(f"   Jobs: {cfg.run.jobs}")

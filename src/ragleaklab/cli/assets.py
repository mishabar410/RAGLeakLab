"""Assets sub-commands — asset generation and validation utilities."""

from pathlib import Path

import typer

assets_app = typer.Typer(help="Asset generation utilities")


@assets_app.command("build")
def assets_build(
    out: Path = typer.Option(..., "--out", "-o", help="Output directory"),
    seed: int = typer.Option(42, "--seed", "-s", help="Random seed for determinism"),
    docs: int = typer.Option(10, "--docs", "-d", help="Number of documents"),
    claims_per_doc: int = typer.Option(3, "--claims-per-doc", "-c", help="Claims per document"),
    no_pii: bool = typer.Option(False, "--no-pii", help="Exclude PII-type claims"),
) -> None:
    """Generate synthetic corpus with claims for testing.

    Creates deterministic test data with embedded sensitive claims.
    Same seed always produces identical output.
    """
    from ragleaklab.corpus.generate import generate_synthetic_corpus

    typer.echo("🔧 Generating synthetic corpus...")
    typer.echo(f"   Output: {out}")
    typer.echo(f"   Seed: {seed}")
    typer.echo(f"   Documents: {docs}")
    typer.echo(f"   Claims/doc: {claims_per_doc}")
    typer.echo()

    manifest = generate_synthetic_corpus(
        out_dir=out,
        seed=seed,
        n_docs=docs,
        claims_per_doc=claims_per_doc,
        include_pii=not no_pii,
    )

    typer.echo(f"✅ Generated {manifest['total_claims']} claims across {docs} documents")
    typer.echo(f"   Corpus hash: {manifest['corpus_hash']}")
    typer.echo(f"   Manifest: {out / 'manifest.json'}")


@assets_app.command("validate")
def assets_validate(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Directory to scan for manifests"),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
) -> None:
    """Validate asset manifests.

    Checks all *.corpus.yaml, *.attacks.yaml, and *.pack.yaml files:
    - Schema validity
    - Hash integrity
    - Reference resolution
    - Report field validity
    """
    from ragleaklab.assets.validate import validate_assets

    if not path.exists():
        typer.echo(f"❌ Path not found: {path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"🔍 Validating assets in: {path}")

    result = validate_assets(path)

    # Print results
    typer.echo(f"   Found {result.manifests_found} manifest(s)")
    typer.echo(f"   Valid: {result.manifests_valid}/{result.manifests_found}")

    if result.warnings:
        typer.echo("\n⚠️  Warnings:")
        for w in result.warnings:
            typer.echo(f"   {w.path}: {w.message}")

    if result.errors:
        typer.echo("\n❌ Errors:")
        for e in result.errors:
            typer.echo(f"   {e.path}: {e.message}")

    # Determine exit status
    has_failures = len(result.errors) > 0 or (strict and len(result.warnings) > 0)

    if has_failures:
        typer.echo("\n❌ Validation failed")
        raise typer.Exit(1)
    else:
        typer.echo("\n✅ All manifests valid")

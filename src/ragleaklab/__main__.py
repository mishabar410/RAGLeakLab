"""CLI entry point for ragleaklab."""

from pathlib import Path
from typing import Any

import typer

app = typer.Typer(
    name="ragleaklab",
    help="RAGLeakLab - MVP security testing framework for RAG systems",
    add_completion=False,
)


@app.command()
def run(
    corpus: Path = typer.Option(None, "--corpus", "-c", help="Path to corpus directory"),
    attacks: Path = typer.Option(
        None, "--attacks", "-a", help="Path to attacks YAML file or directory"
    ),
    out: Path = typer.Option(..., "--out", "-o", help="Output directory for reports"),
    config: Path = typer.Option(
        None, "--config", help="Path to YAML config file (alternative to --corpus/--attacks)"
    ),
    pack: list[str] = typer.Option(
        [],
        "--pack",
        "-p",
        help="Built-in attack pack: canary-basic, verbatim-basic, membership-basic",
    ),
    format: list[str] = typer.Option(
        [], "--format", "-f", help="Additional output formats: junit, sarif"
    ),
    minimize_on_fail: bool = typer.Option(
        False, "--minimize-on-fail", help="Minimize failing queries for stable regression"
    ),
    cache: bool = typer.Option(
        False, "--cache", help="Enable disk cache for deterministic runs"
    ),
) -> None:
    """Run attack test cases against a corpus and generate reports.

    Use either --config for full configuration, --pack for built-in packs, or --corpus/--attacks for custom mode.
    """
    from ragleaklab.attacks import load_cases, run_all, run_all_with_target
    from ragleaklab.corpus import load_corpus
    from ragleaklab.metrics import (
        apply_thresholds,
        detect_canary,
        membership_confidence,
        verbatim_overlap,
    )
    from ragleaklab.rag import Document, RAGPipeline
    from ragleaklab.reporting.schema import CaseResult, FailureReason, Report

    # Load pack cases if specified
    pack_cases = []
    if pack:
        from ragleaklab.packs import get_pack_path, get_pack_version

        typer.echo(f"📦 Loading packs (version {get_pack_version()}):")
        for pack_name in pack:
            try:
                pack_path = get_pack_path(pack_name)
                cases = load_cases(pack_path)
                pack_cases.extend(cases)
                typer.echo(f"   {pack_name}: {len(cases)} cases")
            except ValueError as e:
                typer.echo(f"❌ {e}", err=True)
                raise typer.Exit(1) from None

    # Determine mode: config file or CLI args
    if config is not None:
        from ragleaklab.config import HttpTargetConfig, load_config

        if not config.exists():
            typer.echo(f"❌ Config file not found: {config}", err=True)
            raise typer.Exit(1)

        cfg = load_config(config)

        # Get paths from config
        if cfg.corpus is None:
            typer.echo("❌ Config missing 'corpus.path'", err=True)
            raise typer.Exit(1)
        # attacks can be None if using packs
        if cfg.attacks is None and not pack_cases:
            typer.echo("❌ Config missing 'attacks.path' (or use --pack)", err=True)
            raise typer.Exit(1)

        corpus_path = Path(cfg.corpus.path)
        attacks_path = Path(cfg.attacks.path) if cfg.attacks else None
        use_http_target = isinstance(cfg.target, HttpTargetConfig)
    else:
        # CLI args mode
        if corpus is None:
            typer.echo("❌ --corpus required", err=True)
            raise typer.Exit(1)
        if attacks is None and not pack_cases:
            typer.echo("❌ --attacks or --pack required", err=True)
            raise typer.Exit(1)
        corpus_path = corpus
        attacks_path = attacks if attacks else None
        use_http_target = False
        cfg = None

    # Validate inputs
    if not corpus_path.exists():
        typer.echo(f"❌ Corpus path not found: {corpus_path}", err=True)
        raise typer.Exit(1)

    if attacks_path is not None and not attacks_path.exists():
        typer.echo(f"❌ Attacks path not found: {attacks_path}", err=True)
        raise typer.Exit(1)

    # Create output directory
    out.mkdir(parents=True, exist_ok=True)

    # Load corpus
    typer.echo(f"📁 Loading corpus from: {corpus_path}")
    corpus_docs = load_corpus(corpus_path)
    rag_docs = [Document(doc_id=d.doc_id, text=d.text) for d in corpus_docs]
    typer.echo(f"   Loaded {len(corpus_docs)} documents")

    # Build sources for verbatim check
    sources = [(d.doc_id, d.text) for d in corpus_docs]

    # Load attack cases (pack + custom)
    cases = list(pack_cases)  # Start with pack cases
    if attacks_path is not None:
        typer.echo(f"🎯 Loading attacks from: {attacks_path}")
        custom_cases = load_cases(attacks_path)
        cases.extend(custom_cases)
        typer.echo(f"   Loaded {len(custom_cases)} custom test cases")
    typer.echo(f"   Total: {len(cases)} test cases")

    # Run attacks
    typer.echo("⚡ Running attacks...")

    # Compute provenance hashes
    from ragleaklab.assets.hash import compute_tree_hash
    from ragleaklab.core.contracts import Hashes
    from ragleaklab.core.version import compute_config_hash, get_tool_version

    tool_version = get_tool_version()
    corpus_hash = compute_tree_hash(corpus_path)
    attacks_hash_val = compute_tree_hash(attacks_path) if attacks_path else None
    config_hash = compute_config_hash(
        corpus_path=str(corpus_path.resolve()),
        attacks_path=str(attacks_path.resolve()) if attacks_path else "packs",
        packs=",".join(sorted(pack)) if pack else "",
    )

    run_hashes = Hashes(
        corpus_hash=corpus_hash,
        attacks_hash=attacks_hash_val,
        config_hash=config_hash,
        target_hash="http" if use_http_target else "in-process",
    )

    # Setup cache if enabled
    disk_cache = None
    if cache:
        from ragleaklab.core.cache import DiskCache

        cache_dir = out / ".ragleaklab_cache"
        disk_cache = DiskCache(cache_dir)
        typer.echo(f"💾 Cache enabled: {cache_dir}")

    if use_http_target and cfg is not None:
        from ragleaklab.targets import HttpTarget

        target = HttpTarget.from_config(cfg.target)  # type: ignore
        artifacts = run_all_with_target(target, cases, hashes=run_hashes, cache=disk_cache)
    else:
        # Create in-process pipeline
        pipeline = RAGPipeline(top_k=3)
        pipeline.add_documents(rag_docs)
        artifacts = run_all(pipeline, cases, hashes=run_hashes, cache=disk_cache)

    # Calculate metrics per case
    case_results: list[CaseResult] = []
    total_canary_count = 0
    total_verbatim_score = 0.0

    for artifact in artifacts:
        # Canary detection
        canary_result = detect_canary(artifact.answer)
        total_canary_count += canary_result.count

        # Verbatim overlap
        verbatim_result = verbatim_overlap(artifact.answer, sources)
        total_verbatim_score += verbatim_result.score

        # Build case details
        case_details: dict[str, Any] = {}

        # Minimize failing queries if requested
        if minimize_on_fail and canary_result.present:
            from ragleaklab.attacks import minimize_query

            original_query = artifact.meta.get("original_query", artifact.query)

            # Create oracle that checks if leak persists
            def make_oracle(pipe: RAGPipeline | None, tgt: Any) -> Any:
                def oracle(q: str) -> bool:
                    if pipe is not None:
                        result = pipe.query(q)
                        return detect_canary(result.answer).present
                    else:
                        resp = tgt.ask(q)
                        return detect_canary(resp.answer).present

                return oracle

            if use_http_target and cfg is not None:
                oracle_fn = make_oracle(None, target)
            else:
                oracle_fn = make_oracle(pipeline, None)

            min_result = minimize_query(original_query, oracle_fn)
            case_details["minimized_query"] = min_result.minimized_query
            case_details["minimization"] = {
                "original_chunks": min_result.original_chunks,
                "minimized_chunks": min_result.minimized_chunks,
                "iterations": min_result.iterations,
                "reduced": min_result.reduced,
            }

        # Compute attribution for leaks
        attribution_list: list[dict[str, Any]] = []
        if canary_result.present or verbatim_result.score > 0.1:
            from ragleaklab.analysis.attribution import attribute_leak

            attrs = attribute_leak(
                canary_detected=canary_result.present,
                retrieved_ids=artifact.retrieved_ids,
                context_chars=artifact.context_stats.context_chars,
                n_chunks=artifact.context_stats.n_chunks,
                verbatim_score=verbatim_result.score,
                is_http_target=use_http_target,
            )
            attribution_list = [a.model_dump() for a in attrs]

        case_results.append(
            CaseResult(
                test_id=artifact.test_id,
                threat=artifact.threat,
                query=artifact.meta.get("original_query", artifact.query),
                transformed_query=artifact.query,
                retrieved_ids=artifact.retrieved_ids,
                answer=artifact.answer,
                context=artifact.context,
                timings=artifact.timings.model_dump(),
                context_stats=artifact.context_stats.model_dump(),
                hashes=artifact.hashes.model_dump(),
                attribution=attribution_list,
                canary_detected=canary_result.present,
                canary_count=canary_result.count,
                verbatim_score=verbatim_result.score,
                details=case_details,
            )
        )

    # Calculate aggregates
    canary_extracted = total_canary_count > 0
    avg_verbatim = total_verbatim_score / len(cases) if cases else 0.0

    # Membership confidence (using all artifacts)
    membership_result = membership_confidence(artifacts)

    # Overall verdict
    from ragleaklab.metrics.canary import CanaryResult
    from ragleaklab.metrics.verbatim import VerbatimResult

    aggregate_canary = CanaryResult(present=canary_extracted, count=total_canary_count, matches=[])
    aggregate_verbatim = VerbatimResult(
        score=avg_verbatim,
        max_lcs_length=0,
        source_with_max_overlap=None,
        ngram_matches=0,
    )

    verdict = apply_thresholds(
        canary=aggregate_canary,
        verbatim=aggregate_verbatim,
        membership=membership_result,
    )

    # Build report
    failures = [
        FailureReason(
            threat=r.threat,
            reason=r.reason,
            value=r.value,
            threshold=r.threshold,
        )
        for r in verdict.reasons
    ]

    report = Report(
        tool_version=tool_version,
        total_cases=len(cases),
        canary_extracted=canary_extracted,
        canary_count=total_canary_count,
        verbatim_leakage_rate=avg_verbatim,
        membership_confidence=membership_result.score,
        overall_pass=verdict.status == "pass",
        failures=failures,
        corpus_path=str(corpus_path.resolve()),
        attacks_path=str(attacks_path.resolve()) if attacks_path else "built-in packs",
        config_hash=config_hash,
    )

    # Write report.json
    report_path = out / "report.json"
    with open(report_path, "w") as f:
        f.write(report.model_dump_json(indent=2))
    typer.echo(f"📄 Wrote {report_path}")

    # Write runs.jsonl with context truncation
    CONTEXT_LIMIT = 20_000
    runs_path = out / "runs.jsonl"
    with open(runs_path, "w") as f:
        for case_result in case_results:
            # Serialize with potential context truncation
            data = case_result.model_dump()
            context_field = data.get("context", "")
            if len(context_field) > CONTEXT_LIMIT:
                data["context"] = context_field[:CONTEXT_LIMIT]
                if "context_stats" in data:
                    data["context_stats"]["truncated"] = True
            import json

            f.write(json.dumps(data) + "\n")
    typer.echo(f"📄 Wrote {runs_path}")

    # Export additional formats
    for fmt in format:
        fmt_lower = fmt.lower()
        if fmt_lower == "junit":
            from ragleaklab.reporting import export_junit

            junit_path = out / "junit.xml"
            export_junit(report, case_results, junit_path)
            typer.echo(f"📄 Wrote {junit_path}")
        elif fmt_lower == "sarif":
            from ragleaklab.reporting import export_sarif

            sarif_path = out / "results.sarif"
            export_sarif(report, case_results, sarif_path)
            typer.echo(f"📄 Wrote {sarif_path}")
        else:
            typer.echo(f"⚠️  Unknown format: {fmt}", err=True)

    # Summary
    status_icon = "✅" if report.overall_pass else "❌"
    typer.echo(f"\n{status_icon} Overall: {'PASS' if report.overall_pass else 'FAIL'}")
    typer.echo(f"   Canary leaks: {total_canary_count}")
    typer.echo(f"   Verbatim rate: {avg_verbatim:.2%}")
    typer.echo(f"   Membership conf: {membership_result.score:.2%}")

    if not report.overall_pass:
        typer.echo("\n⚠️  Failures:")
        for failure in failures:
            typer.echo(f"   - [{failure.threat}] {failure.reason}")


@app.command()
def diff(
    baseline: Path = typer.Option(..., "--baseline", "-b", help="Path to baseline report.json"),
    current: Path = typer.Option(..., "--current", "-c", help="Path to current report.json"),
    verbatim_threshold: float = typer.Option(
        0.01, "--verbatim-threshold", help="Max allowed increase in verbatim rate"
    ),
    membership_threshold: float = typer.Option(
        0.05, "--membership-threshold", help="Max allowed increase in membership confidence"
    ),
) -> None:
    """Compare current report against baseline for regressions."""
    import json

    from ragleaklab.regression.diff import compare_reports
    from ragleaklab.reporting.schema import Report

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

    baseline_report = Report(**baseline_data)
    current_report = Report(**current_data)

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


# Attacks subcommand
attacks_app = typer.Typer(help="Attack analysis utilities")
app.add_typer(attacks_app, name="attacks")


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

    from ragleaklab.attacks.coverage import compute_coverage, load_expectations_from_manifest

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


# Assets subcommand
assets_app = typer.Typer(help="Asset generation utilities")
app.add_typer(assets_app, name="assets")


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


@app.command()
def version() -> None:
    """Show version information."""
    from ragleaklab import __version__

    typer.echo(f"RAGLeakLab v{__version__}")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """RAGLeakLab - Security testing framework for RAG systems."""
    if ctx.invoked_subcommand is None:
        typer.echo("RAGLeakLab v0.1.0 - Security testing framework for RAG systems")
        typer.echo("Use --help for available commands.")


if __name__ == "__main__":
    app()

"""CLI entry point for ragleaklab."""

from pathlib import Path

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
) -> None:
    """Run attack test cases against a corpus and generate reports.

    Use either --config for full configuration, or --corpus/--attacks for simple mode.
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
        if cfg.attacks is None:
            typer.echo("❌ Config missing 'attacks.path'", err=True)
            raise typer.Exit(1)

        corpus_path = Path(cfg.corpus.path)
        attacks_path = Path(cfg.attacks.path)
        use_http_target = isinstance(cfg.target, HttpTargetConfig)
    else:
        # CLI args mode
        if corpus is None or attacks is None:
            typer.echo("❌ Either --config or both --corpus and --attacks required", err=True)
            raise typer.Exit(1)
        corpus_path = corpus
        attacks_path = attacks
        use_http_target = False
        cfg = None

    # Validate inputs
    if not corpus_path.exists():
        typer.echo(f"❌ Corpus path not found: {corpus_path}", err=True)
        raise typer.Exit(1)

    if not attacks_path.exists():
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

    # Load attack cases
    typer.echo(f"🎯 Loading attacks from: {attacks_path}")
    cases = load_cases(attacks_path)
    typer.echo(f"   Loaded {len(cases)} test cases")

    # Run attacks
    typer.echo("⚡ Running attacks...")

    if use_http_target and cfg is not None:
        from ragleaklab.targets import HttpTarget

        target = HttpTarget.from_config(cfg.target)  # type: ignore
        artifacts = run_all_with_target(target, cases)
    else:
        # Create in-process pipeline
        pipeline = RAGPipeline(top_k=3)
        pipeline.add_documents(rag_docs)
        artifacts = run_all(pipeline, cases)

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

        case_results.append(
            CaseResult(
                test_id=artifact.test_id,
                threat=artifact.threat,
                query=artifact.metadata.get("original_query", artifact.query),
                transformed_query=artifact.query,
                retrieved_ids=artifact.retrieved_ids,
                answer=artifact.answer,
                canary_detected=canary_result.present,
                canary_count=canary_result.count,
                verbatim_score=verbatim_result.score,
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
        total_cases=len(cases),
        canary_extracted=canary_extracted,
        canary_count=total_canary_count,
        verbatim_leakage_rate=avg_verbatim,
        membership_confidence=membership_result.score,
        overall_pass=verdict.status == "pass",
        failures=failures,
        corpus_path=str(corpus_path.resolve()),
        attacks_path=str(attacks_path.resolve()),
    )

    # Write report.json
    report_path = out / "report.json"
    with open(report_path, "w") as f:
        f.write(report.model_dump_json(indent=2))
    typer.echo(f"📄 Wrote {report_path}")

    # Write runs.jsonl
    runs_path = out / "runs.jsonl"
    with open(runs_path, "w") as f:
        for case_result in case_results:
            f.write(case_result.model_dump_json() + "\n")
    typer.echo(f"📄 Wrote {runs_path}")

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

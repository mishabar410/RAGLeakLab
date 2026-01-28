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
    corpus: Path = typer.Option(..., "--corpus", "-c", help="Path to corpus directory"),
    attacks: Path = typer.Option(
        ..., "--attacks", "-a", help="Path to attacks YAML file or directory"
    ),
    out: Path = typer.Option(..., "--out", "-o", help="Output directory for reports"),
) -> None:
    """Run attack test cases against a corpus and generate reports."""
    from ragleaklab.attacks import load_cases, run_all
    from ragleaklab.corpus import load_corpus
    from ragleaklab.metrics import (
        apply_thresholds,
        detect_canary,
        membership_confidence,
        verbatim_overlap,
    )
    from ragleaklab.rag import Document, RAGPipeline
    from ragleaklab.reporting.schema import CaseResult, FailureReason, Report

    # Validate inputs
    if not corpus.exists():
        typer.echo(f"❌ Corpus path not found: {corpus}", err=True)
        raise typer.Exit(1)

    if not attacks.exists():
        typer.echo(f"❌ Attacks path not found: {attacks}", err=True)
        raise typer.Exit(1)

    # Create output directory
    out.mkdir(parents=True, exist_ok=True)

    # Load corpus
    typer.echo(f"📁 Loading corpus from: {corpus}")
    corpus_docs = load_corpus(corpus)
    rag_docs = [Document(doc_id=d.doc_id, text=d.text) for d in corpus_docs]
    typer.echo(f"   Loaded {len(corpus_docs)} documents")

    # Build sources for verbatim check
    sources = [(d.doc_id, d.text) for d in corpus_docs]

    # Create pipeline
    pipeline = RAGPipeline(top_k=3)
    pipeline.add_documents(rag_docs)

    # Load attack cases
    typer.echo(f"🎯 Loading attacks from: {attacks}")
    cases = load_cases(attacks)
    typer.echo(f"   Loaded {len(cases)} test cases")

    # Run attacks
    typer.echo("⚡ Running attacks...")
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
        corpus_path=str(corpus.resolve()),
        attacks_path=str(attacks.resolve()),
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

"""Bench sub-commands — benchmark utilities."""

from datetime import UTC
from pathlib import Path

import typer

bench_app = typer.Typer(help="Benchmark utilities")


@bench_app.command("time")
def bench_time(
    pack: str = typer.Option(..., "--pack", "-p", help="Attack pack to benchmark"),
    runs: int = typer.Option(3, "--runs", "-r", help="Number of benchmark runs"),
    out: Path = typer.Option(..., "--out", "-o", help="Output JSON file path"),
    cache: bool = typer.Option(False, "--cache", help="Enable disk cache"),
    jobs: int = typer.Option(1, "--jobs", "-j", help="Parallel workers"),
) -> None:
    """Benchmark attack pack execution time.

    Measures total runtime, median per-case time, and cache hit rate.
    """
    import json
    import statistics
    import time
    from datetime import datetime

    from ragleaklab.attacks import load_cases, run_all
    from ragleaklab.corpus import load_corpus
    from ragleaklab.packs import get_pack_path
    from ragleaklab.rag import Document, RAGPipeline

    # Load pack
    try:
        pack_path = get_pack_path(pack)
        corpus_path = pack_path.parent / "corpus"  # Packs include their corpus
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from None

    # Find corpus - packs may have different structures
    if not corpus_path.exists():
        # Try data directory
        corpus_path = Path(__file__).parent.parent.parent.parent / "data" / "corpus_private_canary"
    if not corpus_path.exists():
        typer.echo(f"❌ Corpus not found for pack: {pack}", err=True)
        raise typer.Exit(1)

    typer.echo(f"🔬 Benchmarking pack: {pack}")
    typer.echo(f"   Runs: {runs}")
    typer.echo(f"   Jobs: {jobs}")
    typer.echo(f"   Cache: {'enabled' if cache else 'disabled'}")

    # Load corpus and cases
    cases = load_cases(pack_path)
    corpus_docs = load_corpus(corpus_path)
    rag_docs = [Document(doc_id=d.doc_id, text=d.text) for d in corpus_docs]

    typer.echo(f"   Cases: {len(cases)}")
    typer.echo(f"   Documents: {len(corpus_docs)}")

    # Setup cache if enabled
    disk_cache = None
    if cache:
        from ragleaklab.core.cache import DiskCache

        cache_dir = (
            out.parent / ".ragleaklab_bench_cache"
            if out.parent.exists()
            else Path(".ragleaklab_bench_cache")
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        disk_cache = DiskCache(cache_dir)

    # Create pipeline
    pipeline = RAGPipeline(top_k=3)
    pipeline.add_documents(rag_docs)

    # Run benchmarks
    run_times: list[float] = []
    per_case_times: list[float] = []
    total_cache_hits = 0
    total_cases_run = 0

    typer.echo("\n⏱️  Running benchmarks...")
    for run_idx in range(runs):
        start = time.perf_counter()
        artifacts = run_all(pipeline, cases, cache=disk_cache, jobs=jobs)
        elapsed = time.perf_counter() - start

        run_times.append(elapsed)
        per_case_times.append(elapsed / len(cases) if cases else 0)

        # Count cache hits
        for artifact in artifacts:
            total_cases_run += 1
            if artifact.meta.get("cache_hit", False):
                total_cache_hits += 1

        typer.echo(
            f"   Run {run_idx + 1}/{runs}: {elapsed:.3f}s ({elapsed / len(cases) * 1000:.1f}ms/case)"
        )

    # Calculate stats
    total_runtime = sum(run_times)
    median_per_case = statistics.median(per_case_times) if per_case_times else 0
    cache_hit_rate = total_cache_hits / total_cases_run if total_cases_run > 0 else 0

    # Build result
    result = {
        "pack": pack,
        "runs": runs,
        "cases_per_run": len(cases),
        "jobs": jobs,
        "cache_enabled": cache,
        "total_runtime_sec": round(total_runtime, 3),
        "run_times_sec": [round(t, 3) for t in run_times],
        "median_per_case_sec": round(median_per_case, 6),
        "median_per_case_ms": round(median_per_case * 1000, 2),
        "cache_hit_rate": round(cache_hit_rate, 4),
        "generated_at": datetime.now(UTC).isoformat(),
    }

    # Write output
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    typer.echo(f"\n📄 Wrote {out}")
    typer.echo("\n📊 Summary:")
    typer.echo(f"   Total runtime: {total_runtime:.3f}s")
    typer.echo(f"   Median per-case: {median_per_case * 1000:.2f}ms")
    typer.echo(f"   Cache hit rate: {cache_hit_rate:.1%}")


@bench_app.command("bundle")
def bench_bundle(
    bundle: Path = typer.Option(..., "--bundle", "-b", help="Path to bundle.yaml"),
    out: Path = typer.Option(..., "--out", "-o", help="Output directory"),
    limit_packs: int = typer.Option(None, "--limit-packs", help="Limit number of packs to run"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't run packs, just validate"),
) -> None:
    """Run a benchmark bundle and generate summary.

    Executes all packs defined in the bundle and produces:
    - Individual pack results in OUTDIR/<pack>/
    - Aggregated summary in OUTDIR/bench_summary.json
    - Human-readable report in OUTDIR/bench_summary.md
    """
    import json

    from ragleaklab.bench.bundle import (
        generate_summary_markdown,
        load_bundle,
        run_bundle,
    )

    # Validate bundle exists
    if not bundle.exists():
        typer.echo(f"❌ Bundle not found: {bundle}", err=True)
        raise typer.Exit(1)

    typer.echo("📦 RAGLeakLab Benchmark Bundle")
    typer.echo(f"   Bundle: {bundle}")
    typer.echo(f"   Output: {out}")

    # Load bundle
    try:
        manifest = load_bundle(bundle)
    except (FileNotFoundError, ValueError) as e:
        typer.echo(f"❌ Failed to load bundle: {e}", err=True)
        raise typer.Exit(1) from None

    typer.echo(f"   Name: {manifest.name} v{manifest.version}")
    typer.echo(f"   Packs: {len(manifest.packs)}")

    if limit_packs:
        typer.echo(f"   Limiting to: {limit_packs} packs")

    if dry_run:
        typer.echo("   Mode: dry-run (validation only)")

    typer.echo("")

    # Run bundle
    summary = run_bundle(manifest, out, limit_packs=limit_packs, dry_run=dry_run)

    # Write summary JSON
    summary_json_path = out / "bench_summary.json"
    with open(summary_json_path, "w") as f:
        json.dump(summary.model_dump(), f, indent=2)
    typer.echo(f"📄 Wrote {summary_json_path}")

    # Write summary markdown
    summary_md = generate_summary_markdown(summary)
    summary_md_path = out / "bench_summary.md"
    summary_md_path.write_text(summary_md)
    typer.echo(f"📄 Wrote {summary_md_path}")

    # Print summary
    typer.echo("\n📊 Results:")
    typer.echo(f"   Passed: {summary.passed_packs}/{summary.total_packs}")
    typer.echo(f"   Failed: {summary.failed_packs}")
    typer.echo(f"   Errors: {summary.error_packs}")
    typer.echo(f"   Risk Score: {summary.risk_score:.4f}")
    typer.echo(f"   Runtime: {summary.total_runtime_sec:.2f}s")

    # Exit code based on failures
    if summary.failed_packs > 0 or summary.error_packs > 0:
        typer.echo("\n❌ Benchmark failed")
        raise typer.Exit(1)
    else:
        typer.echo("\n✅ Benchmark passed")

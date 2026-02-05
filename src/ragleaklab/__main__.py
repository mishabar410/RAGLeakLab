"""CLI entry point for ragleaklab."""

from datetime import UTC
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
    poisoning_pack: list[str] = typer.Option(
        [],
        "--poisoning-pack",
        help="Built-in poisoning pack: integrity-dummy",
    ),
    format: list[str] = typer.Option(
        [], "--format", "-f", help="Additional output formats: junit, sarif"
    ),
    minimize_on_fail: bool = typer.Option(
        False, "--minimize-on-fail", help="Minimize failing queries for stable regression"
    ),
    cache: bool = typer.Option(False, "--cache", help="Enable disk cache for deterministic runs"),
    jobs: int = typer.Option(1, "--jobs", "-j", help="Parallel workers (default: 1)"),
    no_redact: bool = typer.Option(
        False, "--no-redact", help="Disable secret redaction (for local debug)"
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

    # Track poisoning packs for specialized post-attack evaluation
    poisoning_pack_names: list[str] = []
    poisoning_cases: list = []
    if poisoning_pack:
        from ragleaklab.poisoning.packs import (
            get_poisoning_pack_path,
            get_poisoning_pack_version,
        )
        from ragleaklab.poisoning.packs.runner import load_poisoning_cases

        typer.echo(f"🧪 Loading poisoning packs (version {get_poisoning_pack_version()}):")
        for pack_name in poisoning_pack:
            try:
                pack_path = get_poisoning_pack_path(pack_name)
                # Track the pack name for specialized evaluation later
                poisoning_pack_names.append(pack_name)

                # For yaml-based packs, load cases directly
                # Specialized packs use their own loaders
                if pack_name not in (
                    "relevance-hijack",
                    "claim-corruption",
                    "sentinel-takeover-safe",
                ):
                    pcases = load_poisoning_cases(pack_path)
                    poisoning_cases.extend(pcases)
                    typer.echo(f"   {pack_name}: {len(pcases)} cases")
                else:
                    # Specialized packs are evaluated post-attack
                    typer.echo(f"   {pack_name}: specialized pack (evaluated post-attack)")
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
        # Allow --poisoning-pack without --attacks or --pack
        if attacks is None and not pack_cases and not poisoning_pack_names:
            typer.echo("❌ --attacks, --pack, or --poisoning-pack required", err=True)
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

    # Validate and create output directory
    from ragleaklab.core.fs import atomic_write

    try:
        # Ensure output path doesn't escape current directory
        cwd = Path.cwd()
        out_resolved = out.resolve()
        # Allow absolute paths but warn if they escape cwd
        if not str(out_resolved).startswith(str(cwd)):
            typer.echo(f"⚠️  Output directory outside project: {out_resolved}", err=True)
    except Exception:
        pass  # Allow if resolution fails

    out.mkdir(parents=True, exist_ok=True)

    # Load corpus (supports .txt and .jsonl files)
    typer.echo(f"📁 Loading corpus from: {corpus_path}")
    corpus_docs = load_corpus(corpus_path, extensions=(".txt", ".jsonl"))
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

    # Inject specialized pack queries into attack pipeline
    for pack_name in poisoning_pack_names:
        if pack_name == "relevance-hijack":
            from ragleaklab.poisoning.packs import get_poisoning_pack_path
            from ragleaklab.poisoning.packs.relevance_hijack import (
                load_relevance_hijack_pack,
                pack_to_test_cases,
            )

            pack_path = get_poisoning_pack_path(pack_name)
            rh_pack = load_relevance_hijack_pack(pack_path)
            pack_test_cases = pack_to_test_cases(rh_pack)
            cases.extend(pack_test_cases)
            typer.echo(f"   Injected {len(pack_test_cases)} queries from {pack_name}")

        elif pack_name == "sentinel-takeover-safe":
            from ragleaklab.poisoning.packs import get_poisoning_pack_path
            from ragleaklab.poisoning.packs.sentinel_takeover_safe import (
                load_sentinel_pack,
                pack_to_test_cases,
            )

            pack_path = get_poisoning_pack_path(pack_name)
            st_pack = load_sentinel_pack(pack_path)
            pack_test_cases = pack_to_test_cases(st_pack)
            cases.extend(pack_test_cases)
            typer.echo(f"   Injected {len(pack_test_cases)} queries from {pack_name}")

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
        artifacts = run_all_with_target(
            target, cases, hashes=run_hashes, cache=disk_cache, jobs=jobs
        )
    else:
        # Create in-process pipeline
        pipeline = RAGPipeline(top_k=3)
        pipeline.add_documents(rag_docs)
        artifacts = run_all(pipeline, cases, hashes=run_hashes, cache=disk_cache, jobs=jobs)

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

    # Run poisoning packs if specified
    integrity_section = None
    if poisoning_pack_names:
        from ragleaklab.poisoning.evidence import IntegritySection, IntegritySummary
        from ragleaklab.poisoning.packs import get_poisoning_pack_path

        typer.echo("🧪 Evaluating integrity...")

        # Collect all integrity evidence from different pack types
        all_packs: list[Any] = []
        total_findings = 0

        for pack_name in poisoning_pack_names:
            pack_path = get_poisoning_pack_path(pack_name)

            if pack_name == "relevance-hijack":
                # Use specialized relevance hijack evaluator
                from ragleaklab.poisoning.packs.relevance_hijack import (
                    load_relevance_hijack_pack,
                    run_relevance_hijack_from_artifacts,
                )

                rh_pack = load_relevance_hijack_pack(pack_path)
                rh_result = run_relevance_hijack_from_artifacts(rh_pack, artifacts)
                section = rh_result.to_integrity_section()
                all_packs.extend(section.packs)
                total_findings += len([e for e in section.packs if e])
                typer.echo(f"   {pack_name}: {len(rh_result.query_results)} queries evaluated")

            elif pack_name == "claim-corruption":
                # Use specialized claim corruption evaluator
                # Note: requires clean and poisoned results - for now just report capability
                typer.echo(f"   {pack_name}: requires two-phase evaluation (not yet in CLI)")

            elif pack_name == "sentinel-takeover-safe":
                # Use specialized sentinel evaluator
                from ragleaklab.poisoning.packs.sentinel_takeover_safe import (
                    load_sentinel_pack,
                    run_sentinel_from_artifacts,
                )

                st_pack = load_sentinel_pack(pack_path)
                st_result = run_sentinel_from_artifacts(st_pack, artifacts)
                section = st_result.to_integrity_section()
                all_packs.extend(section.packs)
                total_findings += len([e for e in section.packs if e])
                typer.echo(
                    f"   {pack_name}: {len(st_result.query_results)} queries, "
                    f"block_rate={st_result.block_rate:.1%}, leak_rate={st_result.leak_rate:.1%}"
                )

            else:
                # Use generic YAML-based runner for other packs
                from ragleaklab.poisoning.packs.runner import (
                    load_poisoning_cases,
                    run_poisoning_pack,
                )

                pcases = load_poisoning_cases(pack_path)
                if pcases:
                    section = run_poisoning_pack(pcases, artifacts)
                    all_packs.extend(section.packs)
                    total_findings += len(section.packs)
                    typer.echo(f"   {pack_name}: {len(pcases)} cases evaluated")

        # Build combined integrity section
        if all_packs:
            integrity_section = IntegritySection(
                packs=all_packs,
                summary=IntegritySummary(
                    total_findings=total_findings,
                    retrieval_poisoned=any(hasattr(p, "top_k_doc_ids") for p in all_packs if p),
                    claim_injected=any(hasattr(p, "matched_poison_claims") for p in all_packs if p),
                    sentinel_triggered=any(hasattr(p, "triggered") for p in all_packs if p),
                ),
            )
            if total_findings > 0:
                typer.echo(f"   Found {total_findings} integrity violations")
            else:
                typer.echo("   No integrity violations detected")
        else:
            typer.echo("   No integrity evidence generated")

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
        integrity=integrity_section.model_dump() if integrity_section else None,
    )

    # Write report.json
    import json

    from ragleaklab.core.redact import redact_dict

    report_path = out / "report.json"
    report_data = report.model_dump()
    if not no_redact:
        report_data = redact_dict(report_data)
    atomic_write(report_path, json.dumps(report_data, indent=2))
    typer.echo(f"📄 Wrote {report_path}")

    # Write runs.jsonl with context truncation
    CONTEXT_LIMIT = 20_000
    runs_path = out / "runs.jsonl"
    lines = []
    for case_result in case_results:
        # Serialize with potential context truncation
        data = case_result.model_dump()
        context_field = data.get("context", "")
        if len(context_field) > CONTEXT_LIMIT:
            data["context"] = context_field[:CONTEXT_LIMIT]
            if "context_stats" in data:
                data["context_stats"]["truncated"] = True
        # Apply redaction unless disabled
        if not no_redact:
            data = redact_dict(data)
        lines.append(json.dumps(data))
    atomic_write(runs_path, "\n".join(lines) + "\n" if lines else "")
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


@app.command()
def bench(
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
        corpus_path = Path(__file__).parent.parent.parent / "data" / "corpus_private_canary"
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


# Verify subcommand
verify_app = typer.Typer(help="Verification utilities")
app.add_typer(verify_app, name="verify")


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


# Report subcommand
report_app = typer.Typer(help="Report analysis utilities")
app.add_typer(report_app, name="report")


@report_app.command("summarize")
def report_summarize(
    input_dir: Path = typer.Option(
        ..., "--in", "-i", help="Input directory containing report.json and runs.jsonl"
    ),
    top: int = typer.Option(20, "--top", "-n", help="Number of top findings to show"),
    format_type: str = typer.Option("text", "--format", "-f", help="Output format: text or md"),
) -> None:
    """Summarize findings from a report for triage.

    Reads report.json and runs.jsonl to produce a findings-first summary
    showing what leaked, why, and how to fix it.
    """
    import json

    from ragleaklab.analysis.attribution import REMEDIATION_HINTS, AttributionCategory

    # Validate input directory
    if not input_dir.exists():
        typer.echo(f"❌ Input directory not found: {input_dir}", err=True)
        raise typer.Exit(1)

    report_path = input_dir / "report.json"
    runs_path = input_dir / "runs.jsonl"

    if not report_path.exists():
        typer.echo(f"❌ report.json not found in: {input_dir}", err=True)
        raise typer.Exit(1)

    # Load report
    with open(report_path) as f:
        report = json.load(f)

    # Load runs if available
    runs: list[dict] = []
    if runs_path.exists():
        with open(runs_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    runs.append(json.loads(line))

    # Determine output format
    is_markdown = format_type.lower() == "md"

    # Helper for formatting
    def heading(text: str, level: int = 1) -> str:
        if is_markdown:
            return "#" * level + " " + text
        return text

    def bold(text: str) -> str:
        if is_markdown:
            return f"**{text}**"
        return text

    def code(text: str) -> str:
        if is_markdown:
            return f"`{text}`"
        return text

    def truncate(text: str, max_len: int = 80) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    # Build output
    lines: list[str] = []

    # Overall status
    overall_pass = report.get("overall_pass", True)
    status_icon = "✅" if overall_pass else "❌"
    status_text = "PASS" if overall_pass else "FAIL"

    lines.append(heading("RAGLeakLab Findings Summary"))
    lines.append("")
    lines.append(f"{status_icon} {bold('Overall Status:')} {status_text}")
    lines.append("")

    # Key metrics
    lines.append(heading("Metrics", 2))
    lines.append(f"- Total cases: {report.get('total_cases', 0)}")
    lines.append(f"- Canary extracted: {report.get('canary_extracted', False)}")
    lines.append(f"- Canary count: {report.get('canary_count', 0)}")
    lines.append(f"- Verbatim leakage rate: {report.get('verbatim_leakage_rate', 0):.2%}")
    lines.append(f"- Membership confidence: {report.get('membership_confidence', 0):.2%}")
    lines.append("")

    # Report-level failures
    failures = report.get("failures", [])
    if failures:
        lines.append(heading("Threshold Violations", 2))
        for f in failures:
            lines.append(f"- [{f.get('threat', 'unknown')}] {f.get('reason', 'No reason')}")
        lines.append("")

    # Collect findings from runs
    findings: list[dict] = []
    for run in runs:
        # Check if this run has a leak
        canary_detected = run.get("canary_detected", False)
        verbatim_score = run.get("verbatim_score", 0.0)
        has_leak = canary_detected or verbatim_score > 0.1

        if has_leak:
            findings.append(run)

    # Sort findings by severity (canary first, then by verbatim score)
    findings.sort(key=lambda x: (not x.get("canary_detected", False), -x.get("verbatim_score", 0)))

    # Limit to top N
    top_findings = findings[:top]

    if top_findings:
        lines.append(heading(f"Top {len(top_findings)} Findings", 2))
        lines.append("")

        for idx, finding in enumerate(top_findings, 1):
            test_id = finding.get("test_id", "unknown")
            threat = finding.get("threat", "unknown")
            canary_detected = finding.get("canary_detected", False)
            verbatim_score = finding.get("verbatim_score", 0.0)
            answer = finding.get("answer", "")

            # Build evidence summary
            if canary_detected:
                evidence_type = "Canary token extracted"
                evidence_detail = f"count={finding.get('canary_count', 0)}"
            else:
                evidence_type = "Verbatim leakage"
                evidence_detail = f"score={verbatim_score:.2%}"

            # Get attribution
            attributions = finding.get("attribution", [])
            attr_categories: list[str] = []
            hints: list[str] = []
            for attr in attributions:
                cat = attr.get("category", "")
                attr_categories.append(cat)
                hint = attr.get("hint", "")
                if hint:
                    hints.append(hint)

            # If no attribution, try to infer
            if not attr_categories:
                if canary_detected:
                    attr_categories.append("retrieval_included_secret")
                    hints.append(
                        REMEDIATION_HINTS.get(AttributionCategory.RETRIEVAL_INCLUDED_SECRET, "")
                    )
                elif verbatim_score > 0.1:
                    attr_categories.append("high_verbatim_overlap")
                    hints.append("Review which documents are being retrieved.")

            # Format finding
            if is_markdown:
                lines.append(f"### {idx}. {code(test_id)}")
                lines.append("")
                lines.append(f"- {bold('Threat:')} {threat}")
                lines.append(f"- {bold('Evidence:')} {evidence_type} ({evidence_detail})")
                if attr_categories:
                    lines.append(f"- {bold('Attribution:')} {', '.join(attr_categories)}")
                if hints:
                    lines.append(f"- {bold('Remediation:')} {hints[0]}")
                lines.append(f"- {bold('Answer (truncated):')} {truncate(answer, 100)}")
                lines.append("")
            else:
                lines.append(f"{idx}. [{test_id}]")
                lines.append(f"   Threat: {threat}")
                lines.append(f"   Evidence: {evidence_type} ({evidence_detail})")
                if attr_categories:
                    lines.append(f"   Attribution: {', '.join(attr_categories)}")
                if hints:
                    lines.append(f"   Remediation: {hints[0]}")
                lines.append(f"   Answer: {truncate(answer, 100)}")
                lines.append("")
    else:
        lines.append(heading("Findings", 2))
        lines.append("No individual findings with leaks detected in runs.jsonl.")
        lines.append("")

    # Integrity section (corpus poisoning detection)
    if "integrity" in report:
        integrity = report["integrity"]
        summary = integrity.get("integrity_summary", {})
        packs = integrity.get("packs", [])

        if summary.get("total_findings", 0) > 0:
            lines.append(heading("Integrity Findings", 2))
            lines.append("")

            # Summary stats
            lines.append(f"- Total integrity findings: {summary.get('total_findings', 0)}")
            lines.append(f"- High severity: {summary.get('high_severity', 0)}")
            lines.append(f"- Medium severity: {summary.get('medium_severity', 0)}")
            lines.append(f"- Low severity: {summary.get('low_severity', 0)}")
            lines.append("")

            # Sort packs deterministically: severity → pack_id → query_id
            severity_order = {"high": 0, "medium": 1, "low": 2}
            sorted_packs = sorted(
                packs,
                key=lambda e: (
                    severity_order.get(e.get("severity", "low"), 99),
                    e.get("pack_id", ""),
                    e.get("query_id", ""),
                ),
            )

            # Show top findings
            for idx, evidence in enumerate(sorted_packs[:top], 1):
                pack_id = evidence.get("pack_id", "unknown")
                query_id = evidence.get("query_id", "unknown")
                severity = evidence.get("severity", "unknown")

                # Determine evidence type
                if "expected_doc_ids" in evidence:
                    evidence_type = "Retrieval Poisoning"
                    evidence_detail = f"confidence={evidence.get('confidence', 0):.2f}"
                elif "expected_claim" in evidence:
                    evidence_type = "Claim Poisoning"
                    evidence_detail = (
                        f"semantic_distance={evidence.get('semantic_distance', 0):.2f}"
                    )
                elif "sentinel_type" in evidence:
                    evidence_type = "Sentinel Trigger"
                    evidence_detail = f"type={evidence.get('sentinel_type', 'unknown')}"
                else:
                    evidence_type = "Unknown"
                    evidence_detail = ""

                if is_markdown:
                    lines.append(f"### {idx}. {code(pack_id)}:{code(query_id)}")
                    lines.append("")
                    lines.append(f"- {bold('Severity:')} {severity}")
                    lines.append(f"- {bold('Type:')} {evidence_type}")
                    if evidence_detail:
                        lines.append(f"- {bold('Details:')} {evidence_detail}")
                    lines.append("")
                else:
                    lines.append(f"{idx}. [{pack_id}:{query_id}]")
                    lines.append(f"   Severity: {severity}")
                    lines.append(f"   Type: {evidence_type}")
                    if evidence_detail:
                        lines.append(f"   Details: {evidence_detail}")
                    lines.append("")

    # Next steps
    if not overall_pass:
        lines.append(heading("Next Steps", 2))
        if is_markdown:
            lines.append("1. Review the findings above to understand what leaked")
            lines.append("2. Check the attribution categories for root causes")
            lines.append("3. Apply remediations to fix the underlying issues")
            lines.append("4. Re-run the pack to verify: `ragleaklab run --pack <pack> ...`")
            lines.append("5. See `docs/TRIAGE.md` for detailed guidance")
        else:
            lines.append("1. Review the findings above to understand what leaked")
            lines.append("2. Check the attribution categories for root causes")
            lines.append("3. Apply remediations to fix the underlying issues")
            lines.append("4. Re-run the pack to verify")
            lines.append("5. See docs/TRIAGE.md for detailed guidance")
        lines.append("")

    # Output
    output = "\n".join(lines)
    typer.echo(output)


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

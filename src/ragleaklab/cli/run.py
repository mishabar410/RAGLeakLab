"""Run command — execute attack test cases against a corpus."""

from pathlib import Path
from typing import Any

import typer


def register(app: typer.Typer) -> None:
    """Register run command on the root app."""

    @app.command()
    def run(
        corpus: Path = typer.Option(None, "--corpus", "-c", help="Path to corpus directory"),
        attacks: Path = typer.Option(
            None, "--attacks", "-a", help="Path to attacks YAML file or directory"
        ),
        out: Path = typer.Option(..., "--out", "-o", help="Output directory for reports"),
        config: Path = typer.Option(
            None,
            "--config",
            help="Path to YAML config file (alternative to --corpus/--attacks)",
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
            False,
            "--minimize-on-fail",
            help="Minimize failing queries for stable regression",
        ),
        cache: bool = typer.Option(
            False, "--cache", help="Enable disk cache for deterministic runs"
        ),
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
            from ragleaklab.config.load import ConfigError

            if not config.exists():
                typer.echo(f"❌ Config file not found: {config}", err=True)
                raise typer.Exit(1)

            try:
                cfg = load_config(config)
            except ConfigError as exc:
                typer.echo(str(exc), err=True)
                raise typer.Exit(1) from None

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
                typer.echo(
                    f"⚠️  Output directory outside project: {out_resolved}",
                    err=True,
                )
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

        aggregate_canary = CanaryResult(
            present=canary_extracted, count=total_canary_count, matches=[]
        )
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
            from ragleaklab.poisoning.evidence import (
                IntegritySection,
                IntegritySummary,
            )
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
                        claim_injected=any(
                            hasattr(p, "matched_poison_claims") for p in all_packs if p
                        ),
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

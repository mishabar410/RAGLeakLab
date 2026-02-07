"""Delta sub-commands — delta ingestion gate."""

from pathlib import Path

import typer

delta_app = typer.Typer(help="Delta ingestion gate commands")


@delta_app.command("run")
def delta_run(
    pack: str = typer.Option(..., "--pack", "-p", help="Pack to run"),
    base_corpus: Path = typer.Option(
        ..., "--base-corpus", "-b", help="Path to base corpus directory"
    ),
    patch_dir: Path = typer.Option(..., "--patch", help="Path to patch directory"),
    out: Path = typer.Option(..., "--out", "-o", help="Output directory"),
) -> None:
    """Run pack before/after corpus patch and compare results.

    Creates base/, patched/ directories with run results, plus delta_report.json
    showing new findings and metric changes.
    """
    import json
    import subprocess

    from ragleaklab.corpus.patch import apply_patch

    if not base_corpus.exists():
        typer.echo(f"❌ Base corpus not found: {base_corpus}", err=True)
        raise typer.Exit(1)
    if not patch_dir.exists():
        typer.echo(f"❌ Patch directory not found: {patch_dir}", err=True)
        raise typer.Exit(1)

    typer.echo("🔄 Delta Ingestion Gate")
    typer.echo(f"   Pack: {pack}")
    typer.echo(f"   Base corpus: {base_corpus}")
    typer.echo(f"   Patch: {patch_dir}")
    typer.echo(f"   Output: {out}")

    out.mkdir(parents=True, exist_ok=True)
    base_out = out / "base"
    patched_out = out / "patched"
    patched_corpus_dir = out / "patched_corpus"

    # Step 1: Run pack on base corpus
    typer.echo("\n⚡ Step 1: Running pack on base corpus...")
    base_out.mkdir(parents=True, exist_ok=True)
    cmd_base = [
        "uv",
        "run",
        "ragleaklab",
        "run",
        "--corpus",
        str(base_corpus),
        "--pack",
        pack,
        "--out",
        str(base_out),
    ]
    result = subprocess.run(cmd_base, capture_output=True, text=True)
    if result.returncode != 0:
        typer.echo("❌ Base run failed:", err=True)
        typer.echo(result.stderr, err=True)
        raise typer.Exit(1)
    typer.echo("   ✓ Base run complete")

    # Step 2: Apply patch
    typer.echo("\n⚡ Step 2: Applying patch...")
    try:
        apply_patch(base_corpus, patch_dir, patched_corpus_dir)
    except (FileNotFoundError, ValueError) as e:
        typer.echo(f"❌ Patch failed: {e}", err=True)
        raise typer.Exit(1) from None

    base_docs = len(list(base_corpus.glob("*.txt")))
    patched_docs = len(list(patched_corpus_dir.glob("*.txt")))
    typer.echo(f"   ✓ Patch applied: {base_docs} → {patched_docs} docs")

    # Step 3: Run pack on patched corpus
    typer.echo("\n⚡ Step 3: Running pack on patched corpus...")
    patched_out.mkdir(parents=True, exist_ok=True)
    cmd_patched = [
        "uv",
        "run",
        "ragleaklab",
        "run",
        "--corpus",
        str(patched_corpus_dir),
        "--pack",
        pack,
        "--out",
        str(patched_out),
    ]
    result = subprocess.run(cmd_patched, capture_output=True, text=True)
    if result.returncode != 0:
        typer.echo("❌ Patched run failed:", err=True)
        typer.echo(result.stderr, err=True)
        raise typer.Exit(1)
    typer.echo("   ✓ Patched run complete")

    # Step 4: Compare results
    typer.echo("\n⚡ Step 4: Comparing results...")
    base_report_path = base_out / "report.json"
    patched_report_path = patched_out / "report.json"

    if not base_report_path.exists() or not patched_report_path.exists():
        typer.echo("❌ Missing report.json files", err=True)
        raise typer.Exit(1)

    with open(base_report_path) as f:
        base_report = json.load(f)
    with open(patched_report_path) as f:
        patched_report = json.load(f)

    base_failures = base_report.get("failures", [])
    patched_failures = patched_report.get("failures", [])
    base_failure_ids = {f.get("test_id") for f in base_failures if f.get("test_id")}
    patched_failure_ids = {f.get("test_id") for f in patched_failures if f.get("test_id")}

    new_finding_ids = patched_failure_ids - base_failure_ids
    resolved_finding_ids = base_failure_ids - patched_failure_ids

    new_findings_detail = []
    for failure in patched_failures:
        if failure.get("test_id") in new_finding_ids:
            finding: dict = {"type": "new_failure", "test_id": failure.get("test_id")}
            if "leaked_claims" in failure:
                finding["leaked_claims"] = failure["leaked_claims"]
            new_findings_detail.append(finding)

    # Compute metric deltas
    deltas = []
    base_summary = base_report.get("summary", {})
    patched_summary = patched_report.get("summary", {})

    for metric in ["pass_rate", "fail_rate", "total_cases"]:
        base_val = base_summary.get(metric)
        patched_val = patched_summary.get(metric)
        if base_val is not None and patched_val is not None:
            delta = None
            if isinstance(base_val, (int, float)) and isinstance(patched_val, (int, float)):
                delta = patched_val - base_val
            deltas.append(
                {
                    "metric": metric,
                    "baseline_value": base_val,
                    "current_value": patched_val,
                    "delta": delta,
                }
            )

    delta_report = {
        "status": "fail" if new_finding_ids else "pass",
        "base_corpus": str(base_corpus),
        "patch": str(patch_dir),
        "pack": pack,
        "summary": {
            "new_findings": len(new_finding_ids),
            "resolved_findings": len(resolved_finding_ids),
            "total_base": len(base_failure_ids),
            "total_patched": len(patched_failure_ids),
        },
        "new_findings": new_findings_detail,
        "resolved_findings": list(resolved_finding_ids),
        "deltas": deltas,
    }

    delta_report_path = out / "delta_report.json"
    with open(delta_report_path, "w") as f:
        json.dump(delta_report, f, indent=2)

    typer.echo(f"\n📄 Wrote {delta_report_path}")
    typer.echo("\n📊 Delta Summary:")
    typer.echo(f"   New findings: {len(new_finding_ids)}")
    typer.echo(f"   Resolved: {len(resolved_finding_ids)}")

    for d in deltas:
        if d["delta"] is not None and d["delta"] != 0:
            change = (
                f"({d['delta']:+.4f})" if isinstance(d["delta"], float) else f"({d['delta']:+d})"
            )
            typer.echo(f"   {d['metric']}: {d['baseline_value']} → {d['current_value']} {change}")

    if delta_report["status"] == "pass":
        typer.echo("\n✅ Delta gate passed - no new findings")
    else:
        typer.echo(f"\n❌ Delta gate failed - {len(new_finding_ids)} new findings")
        for finding in new_findings_detail[:5]:
            typer.echo(f"   - {finding.get('test_id', 'unknown')}")
        if len(new_finding_ids) > 5:
            typer.echo(f"   ... and {len(new_finding_ids) - 5} more")
        raise typer.Exit(1)

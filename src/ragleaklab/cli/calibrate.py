"""Calibrate command — calibrate pack thresholds on labeled test sets."""

from pathlib import Path

import typer


def register(app: typer.Typer) -> None:
    """Register calibrate command on the root app."""

    @app.command()
    def calibrate(
        pack: str = typer.Option(..., "--pack", "-p", help="Pack to calibrate"),
        out: Path = typer.Option(
            ..., "--out", "-o", help="Output directory for calibration report"
        ),
        labels: Path = typer.Option(
            None,
            "--labels",
            "-l",
            help="Path to labels.jsonl (default: data/calibration/<pack>/labels.jsonl)",
        ),
        target_fpr: float = typer.Option(0.01, "--target-fpr", help="Target false positive rate"),
        write_thresholds: bool = typer.Option(
            False, "--write-thresholds", help="Update pack manifest with new thresholds"
        ),
    ) -> None:
        """Calibrate pack thresholds on labeled test set.

        Runs the specified pack, extracts per-case scores, and finds the optimal
        threshold that achieves the target FPR (false positive rate).

        Labels format (JSONL):
            {"test_id": "...", "label": "positive"|"negative", "notes": "..."}
            - positive: attack succeeds (expect FAIL/leak)
            - negative: security holds (expect PASS/no-leak)
        """
        import json
        import tempfile

        from ragleaklab.calibration import fit_threshold, generate_report, load_labels
        from ragleaklab.calibration.report import write_report

        # Resolve pack path
        pack_path = None
        pack_type = None
        is_poisoning = False

        # Try poisoning packs first
        try:
            from ragleaklab.poisoning.packs import get_poisoning_pack_path

            pack_path = get_poisoning_pack_path(pack)
            is_poisoning = True

            manifest_path = pack_path / "manifest.yaml"
            if manifest_path.exists():
                import yaml

                with open(manifest_path) as f:
                    manifest = yaml.safe_load(f)
                    pack_type = manifest.get("pack_type", "retrieval")
        except ValueError:
            pass

        # Try regular packs
        if pack_path is None:
            try:
                from ragleaklab.packs import get_pack_path

                pack_path = get_pack_path(pack)
                pack_type = "leakage"
            except ValueError:
                typer.echo(f"❌ Pack not found: {pack}", err=True)
                raise typer.Exit(1) from None

        typer.echo(f"🎯 Calibrating pack: {pack}")
        typer.echo(f"   Pack path: {pack_path}")
        typer.echo(f"   Pack type: {pack_type}")
        typer.echo(f"   Target FPR: {target_fpr:.2%}")

        # Resolve labels path
        if labels is None:
            labels = Path("data/calibration") / pack.replace("-", "_") / "labels.jsonl"

        if not labels.exists():
            typer.echo(f"❌ Labels file not found: {labels}", err=True)
            typer.echo("   Create a labels.jsonl file with format:")
            typer.echo('   {"test_id": "...", "label": "positive"|"negative", "notes": "..."}')
            raise typer.Exit(1)

        typer.echo(f"   Labels: {labels}")

        try:
            label_map = load_labels(labels)
        except (ValueError, FileNotFoundError) as e:
            typer.echo(f"❌ Failed to load labels: {e}", err=True)
            raise typer.Exit(1) from None

        typer.echo(f"   Loaded {len(label_map)} labels")
        n_pos = sum(1 for v in label_map.values() if v == "positive")
        n_neg = sum(1 for v in label_map.values() if v == "negative")
        typer.echo(f"   Positive: {n_pos}, Negative: {n_neg}")

        # Run pack to get scores
        typer.echo("\n⚡ Running pack to collect scores...")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_out = Path(tmp_dir)
            import subprocess

            if is_poisoning:
                corpus_path = pack_path / "corpus"
                if not corpus_path.exists():
                    import yaml

                    manifest_path = pack_path / "manifest.yaml"
                    with open(manifest_path) as f:
                        manifest = yaml.safe_load(f)
                    corpus_cfg = manifest.get("corpus", {})
                    if "legit" in corpus_cfg:
                        corpus_path = pack_path / corpus_cfg["legit"]
                    elif "poison" in corpus_cfg:
                        corpus_path = pack_path / corpus_cfg["poison"]

                cmd = [
                    "uv",
                    "run",
                    "ragleaklab",
                    "run",
                    "--corpus",
                    str(corpus_path.parent if corpus_path.suffix == ".jsonl" else corpus_path),
                    "--poisoning-pack",
                    pack,
                    "--out",
                    str(tmp_out),
                ]
            else:
                cmd = [
                    "uv",
                    "run",
                    "ragleaklab",
                    "run",
                    "--pack",
                    pack,
                    "--out",
                    str(tmp_out),
                ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                typer.echo("❌ Pack run failed:", err=True)
                typer.echo(result.stderr, err=True)
                raise typer.Exit(1)

            runs_path = tmp_out / "runs.jsonl"
            report_path = tmp_out / "report.json"

            if not runs_path.exists():
                typer.echo(f"❌ runs.jsonl not found in {tmp_out}", err=True)
                raise typer.Exit(1)

            # Extract scores based on pack_type
            scores: list[tuple[str, float]] = []
            metric_name = "unknown"
            higher_is_worse = True

            if pack_type == "retrieval":
                metric_name = "poison_rate_at_k"
                if report_path.exists():
                    with open(report_path) as f:
                        report_data = json.load(f)
                    for pe in report_data.get("integrity", {}).get("packs", []):
                        if isinstance(pe, dict) and pe.get("query_id"):
                            scores.append((pe["query_id"], pe.get("poison_rate_at_k", 0.0)))

            elif pack_type == "sentinel":
                metric_name = "leak_rate"
                if report_path.exists():
                    with open(report_path) as f:
                        report_data = json.load(f)
                    for pe in report_data.get("integrity", {}).get("packs", []):
                        if isinstance(pe, dict) and pe.get("query_id"):
                            scores.append((pe["query_id"], 1.0 if pe.get("leak_detected") else 0.0))

            elif pack_type == "claim":
                metric_name = "poison_claim_rate"
                if report_path.exists():
                    with open(report_path) as f:
                        report_data = json.load(f)
                    for pe in report_data.get("integrity", {}).get("packs", []):
                        if isinstance(pe, dict) and pe.get("query_id"):
                            scores.append((pe["query_id"], pe.get("poison_claim_rate", 0.0)))

            else:
                metric_name = "verbatim_score"
                with open(runs_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        run = json.loads(line)
                        test_id = run.get("test_id", "")
                        if test_id:
                            scores.append((test_id, run.get("verbatim_score", 0.0)))

        if not scores:
            typer.echo("❌ No scores extracted from pack run", err=True)
            raise typer.Exit(1)

        typer.echo(f"\n📊 Extracted {len(scores)} scores for metric: {metric_name}")

        # Check label coverage
        score_ids = {tid for tid, _ in scores}
        label_ids = set(label_map.keys())
        matched = score_ids & label_ids
        missing_in_scores = label_ids - score_ids
        missing_in_labels = score_ids - label_ids

        if not matched:
            typer.echo("❌ No test_ids match between scores and labels", err=True)
            typer.echo(f"   Score IDs: {sorted(score_ids)[:5]}...")
            typer.echo(f"   Label IDs: {sorted(label_ids)[:5]}...")
            raise typer.Exit(1)

        if missing_in_scores:
            typer.echo(f"⚠️  Labels without scores: {sorted(missing_in_scores)[:5]}...")
        if missing_in_labels:
            typer.echo(f"⚠️  Scores without labels: {sorted(missing_in_labels)[:5]}...")

        typer.echo(f"   Matched: {len(matched)} test cases")

        # Fit threshold
        typer.echo("\n🔧 Fitting threshold...")
        calibration_result = fit_threshold(
            scores=scores,
            labels=label_map,
            target_fpr=target_fpr,
            higher_is_worse=higher_is_worse,
        )

        typer.echo(f"   Threshold: {calibration_result.threshold:.6f}")
        typer.echo(f"   Achieved FPR: {calibration_result.achieved_fpr:.2%}")
        typer.echo(f"   Achieved TPR: {calibration_result.achieved_tpr:.2%}")
        typer.echo(f"   Decision rule: {calibration_result.decision_rule}")

        report = generate_report(
            pack_name=pack,
            metric_name=metric_name,
            result=calibration_result,
            scores=scores,
            labels=label_map,
            target_fpr=target_fpr,
            higher_is_worse=higher_is_worse,
        )

        report_file = write_report(report, out)
        typer.echo(f"\n📄 Wrote {report_file}")

        if write_thresholds:
            typer.echo("\n⚠️  --write-thresholds not yet implemented")
            typer.echo("   Manual update required in pack manifest.yaml")

        typer.echo("\n✅ Calibration complete")

"""Report sub-commands — summarize and annotate findings."""

from pathlib import Path

import typer

report_app = typer.Typer(help="Report analysis utilities")


def _load_report_and_runs(input_dir: Path) -> tuple[dict, list[dict]]:
    """Load report.json and runs.jsonl from input directory."""
    import json

    if not input_dir.exists():
        typer.echo(f"❌ Input directory not found: {input_dir}", err=True)
        raise typer.Exit(1)

    report_path = input_dir / "report.json"
    if not report_path.exists():
        typer.echo(f"❌ report.json not found in: {input_dir}", err=True)
        raise typer.Exit(1)

    with open(report_path) as f:
        report = json.load(f)

    runs: list[dict] = []
    runs_path = input_dir / "runs.jsonl"
    if runs_path.exists():
        with open(runs_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    runs.append(json.loads(line))

    return report, runs


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
    from ragleaklab.analysis.attribution import REMEDIATION_HINTS, AttributionCategory

    report, runs = _load_report_and_runs(input_dir)

    is_markdown = format_type.lower() == "md"

    def heading(text: str, level: int = 1) -> str:
        return ("#" * level + " " + text) if is_markdown else text

    def bold(text: str) -> str:
        return f"**{text}**" if is_markdown else text

    def code(text: str) -> str:
        return f"`{text}`" if is_markdown else text

    def truncate(text: str, max_len: int = 80) -> str:
        return text if len(text) <= max_len else text[: max_len - 3] + "..."

    lines: list[str] = []

    overall_pass = report.get("overall_pass", True)
    status_icon = "✅" if overall_pass else "❌"
    status_text = "PASS" if overall_pass else "FAIL"

    lines.append(heading("RAGLeakLab Findings Summary"))
    lines.append("")
    lines.append(f"{status_icon} {bold('Overall Status:')} {status_text}")
    lines.append("")

    lines.append(heading("Metrics", 2))
    lines.append(f"- Total cases: {report.get('total_cases', 0)}")
    lines.append(f"- Canary extracted: {report.get('canary_extracted', False)}")
    lines.append(f"- Canary count: {report.get('canary_count', 0)}")
    lines.append(f"- Verbatim leakage rate: {report.get('verbatim_leakage_rate', 0):.2%}")
    lines.append(f"- Membership confidence: {report.get('membership_confidence', 0):.2%}")
    lines.append("")

    failures = report.get("failures", [])
    if failures:
        lines.append(heading("Threshold Violations", 2))
        for f in failures:
            lines.append(f"- [{f.get('threat', 'unknown')}] {f.get('reason', 'No reason')}")
        lines.append("")

    # Collect and sort findings from runs
    findings = [
        r for r in runs if r.get("canary_detected", False) or r.get("verbatim_score", 0.0) > 0.1
    ]
    findings.sort(key=lambda x: (not x.get("canary_detected", False), -x.get("verbatim_score", 0)))
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

            if canary_detected:
                evidence_type = "Canary token extracted"
                evidence_detail = f"count={finding.get('canary_count', 0)}"
            else:
                evidence_type = "Verbatim leakage"
                evidence_detail = f"score={verbatim_score:.2%}"

            attributions = finding.get("attribution", [])
            attr_categories = [a.get("category", "") for a in attributions]
            hints = [a.get("hint", "") for a in attributions if a.get("hint")]

            if not attr_categories:
                if canary_detected:
                    attr_categories.append("retrieval_included_secret")
                    hints.append(
                        REMEDIATION_HINTS.get(AttributionCategory.RETRIEVAL_INCLUDED_SECRET, "")
                    )
                elif verbatim_score > 0.1:
                    attr_categories.append("high_verbatim_overlap")
                    hints.append("Review which documents are being retrieved.")

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

    # Integrity section
    if "integrity" in report:
        integrity = report["integrity"]
        summary = integrity.get("integrity_summary", {})
        packs = integrity.get("packs", [])

        if summary.get("total_findings", 0) > 0:
            lines.append(heading("Integrity Findings", 2))
            lines.append("")
            lines.append(f"- Total integrity findings: {summary.get('total_findings', 0)}")
            lines.append(f"- High severity: {summary.get('high_severity', 0)}")
            lines.append(f"- Medium severity: {summary.get('medium_severity', 0)}")
            lines.append(f"- Low severity: {summary.get('low_severity', 0)}")
            lines.append("")

            severity_order = {"high": 0, "medium": 1, "low": 2}
            sorted_packs = sorted(
                packs,
                key=lambda e: (
                    severity_order.get(e.get("severity", "low"), 99),
                    e.get("pack_id", ""),
                    e.get("query_id", ""),
                ),
            )

            for idx, evidence in enumerate(sorted_packs[:top], 1):
                pack_id = evidence.get("pack_id", "unknown")
                query_id = evidence.get("query_id", "unknown")
                severity = evidence.get("severity", "unknown")

                if "expected_doc_ids" in evidence:
                    etype = "Retrieval Poisoning"
                    edetail = f"confidence={evidence.get('confidence', 0):.2f}"
                elif "expected_claim" in evidence:
                    etype = "Claim Poisoning"
                    edetail = f"semantic_distance={evidence.get('semantic_distance', 0):.2f}"
                elif "sentinel_type" in evidence:
                    etype = "Sentinel Trigger"
                    edetail = f"type={evidence.get('sentinel_type', 'unknown')}"
                else:
                    etype, edetail = "Unknown", ""

                if is_markdown:
                    lines.append(f"### {idx}. {code(pack_id)}:{code(query_id)}")
                    lines.append("")
                    lines.append(f"- {bold('Severity:')} {severity}")
                    lines.append(f"- {bold('Type:')} {etype}")
                    if edetail:
                        lines.append(f"- {bold('Details:')} {edetail}")
                    lines.append("")
                else:
                    lines.append(f"{idx}. [{pack_id}:{query_id}]")
                    lines.append(f"   Severity: {severity}")
                    lines.append(f"   Type: {etype}")
                    if edetail:
                        lines.append(f"   Details: {edetail}")
                    lines.append("")

    if not overall_pass:
        lines.append(heading("Next Steps", 2))
        lines.append("1. Review the findings above to understand what leaked")
        lines.append("2. Check the attribution categories for root causes")
        lines.append("3. Apply remediations to fix the underlying issues")
        if is_markdown:
            lines.append("4. Re-run the pack to verify: `ragleaklab run --pack <pack> ...`")
            lines.append("5. See `docs/TRIAGE.md` for detailed guidance")
        else:
            lines.append("4. Re-run the pack to verify")
            lines.append("5. See docs/TRIAGE.md for detailed guidance")
        lines.append("")

    typer.echo("\n".join(lines))


@report_app.command("annotate")
def report_annotate(
    input_dir: Path = typer.Option(
        ..., "--in", "-i", help="Input directory containing report.json"
    ),
    max_annotations: int = typer.Option(
        50, "--max", "-m", help="Maximum number of annotations to emit"
    ),
) -> None:
    """Emit GitHub Actions annotations for failures.

    Prints ::error:: and ::warning:: lines that GitHub Actions parses
    to create PR annotations and workflow summaries.

    Example:
        ::error title=Data Leak::Test xyz leaked claim "email@example.com"
    """
    report, runs = _load_report_and_runs(input_dir)

    failed_ids: set[str] = set()
    if "failures" in report:
        for fail in report["failures"]:
            test_id = fail.get("test_id") or fail.get("case_id", "unknown")
            failed_ids.add(test_id)

    def escape_msg(msg: str) -> str:
        return msg.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

    def truncate(text: str, max_len: int = 200) -> str:
        return text if len(text) <= max_len else text[: max_len - 3] + "..."

    annotation_count = 0

    for run in runs:
        if annotation_count >= max_annotations:
            break
        test_id = run.get("test_id", "unknown")
        if test_id not in failed_ids:
            continue

        evidence = run.get("evidence", {})
        answer = run.get("answer", "")
        canary = evidence.get("canary_detected", False)
        verbatim = evidence.get("verbatim_score", 0)
        membership = evidence.get("membership_confidence", 0)

        if canary:
            title = "Canary Token Leaked"
            msg = f"Test {test_id} leaked canary token in answer"
        elif verbatim > 0.1:
            title = "High Verbatim Overlap"
            msg = f"Test {test_id} has {verbatim:.0%} verbatim overlap"
        elif membership > 0.5:
            title = "Membership Inference"
            msg = f"Test {test_id} reveals corpus membership ({membership:.0%})"
        else:
            title = "Security Test Failed"
            msg = f"Test {test_id} failed"

        if answer:
            msg += f": {truncate(answer, 150)}"

        print(f"::error title={escape_msg(title)}::{escape_msg(msg)}")
        annotation_count += 1

    if "integrity" in report:
        for finding in report["integrity"].get("packs", []):
            if annotation_count >= max_annotations:
                break
            pack_id = finding.get("pack_id", "unknown")
            query_id = finding.get("query_id", "")
            severity = finding.get("severity", "medium")
            evidence_type = finding.get("evidence", {}).get("type", "unknown")

            title = f"Integrity: {pack_id}"
            msg = f"Query {query_id}: {evidence_type} ({severity})"
            level = "warning" if severity in ("low", "medium") else "error"
            print(f"::{level} title={escape_msg(title)}::{escape_msg(msg)}")
            annotation_count += 1

    if annotation_count > 0:
        total_failures = len(failed_ids)
        total_shown = min(annotation_count, total_failures)
        if total_failures > total_shown:
            print(
                f"::warning title=More Findings::"
                f"{total_failures - total_shown} additional findings not shown"
            )

    typer.echo(f"Emitted {annotation_count} annotations", err=True)

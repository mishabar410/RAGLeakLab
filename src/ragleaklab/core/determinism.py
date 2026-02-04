"""Determinism verification utilities.

Ensures RAGLeakLab produces identical outputs across runs by:
1. Normalizing volatile fields (timestamps, timings)
2. Sorting runs.jsonl by test_id
3. Deep comparison of normalized outputs
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Fields to strip from reports (volatile across runs)
VOLATILE_REPORT_FIELDS = {"generated_at"}

# Fields to strip from individual run entries
VOLATILE_RUN_FIELDS = {"timings"}


def normalize_report(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize report.json by stripping volatile fields.

    Args:
        data: Raw report dictionary

    Returns:
        Normalized dictionary with volatile fields removed
    """
    result = copy.deepcopy(data)

    for field in VOLATILE_REPORT_FIELDS:
        result.pop(field, None)

    return result


def normalize_run_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single runs.jsonl entry.

    Args:
        entry: Raw run entry dictionary

    Returns:
        Normalized dictionary with volatile fields removed
    """
    result = copy.deepcopy(entry)

    for field in VOLATILE_RUN_FIELDS:
        result.pop(field, None)

    return result


def normalize_runs(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize runs.jsonl entries.

    - Strips volatile fields (timings)
    - Sorts by test_id for stable comparison

    Args:
        lines: List of run entry dictionaries

    Returns:
        Sorted, normalized list
    """
    normalized = [normalize_run_entry(entry) for entry in lines]
    return sorted(normalized, key=lambda x: x.get("test_id", ""))


def load_report(path: Path) -> dict[str, Any]:
    """Load and parse report.json."""
    with open(path) as f:
        return json.load(f)


def load_runs(path: Path) -> list[dict[str, Any]]:
    """Load and parse runs.jsonl."""
    lines = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


def compare_normalized(
    data1: Any,
    data2: Any,
    path: str = "",
) -> list[str]:
    """Deep compare two normalized structures.

    Args:
        data1: First data structure
        data2: Second data structure
        path: Current path for error messages

    Returns:
        List of difference descriptions (empty = equal)
    """
    diffs: list[str] = []

    if type(data1) is not type(data2):
        diffs.append(f"{path}: type mismatch {type(data1).__name__} vs {type(data2).__name__}")
        return diffs

    if isinstance(data1, dict):
        keys1 = set(data1.keys())
        keys2 = set(data2.keys())

        for key in keys1 - keys2:
            diffs.append(f"{path}.{key}: missing in second")
        for key in keys2 - keys1:
            diffs.append(f"{path}.{key}: missing in first")

        for key in keys1 & keys2:
            sub_path = f"{path}.{key}" if path else key
            diffs.extend(compare_normalized(data1[key], data2[key], sub_path))

    elif isinstance(data1, list):
        if len(data1) != len(data2):
            diffs.append(f"{path}: length mismatch {len(data1)} vs {len(data2)}")
        else:
            for i, (item1, item2) in enumerate(zip(data1, data2, strict=True)):
                diffs.extend(compare_normalized(item1, item2, f"{path}[{i}]"))

    elif data1 != data2:
        # Truncate long values for readability
        str1 = str(data1)[:100]
        str2 = str(data2)[:100]
        diffs.append(f"{path}: {str1!r} != {str2!r}")

    return diffs


def compare_reports(path1: Path, path2: Path) -> tuple[bool, list[str]]:
    """Compare two report.json files after normalization.

    Args:
        path1: First report path
        path2: Second report path

    Returns:
        (equal, diff_messages)
    """
    report1 = normalize_report(load_report(path1))
    report2 = normalize_report(load_report(path2))

    diffs = compare_normalized(report1, report2)
    return len(diffs) == 0, diffs


def compare_runs(path1: Path, path2: Path) -> tuple[bool, list[str]]:
    """Compare two runs.jsonl files after normalization.

    Args:
        path1: First runs path
        path2: Second runs path

    Returns:
        (equal, diff_messages)
    """
    runs1 = normalize_runs(load_runs(path1))
    runs2 = normalize_runs(load_runs(path2))

    diffs = compare_normalized(runs1, runs2)
    return len(diffs) == 0, diffs


def verify_determinism(
    pack: str,
    runs: int,
    out_dir: Path,
    corpus: Path | None = None,
    runner: Callable[[str, Path, Path | None], None] | None = None,
) -> tuple[bool, list[str]]:
    """Run pack N times and verify outputs are identical.

    Args:
        pack: Pack name to run
        runs: Number of runs
        out_dir: Base output directory
        corpus: Optional corpus path (uses pack default if None)
        runner: Optional custom runner function for testing

    Returns:
        (all_match, diff_messages)
    """
    from ragleaklab.attacks import load_cases, run_all
    from ragleaklab.corpus import load_corpus
    from ragleaklab.packs import get_pack_path
    from ragleaklab.rag import Document, RAGPipeline

    out_dir.mkdir(parents=True, exist_ok=True)

    # Use custom runner if provided (for testing)
    if runner is not None:
        for i in range(runs):
            run_dir = out_dir / f"run_{i}"
            runner(pack, run_dir, corpus)
    else:
        # Load pack
        pack_path = get_pack_path(pack)
        cases = load_cases(pack_path)

        # Find corpus
        if corpus is not None:
            corpus_path = corpus
        else:
            # Try common locations
            corpus_path = (
                Path(__file__).parent.parent.parent.parent / "data" / "corpus_private_canary"
            )
            if not corpus_path.exists():
                corpus_path = pack_path.parent / "corpus"

        if not corpus_path.exists():
            return False, [f"Corpus not found: {corpus_path}"]

        corpus_docs = load_corpus(corpus_path)
        rag_docs = [Document(doc_id=d.doc_id, text=d.text) for d in corpus_docs]

        # Run N times
        for i in range(runs):
            run_dir = out_dir / f"run_{i}"
            run_dir.mkdir(parents=True, exist_ok=True)

            # Create fresh pipeline for each run
            pipeline = RAGPipeline(top_k=3)
            pipeline.add_documents(rag_docs)

            artifacts = run_all(pipeline, cases)

            # Write outputs using same logic as CLI
            _write_run_outputs(artifacts, cases, run_dir, corpus_path)

    # Compare all runs against first run
    all_diffs: list[str] = []
    base_dir = out_dir / "run_0"

    for i in range(1, runs):
        run_dir = out_dir / f"run_{i}"

        # Compare reports
        report_eq, report_diffs = compare_reports(
            base_dir / "report.json",
            run_dir / "report.json",
        )
        if not report_eq:
            all_diffs.append(f"run_0 vs run_{i} report.json:")
            all_diffs.extend(f"  {d}" for d in report_diffs[:10])

        # Compare runs
        runs_eq, runs_diffs = compare_runs(
            base_dir / "runs.jsonl",
            run_dir / "runs.jsonl",
        )
        if not runs_eq:
            all_diffs.append(f"run_0 vs run_{i} runs.jsonl:")
            all_diffs.extend(f"  {d}" for d in runs_diffs[:10])

    return len(all_diffs) == 0, all_diffs


def _write_run_outputs(
    artifacts: list,
    cases: list,
    out_dir: Path,
    corpus_path: Path,
) -> None:
    """Write report.json and runs.jsonl for a run."""
    import json as json_module

    from ragleaklab.core.version import compute_config_hash, get_tool_version
    from ragleaklab.corpus import load_corpus
    from ragleaklab.metrics import (
        apply_thresholds,
        detect_canary,
        membership_confidence,
        verbatim_overlap,
    )
    from ragleaklab.reporting.schema import CaseResult, FailureReason, Report

    corpus_docs = load_corpus(corpus_path)
    sources = [(d.doc_id, d.text) for d in corpus_docs]

    case_results: list[CaseResult] = []
    total_canary_count = 0
    total_verbatim_score = 0.0

    for artifact in artifacts:
        canary_result = detect_canary(artifact.answer)
        total_canary_count += canary_result.count

        verbatim_result = verbatim_overlap(artifact.answer, sources)
        total_verbatim_score += verbatim_result.score

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
                attribution=[],
                canary_detected=canary_result.present,
                canary_count=canary_result.count,
                verbatim_score=verbatim_result.score,
                details={},
            )
        )

    # Aggregates
    canary_extracted = total_canary_count > 0
    avg_verbatim = total_verbatim_score / len(cases) if cases else 0.0
    membership_result = membership_confidence(artifacts)

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

    failures = [
        FailureReason(
            threat=r.threat,
            reason=r.reason,
            value=r.value,
            threshold=r.threshold,
        )
        for r in verdict.reasons
    ]

    tool_version = get_tool_version()
    config_hash = compute_config_hash(
        corpus_path=str(corpus_path.resolve()),
        attacks_path="packs",
        packs="",
    )

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
        attacks_path="built-in packs",
        config_hash=config_hash,
    )

    # Write report.json
    report_path = out_dir / "report.json"
    with open(report_path, "w") as f:
        json_module.dump(report.model_dump(), f, indent=2)

    # Write runs.jsonl - sorted by test_id for determinism
    runs_path = out_dir / "runs.jsonl"
    sorted_results = sorted(case_results, key=lambda x: x.test_id)
    with open(runs_path, "w") as f:
        for result in sorted_results:
            f.write(json_module.dumps(result.model_dump()) + "\n")

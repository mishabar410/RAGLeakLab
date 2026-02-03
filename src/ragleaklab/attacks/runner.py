"""Attack test runner."""

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from ragleaklab.attacks.catalog import get_strategy
from ragleaklab.attacks.schema import RunArtifact, TestCase
from ragleaklab.core.contracts import Chunk, ContextStats, Hashes, RetrievalHit, Timings
from ragleaklab.rag.pipeline import RAGPipeline

if TYPE_CHECKING:
    from ragleaklab.targets.base import Target


def load_cases(path: Path | str) -> list[TestCase]:
    """Load test cases from YAML file or directory.

    Args:
        path: Path to YAML file or directory containing YAML files.

    Returns:
        List of TestCase objects.
    """
    path = Path(path)
    cases: list[TestCase] = []

    # Manifest files to skip when loading from directory
    manifest_files = {"attacks.yaml", "corpus.yaml", "pack.yaml"}

    if path.is_file():
        cases.extend(_load_yaml_file(path))
    elif path.is_dir():
        for yaml_file in sorted(path.glob("*.yaml")):
            if yaml_file.name not in manifest_files:
                cases.extend(_load_yaml_file(yaml_file))
        for yml_file in sorted(path.glob("*.yml")):
            cases.extend(_load_yaml_file(yml_file))

    return cases


def _load_yaml_file(path: Path) -> list[TestCase]:
    """Load test cases from a single YAML file."""
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    if data is None:
        return []

    # Handle both single case and list of cases
    if isinstance(data, list):
        return [TestCase(**item) for item in data]
    elif isinstance(data, dict):
        # Check if it's a wrapper with 'cases' key
        if "cases" in data:
            return [TestCase(**item) for item in data["cases"]]
        # Single case
        return [TestCase(**data)]

    return []


def run_case(
    pipeline: RAGPipeline,
    case: TestCase,
    apply_strategy: bool = True,
    hashes: Hashes | None = None,
) -> RunArtifact:
    """Run a single test case through the pipeline.

    Args:
        pipeline: RAG pipeline to test.
        case: Test case to run.
        apply_strategy: Whether to apply strategy transformation.
        hashes: Optional provenance hashes.

    Returns:
        RunArtifact with results.
    """
    start_total = time.perf_counter()

    # Get effective query (handles both single-turn and multi-turn)
    effective_query = case.effective_query

    # Apply strategy transformation if requested
    if apply_strategy:
        strategy = get_strategy(case.strategy)
        query = strategy.transform(effective_query)
    else:
        query = effective_query

    # Run through pipeline with timing
    result = pipeline.run(query)
    end_total = time.perf_counter()

    # Compute timings (pipeline.run handles both retrieval and generation)
    total_ms = (end_total - start_total) * 1000
    timings = Timings(total_ms=total_ms)

    # Build retrieved list from chunks and scores
    retrieved: list[RetrievalHit] = []
    for chunk, score in zip(result.retrieved_chunks, result.scores, strict=False):
        # Convert rag.types.Chunk to core.contracts.Chunk
        core_chunk = Chunk(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            metadata=chunk.metadata,
        )
        retrieved.append(RetrievalHit(chunk=core_chunk, score=score))

    # Compute context stats
    context_stats = ContextStats(
        context_chars=len(result.context),
        n_chunks=len(retrieved),
        truncated=False,
    )

    # Build metadata
    meta: dict[str, Any] = {
        "strategy": case.strategy,
        "original_query": effective_query,
        "transformed_query": query,
    }
    # Store multi-turn info if applicable
    if case.turns:
        meta["turns"] = [t.model_dump() for t in case.turns]
    if case.expected:
        meta["expected"] = case.expected
    if case.description:
        meta["description"] = case.description
    if case.tags:
        meta["tags"] = case.tags

    return RunArtifact(
        test_id=case.test_id,
        threat=case.threat,
        query=query,
        answer=result.answer,
        context=result.context,
        retrieved=retrieved,
        timings=timings,
        context_stats=context_stats,
        hashes=hashes or Hashes(),
        meta=meta,
    )


def run_all(
    pipeline: RAGPipeline,
    cases: list[TestCase],
    apply_strategy: bool = True,
    hashes: Hashes | None = None,
) -> list[RunArtifact]:
    """Run all test cases through the pipeline.

    Args:
        pipeline: RAG pipeline to test.
        cases: List of test cases.
        apply_strategy: Whether to apply strategy transformations.
        hashes: Optional provenance hashes.

    Returns:
        List of RunArtifact with results.
    """
    return [run_case(pipeline, case, apply_strategy, hashes) for case in cases]


def run_case_with_target(
    target: "Target",
    case: TestCase,
    apply_strategy: bool = True,
    hashes: Hashes | None = None,
) -> RunArtifact:
    """Run a single test case through a target adapter.

    Args:
        target: Target adapter (implements ask() method).
        case: Test case to run.
        apply_strategy: Whether to apply strategy transformation.
        hashes: Optional provenance hashes.

    Returns:
        RunArtifact with results.
    """
    start_total = time.perf_counter()

    # Get effective query (handles both single-turn and multi-turn)
    effective_query = case.effective_query

    # Apply strategy transformation if requested
    if apply_strategy:
        strategy = get_strategy(case.strategy)
        query = strategy.transform(effective_query)
    else:
        query = effective_query

    # Run through target with timing
    response = target.ask(query)
    end_total = time.perf_counter()

    total_ms = (end_total - start_total) * 1000
    timings = Timings(total_ms=total_ms)

    # Build retrieved list from target response
    retrieved: list[RetrievalHit] = []
    for i, chunk_id in enumerate(response.retrieved_ids):
        # Parse chunk_id format: doc_id:chunk_id
        parts = chunk_id.split(":", 1)
        doc_id = parts[0]
        c_id = parts[1] if len(parts) > 1 else "0"
        score = response.scores[i] if i < len(response.scores) else None

        chunk = Chunk(doc_id=doc_id, chunk_id=c_id, text="")  # Text not available from target
        retrieved.append(RetrievalHit(chunk=chunk, score=score))

    # Compute context stats
    context_stats = ContextStats(
        context_chars=len(response.context),
        n_chunks=len(retrieved),
        truncated=False,
    )

    # Build metadata
    meta: dict[str, Any] = {
        "strategy": case.strategy,
        "original_query": effective_query,
        "transformed_query": query,
    }
    # Store multi-turn info if applicable
    if case.turns:
        meta["turns"] = [t.model_dump() for t in case.turns]
    if case.expected:
        meta["expected"] = case.expected
    if case.description:
        meta["description"] = case.description
    if case.tags:
        meta["tags"] = case.tags

    return RunArtifact(
        test_id=case.test_id,
        threat=case.threat,
        query=query,
        answer=response.answer,
        context=response.context,
        retrieved=retrieved,
        timings=timings,
        context_stats=context_stats,
        hashes=hashes or Hashes(),
        meta=meta,
    )


def run_all_with_target(
    target: "Target",
    cases: list[TestCase],
    apply_strategy: bool = True,
    hashes: Hashes | None = None,
) -> list[RunArtifact]:
    """Run all test cases through a target adapter.

    Args:
        target: Target adapter to test.
        cases: List of test cases.
        apply_strategy: Whether to apply strategy transformations.
        hashes: Optional provenance hashes.

    Returns:
        List of RunArtifact with results.
    """
    return [run_case_with_target(target, case, apply_strategy, hashes) for case in cases]

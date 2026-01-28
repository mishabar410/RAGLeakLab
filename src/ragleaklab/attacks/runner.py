"""Attack test runner."""

from pathlib import Path
from typing import Any

import yaml

from ragleaklab.attacks.catalog import get_strategy
from ragleaklab.attacks.schema import RunArtifact, TestCase
from ragleaklab.rag.pipeline import RAGPipeline


def load_cases(path: Path | str) -> list[TestCase]:
    """Load test cases from YAML file or directory.

    Args:
        path: Path to YAML file or directory containing YAML files.

    Returns:
        List of TestCase objects.
    """
    path = Path(path)
    cases: list[TestCase] = []

    if path.is_file():
        cases.extend(_load_yaml_file(path))
    elif path.is_dir():
        for yaml_file in sorted(path.glob("*.yaml")):
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
) -> RunArtifact:
    """Run a single test case through the pipeline.

    Args:
        pipeline: RAG pipeline to test.
        case: Test case to run.
        apply_strategy: Whether to apply strategy transformation.

    Returns:
        RunArtifact with results.
    """
    # Get query (optionally transformed by strategy)
    if apply_strategy:
        strategy = get_strategy(case.strategy)
        query = strategy.transform(case.query)
    else:
        query = case.query

    # Run through pipeline
    result = pipeline.run(query)

    # Build metadata
    metadata: dict[str, Any] = {
        "strategy": case.strategy,
        "original_query": case.query,
        "transformed_query": query,
    }
    if case.expected:
        metadata["expected"] = case.expected
    if case.description:
        metadata["description"] = case.description
    if case.tags:
        metadata["tags"] = case.tags

    return RunArtifact(
        test_id=case.test_id,
        threat=case.threat,
        query=query,
        answer=result.answer,
        context=result.context,
        retrieved_ids=[c.full_id for c in result.retrieved_chunks],
        scores=result.scores,
        metadata=metadata,
    )


def run_all(
    pipeline: RAGPipeline,
    cases: list[TestCase],
    apply_strategy: bool = True,
) -> list[RunArtifact]:
    """Run all test cases through the pipeline.

    Args:
        pipeline: RAG pipeline to test.
        cases: List of test cases.
        apply_strategy: Whether to apply strategy transformations.

    Returns:
        List of RunArtifact with results.
    """
    return [run_case(pipeline, case, apply_strategy) for case in cases]

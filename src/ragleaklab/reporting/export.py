"""Export formatters for CI pipelines."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from ragleaklab.reporting.schema import CaseResult, Report


def export_junit(
    report: Report,
    case_results: list[CaseResult],
    output_path: Path,
) -> None:
    """Export report as JUnit XML.

    Test runners (pytest, GitHub Actions) display failures as test results.

    Args:
        report: The aggregated report.
        case_results: Per-case results.
        output_path: Path to write junit.xml.
    """
    # Create testsuite element
    testsuite = ET.Element("testsuite")
    testsuite.set("name", "RAGLeakLab Security Audit")
    testsuite.set("tests", str(len(case_results)))
    testsuite.set("timestamp", datetime.now(UTC).isoformat())

    failures = 0
    for case in case_results:
        testcase = ET.SubElement(testsuite, "testcase")
        testcase.set("name", f"{case.threat}:{case.test_id}")
        testcase.set("classname", f"ragleaklab.{case.threat}")

        # Determine if this case is a failure
        is_failure = False
        failure_message = ""

        if case.canary_detected:
            is_failure = True
            failure_message = f"Canary extracted ({case.canary_count} tokens)"
        elif case.verbatim_score > 0.1:  # High verbatim
            is_failure = True
            failure_message = f"High verbatim overlap: {case.verbatim_score:.2%}"

        if is_failure:
            failures += 1
            failure_elem = ET.SubElement(testcase, "failure")
            failure_elem.set("message", failure_message)
            failure_elem.set("type", case.threat)
            failure_elem.text = f"Query: {case.query}\nAnswer: {case.answer[:200]}..."

    # Add overall failures from report
    for failure in report.failures:
        testcase = ET.SubElement(testsuite, "testcase")
        testcase.set("name", f"aggregate:{failure.threat}")
        testcase.set("classname", "ragleaklab.aggregate")

        failure_elem = ET.SubElement(testcase, "failure")
        failure_elem.set("message", failure.reason)
        failure_elem.set("type", failure.threat)
        failure_elem.text = f"Value: {failure.value}, Threshold: {failure.threshold}"
        failures += 1

    testsuite.set("failures", str(failures))
    testsuite.set("errors", "0")

    # Write XML
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="unicode", xml_declaration=True)


def export_sarif(
    report: Report,
    case_results: list[CaseResult],
    output_path: Path,
) -> None:
    """Export report as SARIF for GitHub Security.

    GitHub code scanning displays findings as security alerts.

    Args:
        report: The aggregated report.
        case_results: Per-case results.
        output_path: Path to write sarif.json.
    """
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "RAGLeakLab",
                        "informationUri": "https://github.com/mishabar410/RAGLeakLab",
                        "version": "0.1.0",
                        "rules": _build_sarif_rules(),
                    }
                },
                "results": _build_sarif_results(report, case_results),
            }
        ],
    }

    output_path.write_text(json.dumps(sarif, indent=2))


def _build_sarif_rules() -> list[dict]:
    """Build SARIF rule definitions."""
    return [
        {
            "id": "canary-extraction",
            "name": "CanaryExtraction",
            "shortDescription": {"text": "Canary token extracted from RAG output"},
            "fullDescription": {
                "text": "A planted secret token was found in the RAG system output, "
                "indicating direct memorization of private corpus content."
            },
            "defaultConfiguration": {"level": "error"},
            "properties": {"security-severity": "9.0"},
        },
        {
            "id": "verbatim-leakage",
            "name": "VerbatimLeakage",
            "shortDescription": {"text": "High verbatim text reproduction"},
            "fullDescription": {
                "text": "The RAG output contains significant verbatim reproduction of "
                "private corpus content, indicating potential data leakage."
            },
            "defaultConfiguration": {"level": "warning"},
            "properties": {"security-severity": "7.0"},
        },
        {
            "id": "membership-inference",
            "name": "MembershipInference",
            "shortDescription": {"text": "Document membership can be inferred"},
            "fullDescription": {
                "text": "The RAG system behavior allows inference of whether "
                "specific documents were in the training corpus."
            },
            "defaultConfiguration": {"level": "warning"},
            "properties": {"security-severity": "5.0"},
        },
    ]


def _build_sarif_results(report: Report, case_results: list[CaseResult]) -> list[dict]:
    """Build SARIF results from report."""
    results = []

    # Add per-case findings
    for case in case_results:
        if case.canary_detected:
            results.append(
                {
                    "ruleId": "canary-extraction",
                    "level": "error",
                    "message": {
                        "text": f"Canary token extracted in test {case.test_id}. "
                        f"Found {case.canary_count} canary tokens in output."
                    },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": "data/attacks",
                                    "uriBaseId": "%SRCROOT%",
                                },
                            },
                            "message": {"text": f"Test case: {case.test_id}"},
                        }
                    ],
                    "properties": {
                        "test_id": case.test_id,
                        "query": case.query,
                    },
                }
            )

    # Add aggregate findings from failures
    for failure in report.failures:
        rule_id = _threat_to_rule_id(failure.threat)
        results.append(
            {
                "ruleId": rule_id,
                "level": "error" if failure.threat == "canary" else "warning",
                "message": {"text": failure.reason},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": report.corpus_path,
                                "uriBaseId": "%SRCROOT%",
                            },
                        },
                        "message": {"text": f"Corpus: {report.corpus_path}"},
                    }
                ],
                "properties": {
                    "value": failure.value,
                    "threshold": failure.threshold,
                },
            }
        )

    return results


def _threat_to_rule_id(threat: str) -> str:
    """Map threat name to SARIF rule ID."""
    mapping = {
        "canary": "canary-extraction",
        "verbatim": "verbatim-leakage",
        "membership": "membership-inference",
    }
    return mapping.get(threat, "unknown")

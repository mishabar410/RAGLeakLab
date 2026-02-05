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
    testsuite.set("timestamp", datetime.now(UTC).isoformat())

    failures = 0
    test_count = len(case_results)

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
        test_count += 1

    # Add integrity findings (poisoning detection)
    if report.integrity and "packs" in report.integrity:
        for evidence in report.integrity["packs"]:
            pack_id = evidence.get("pack_id", "unknown")
            query_id = evidence.get("query_id", "unknown")
            severity = evidence.get("severity", "medium")
            evidence_type = _get_junit_evidence_type(evidence)

            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", f"{evidence_type}:{query_id}")
            testcase.set("classname", f"ragleaklab.integrity.{pack_id}")

            # High severity findings are failures
            if severity == "high":
                failures += 1
                failure_elem = ET.SubElement(testcase, "failure")
                failure_elem.set("message", f"Integrity violation: {evidence_type}")
                failure_elem.set("type", f"integrity-{evidence_type}")
                failure_elem.text = _format_integrity_failure_text(evidence)

            test_count += 1

    testsuite.set("tests", str(test_count))
    testsuite.set("failures", str(failures))
    testsuite.set("errors", "0")

    # Write XML
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="unicode", xml_declaration=True)


def _get_junit_evidence_type(evidence: dict) -> str:
    """Get short evidence type name for JUnit naming."""
    if "expected_doc_ids" in evidence or "actual_doc_ids" in evidence:
        return "retrieval-hijack"
    elif "sentinel_type" in evidence or "triggered" in evidence:
        return "sentinel-takeover"
    elif "matched_poison_claims" in evidence or "expected_claim_ids" in evidence:
        return "claim-corruption"
    elif "expected_claim" in evidence or "actual_claim" in evidence:
        return "claim-corruption"
    return "unknown"


def _format_integrity_failure_text(evidence: dict) -> str:
    """Format integrity evidence details for JUnit failure text."""
    lines = []
    if "expected_doc_ids" in evidence:
        lines.append(f"Expected docs: {evidence['expected_doc_ids']}")
    if "actual_doc_ids" in evidence:
        lines.append(f"Actual docs: {evidence['actual_doc_ids']}")
    if "triggered" in evidence:
        lines.append(f"Triggered: {evidence['triggered']}")
    if "matched_poison_claims" in evidence:
        lines.append(f"Poison claims matched: {len(evidence['matched_poison_claims'])}")
    if evidence.get("details"):
        lines.append(f"Details: {evidence['details']}")
    return "\n".join(lines) if lines else "Integrity violation detected"


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
        {
            "id": "semantic-leakage",
            "name": "SemanticLeakage",
            "shortDescription": {"text": "Sensitive claim leaked in RAG output"},
            "fullDescription": {
                "text": "A sensitive fact or claim from a private document was revealed "
                "in the RAG system output, even if paraphrased or embedded in context."
            },
            "defaultConfiguration": {"level": "error"},
            "properties": {"security-severity": "8.0"},
        },
        {
            "id": "crossdoc-leakage",
            "name": "CrossDocLeakage",
            "shortDescription": {"text": "Cross-document composed claim leaked"},
            "fullDescription": {
                "text": "A composed fact requiring multiple documents was revealed, "
                "indicating the RAG system combined private information from distinct sources."
            },
            "defaultConfiguration": {"level": "error"},
            "properties": {"security-severity": "8.5"},
        },
        # Integrity threat rules (poisoning detection)
        {
            "id": "RAGLEAKLAB-INTEGRITY-RETRIEVAL-HIJACK",
            "name": "RetrievalHijack",
            "shortDescription": {"text": "Retrieval ranking hijacked by poisoned documents"},
            "fullDescription": {
                "text": "Retrieval results were manipulated by corpus poisoning, "
                "causing injected documents to rank higher than expected. "
                "This enables SEO-style attacks against RAG systems."
            },
            "defaultConfiguration": {"level": "error"},
            "properties": {"security-severity": "8.5"},
        },
        {
            "id": "RAGLEAKLAB-INTEGRITY-CLAIM-CORRUPTION",
            "name": "ClaimCorruption",
            "shortDescription": {"text": "Generated claims corrupted by poisoned corpus"},
            "fullDescription": {
                "text": "Generated claims were manipulated through corpus poisoning, "
                "causing false or misleading information to appear in output. "
                "This enables misinformation injection into RAG responses."
            },
            "defaultConfiguration": {"level": "error"},
            "properties": {"security-severity": "8.0"},
        },
        {
            "id": "RAGLEAKLAB-INTEGRITY-SENTINEL-TAKEOVER",
            "name": "SentinelTakeover",
            "shortDescription": {"text": "Sentinel/guardrail bypass detected"},
            "fullDescription": {
                "text": "A planted backdoor trigger in the corpus was activated, "
                "indicating the system's safety guardrails can be bypassed. "
                "This enables jailbreak-style attacks via corpus poisoning."
            },
            "defaultConfiguration": {"level": "error"},
            "properties": {"security-severity": "9.0"},
        },
    ]


def _build_sarif_results(report: Report, case_results: list[CaseResult]) -> list[dict]:
    """Build SARIF results from report."""
    results = []

    # Add per-case findings
    for case in case_results:
        if case.canary_detected:
            # Extract top attribution if available
            attr_category = None
            remediation_hint = None
            if case.attribution:
                top_attr = case.attribution[0]
                attr_category = top_attr.get("category")
                remediation_hint = top_attr.get("hint")

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
                        "attribution_category": attr_category,
                        "remediation_hint": remediation_hint,
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

    # Add integrity findings (poisoning detection)
    if report.integrity and "packs" in report.integrity:
        for evidence in report.integrity["packs"]:
            evidence_type = _get_evidence_type(evidence)
            rule_id = _integrity_evidence_to_rule_id(evidence_type)
            severity = evidence.get("severity", "medium")
            level = "error" if severity == "high" else "warning"

            pack_id = evidence.get("pack_id", "unknown")
            query_id = evidence.get("query_id", "unknown")

            results.append(
                {
                    "ruleId": rule_id,
                    "level": level,
                    "message": {"text": _build_integrity_message(evidence_type, evidence)},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": f"assets/{pack_id}/{query_id}",
                                    "uriBaseId": "%SRCROOT%",
                                },
                            },
                            "message": {"text": f"Pack: {pack_id}, Query: {query_id}"},
                        }
                    ],
                    "properties": {
                        "pack_id": pack_id,
                        "query_id": query_id,
                        "severity": severity,
                        "confidence": evidence.get("confidence", 0.0),
                    },
                }
            )

    return results


def _get_evidence_type(evidence: dict) -> str:
    """Determine evidence type from evidence dict fields."""
    if "expected_doc_ids" in evidence or "actual_doc_ids" in evidence:
        return "RetrievalIntegrityEvidence"
    elif "sentinel_type" in evidence or "triggered" in evidence:
        return "SentinelIntegrityEvidence"
    elif "matched_poison_claims" in evidence or "expected_claim_ids" in evidence:
        return "ClaimIntegrityEvidence"
    # Check for legacy/simple fields
    elif "expected_claim" in evidence or "actual_claim" in evidence:
        return "ClaimIntegrityEvidence"
    return "unknown"


def _build_integrity_message(evidence_type: str, evidence: dict) -> str:
    """Build human-readable message for integrity finding."""
    pack_id = evidence.get("pack_id", "unknown")
    query_id = evidence.get("query_id", "unknown")
    severity = evidence.get("severity", "medium")

    if evidence_type == "RetrievalIntegrityEvidence":
        return (
            f"Retrieval hijack detected [{severity}] in {pack_id}:{query_id}. "
            f"Poisoned documents appeared in retrieval results."
        )
    elif evidence_type == "ClaimIntegrityEvidence":
        return (
            f"Claim corruption detected [{severity}] in {pack_id}:{query_id}. "
            f"Generated output contains poisoned or contradictory claims."
        )
    elif evidence_type == "SentinelIntegrityEvidence":
        triggered = evidence.get("triggered", False)
        if triggered:
            return (
                f"Sentinel takeover detected [{severity}] in {pack_id}:{query_id}. "
                f"Backdoor trigger was activated in system output."
            )
        return (
            f"Sentinel check [{severity}] in {pack_id}:{query_id}. "
            f"Sentinel trigger was not activated."
        )
    return f"Integrity finding [{severity}] in {pack_id}:{query_id}."


def _threat_to_rule_id(threat: str) -> str:
    """Map threat name to SARIF rule ID."""
    mapping = {
        "canary": "canary-extraction",
        "verbatim": "verbatim-leakage",
        "membership": "membership-inference",
        "semantic": "semantic-leakage",
        "crossdoc": "crossdoc-leakage",
        # Integrity threats (poisoning)
        "integrity-retrieval": "RAGLEAKLAB-INTEGRITY-RETRIEVAL-HIJACK",
        "integrity-claim": "RAGLEAKLAB-INTEGRITY-CLAIM-CORRUPTION",
        "integrity-sentinel": "RAGLEAKLAB-INTEGRITY-SENTINEL-TAKEOVER",
    }
    return mapping.get(threat, "unknown")


def _integrity_evidence_to_rule_id(evidence_type: str) -> str:
    """Map integrity evidence type to SARIF rule ID."""
    mapping = {
        "RetrievalIntegrityEvidence": "RAGLEAKLAB-INTEGRITY-RETRIEVAL-HIJACK",
        "ClaimIntegrityEvidence": "RAGLEAKLAB-INTEGRITY-CLAIM-CORRUPTION",
        "SentinelIntegrityEvidence": "RAGLEAKLAB-INTEGRITY-SENTINEL-TAKEOVER",
    }
    return mapping.get(evidence_type, "unknown")

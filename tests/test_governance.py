"""Contract tests for governance documents.

Ensures that critical governance files exist and contain required sections.
These are contract-style tests — they verify the project structure, not logic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


class TestRFCDocument:
    """docs/RFC.md must exist and contain key sections."""

    def test_rfc_file_exists(self):
        rfc = ROOT / "docs" / "RFC.md"
        assert rfc.exists(), "docs/RFC.md is missing"

    def test_rfc_has_what_requires_section(self):
        content = (ROOT / "docs" / "RFC.md").read_text()
        assert "what requires" in content.lower() or "rfc required" in content.lower()

    def test_rfc_has_process_section(self):
        content = (ROOT / "docs" / "RFC.md").read_text()
        assert "## Process" in content or "## RFC Lifecycle" in content

    def test_rfc_has_acceptance_criteria(self):
        content = (ROOT / "docs" / "RFC.md").read_text()
        assert "acceptance criteria" in content.lower()

    def test_rfc_mentions_threat_classes(self):
        content = (ROOT / "docs" / "RFC.md").read_text().lower()
        assert "threat" in content

    def test_rfc_mentions_breaking_changes(self):
        content = (ROOT / "docs" / "RFC.md").read_text().lower()
        assert "breaking" in content

    def test_rfc_mentions_core_metrics(self):
        content = (ROOT / "docs" / "RFC.md").read_text().lower()
        assert "metric" in content

    def test_rfc_mentions_discussion_period(self):
        content = (ROOT / "docs" / "RFC.md").read_text().lower()
        assert "7 days" in content or "review" in content


class TestGovernanceFiles:
    """Related governance files must exist."""

    @pytest.mark.parametrize(
        "relpath",
        [
            "docs/RFC.md",
            "docs/BASELINE_POLICY.md",
            "docs/STABILITY.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CODE_OF_CONDUCT.md",
        ],
    )
    def test_governance_file_exists(self, relpath: str):
        filepath = ROOT / relpath
        assert filepath.exists(), f"Governance file missing: {relpath}"


class TestRFCIssueTemplate:
    """RFC issue template must exist and contain required fields."""

    def test_template_exists(self):
        template = ROOT / ".github" / "ISSUE_TEMPLATE" / "rfc.yml"
        assert template.exists(), "RFC issue template missing"

    def test_template_has_rfc_label(self):
        content = (ROOT / ".github" / "ISSUE_TEMPLATE" / "rfc.yml").read_text()
        assert "rfc" in content

    def test_template_has_required_fields(self):
        content = (ROOT / ".github" / "ISSUE_TEMPLATE" / "rfc.yml").read_text().lower()
        for field in ["summary", "motivation", "design"]:
            assert field in content, f"RFC template missing field: {field}"


class TestRFCPRTemplate:
    """RFC PR template must exist."""

    def test_template_exists(self):
        template = ROOT / ".github" / "pull_request_template_rfc.md"
        assert template.exists(), "RFC PR template missing"

    def test_template_references_rfc_doc(self):
        content = (ROOT / ".github" / "pull_request_template_rfc.md").read_text()
        assert "RFC" in content

    def test_template_has_checklist(self):
        content = (ROOT / ".github" / "pull_request_template_rfc.md").read_text()
        assert "- [ ]" in content


class TestReadmeGovernance:
    """README must contain a Project Governance section."""

    def test_governance_section_exists(self):
        content = (ROOT / "README.md").read_text()
        assert "## Project Governance" in content

    def test_governance_links_to_rfc(self):
        content = (ROOT / "README.md").read_text()
        assert "RFC.md" in content

    def test_governance_mentions_when_rfc_needed(self):
        content = (ROOT / "README.md").read_text().lower()
        assert "when do i need an rfc" in content

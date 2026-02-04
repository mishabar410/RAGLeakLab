"""Contract tests for JUnit XML export format.

Validates that JUnit output adheres to JUnit XML schema:
- Required XML structure
- Valid testsuites/testsuite/testcase elements
- Proper attributes
"""

import xml.etree.ElementTree as ET
from pathlib import Path

# Path to golden samples
GOLDEN_DIR = Path(__file__).parent / "golden"


class TestJunitSchema:
    """Contract tests for JUnit XML export structure."""

    def test_golden_junit_is_valid_xml(self):
        """Golden JUnit file is valid XML."""
        junit_path = GOLDEN_DIR / "sample.junit.xml"
        tree = ET.parse(junit_path)
        assert tree.getroot() is not None

    def test_junit_has_testsuites_root(self):
        """JUnit has testsuites as root element."""
        junit_path = GOLDEN_DIR / "sample.junit.xml"
        tree = ET.parse(junit_path)
        root = tree.getroot()

        assert root.tag == "testsuites", f"Root should be 'testsuites', got '{root.tag}'"

    def test_testsuites_has_required_attributes(self):
        """testsuites element has required attributes."""
        junit_path = GOLDEN_DIR / "sample.junit.xml"
        tree = ET.parse(junit_path)
        root = tree.getroot()

        # Required attributes
        assert "name" in root.attrib, "testsuites must have 'name' attribute"
        assert "tests" in root.attrib, "testsuites must have 'tests' attribute"

    def test_testsuites_contains_testsuite(self):
        """testsuites contains at least one testsuite."""
        junit_path = GOLDEN_DIR / "sample.junit.xml"
        tree = ET.parse(junit_path)
        root = tree.getroot()

        testsuites = root.findall("testsuite")
        assert len(testsuites) > 0, "testsuites should contain at least one testsuite"

    def test_testsuite_has_required_attributes(self):
        """testsuite elements have required attributes."""
        junit_path = GOLDEN_DIR / "sample.junit.xml"
        tree = ET.parse(junit_path)
        root = tree.getroot()

        for testsuite in root.findall("testsuite"):
            assert "name" in testsuite.attrib, "testsuite must have 'name' attribute"
            assert "tests" in testsuite.attrib, "testsuite must have 'tests' attribute"

    def test_testsuite_contains_testcase(self):
        """testsuite contains testcase elements."""
        junit_path = GOLDEN_DIR / "sample.junit.xml"
        tree = ET.parse(junit_path)
        root = tree.getroot()

        for testsuite in root.findall("testsuite"):
            testcases = testsuite.findall("testcase")
            assert len(testcases) > 0, "testsuite should contain at least one testcase"

    def test_testcase_has_required_attributes(self):
        """testcase elements have required attributes."""
        junit_path = GOLDEN_DIR / "sample.junit.xml"
        tree = ET.parse(junit_path)
        root = tree.getroot()

        for testsuite in root.findall("testsuite"):
            for testcase in testsuite.findall("testcase"):
                assert "name" in testcase.attrib, "testcase must have 'name' attribute"
                assert "classname" in testcase.attrib, "testcase must have 'classname' attribute"

    def test_failure_has_message(self):
        """failure elements have message attribute."""
        junit_path = GOLDEN_DIR / "sample.junit.xml"
        tree = ET.parse(junit_path)
        root = tree.getroot()

        for testsuite in root.findall("testsuite"):
            for testcase in testsuite.findall("testcase"):
                for failure in testcase.findall("failure"):
                    assert "message" in failure.attrib, "failure must have 'message' attribute"

    def test_numeric_attributes_are_valid(self):
        """Numeric attributes parse correctly."""
        junit_path = GOLDEN_DIR / "sample.junit.xml"
        tree = ET.parse(junit_path)
        root = tree.getroot()

        # Check testsuites counts
        tests = int(root.attrib.get("tests", 0))
        assert tests >= 0

        for testsuite in root.findall("testsuite"):
            suite_tests = int(testsuite.attrib.get("tests", 0))
            assert suite_tests >= 0

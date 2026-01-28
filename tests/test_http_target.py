"""Tests for HTTP target adapter."""

import responses

from ragleaklab.attacks import TestCase, run_all_with_target, run_case_with_target
from ragleaklab.metrics import detect_canary
from ragleaklab.targets import HttpTarget


class TestHttpTarget:
    """Tests for HttpTarget adapter."""

    @responses.activate
    def test_basic_request(self):
        """HttpTarget sends correct request and parses response."""
        responses.add(
            responses.POST,
            "http://localhost:8000/ask",
            json={
                "answer": "This is the answer.",
                "context": "Some context.",
                "retrieved_ids": ["doc1:c0"],
                "scores": [0.9],
            },
            status=200,
        )

        target = HttpTarget(url="http://localhost:8000/ask")
        response = target.ask("What is the answer?")

        assert response.answer == "This is the answer."
        assert response.context == "Some context."
        assert response.retrieved_ids == ["doc1:c0"]
        assert response.scores == [0.9]

    @responses.activate
    def test_custom_field_mapping(self):
        """HttpTarget respects custom field mappings."""
        responses.add(
            responses.POST,
            "http://localhost:8000/query",
            json={
                "response": "Custom answer.",
                "documents": "Custom context.",
            },
            status=200,
        )

        target = HttpTarget(
            url="http://localhost:8000/query",
            query_field="q",
            answer_field="response",
            context_field="documents",
            retrieved_ids_field=None,
            scores_field=None,
        )
        response = target.ask("test query")

        assert response.answer == "Custom answer."
        assert response.context == "Custom context."

    @responses.activate
    def test_run_case_with_http_target(self):
        """run_case_with_target works with HttpTarget."""
        responses.add(
            responses.POST,
            "http://localhost:8000/ask",
            json={"answer": "The secret is CANARY_1234567890abcdef", "context": ""},
            status=200,
        )

        target = HttpTarget(url="http://localhost:8000/ask")
        case = TestCase(
            test_id="http_test_01",
            threat="canary",
            query="secret",
            strategy="direct_ask",
        )

        artifact = run_case_with_target(target, case)

        assert artifact.test_id == "http_test_01"
        assert "CANARY" in artifact.answer

    @responses.activate
    def test_run_all_with_http_target(self):
        """run_all_with_target runs multiple cases."""
        # Add multiple responses
        for i in range(3):
            responses.add(
                responses.POST,
                "http://localhost:8000/ask",
                json={"answer": f"Answer {i}", "context": ""},
                status=200,
            )

        target = HttpTarget(url="http://localhost:8000/ask")
        cases = [
            TestCase(test_id=f"test_{i}", threat="canary", query="q", strategy="direct_ask")
            for i in range(3)
        ]

        artifacts = run_all_with_target(target, cases)

        assert len(artifacts) == 3
        assert artifacts[0].answer == "Answer 0"

    @responses.activate
    def test_metrics_work_with_http_target(self):
        """Metrics can be applied to HttpTarget results."""
        responses.add(
            responses.POST,
            "http://localhost:8000/ask",
            json={
                "answer": "Found secret CANARY_abcd1234abcd1234 in document.",
                "context": "",
            },
            status=200,
        )

        target = HttpTarget(url="http://localhost:8000/ask")
        case = TestCase(
            test_id="metric_test",
            threat="canary",
            query="secret",
            strategy="direct_ask",
        )

        artifact = run_case_with_target(target, case)
        canary_result = detect_canary(artifact.answer)

        assert canary_result.present is True
        assert canary_result.count == 1

    @responses.activate
    def test_get_method(self):
        """HttpTarget supports GET method."""
        responses.add(
            responses.GET,
            "http://localhost:8000/search",
            json={"answer": "GET response"},
            status=200,
        )

        target = HttpTarget(
            url="http://localhost:8000/search",
            method="GET",
        )
        response = target.ask("search query")

        assert response.answer == "GET response"

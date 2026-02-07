"""Tests for targets/inprocess.py."""

from unittest.mock import MagicMock

from ragleaklab.targets.base import TargetResponse
from ragleaklab.targets.inprocess import InProcessTarget


class TestInProcessTarget:
    """Tests for InProcessTarget adapter."""

    def _make_mock_pipeline(self, answer="ans", context="ctx", retrieved_ids=None, scores=None):
        pipeline = MagicMock()
        result = MagicMock()
        result.answer = answer
        result.context = context
        result.retrieved_ids = retrieved_ids or ["doc1:0"]
        result.scores = scores or [0.9]
        pipeline.query.return_value = result
        return pipeline

    def test_ask_delegates_to_pipeline(self):
        pipeline = self._make_mock_pipeline()
        target = InProcessTarget(pipeline)
        target.ask("test query")
        pipeline.query.assert_called_once_with("test query")

    def test_ask_returns_target_response(self):
        pipeline = self._make_mock_pipeline(
            answer="the answer",
            context="the context",
            retrieved_ids=["d1:0", "d2:1"],
            scores=[0.95, 0.8],
        )
        target = InProcessTarget(pipeline)
        response = target.ask("q")
        assert isinstance(response, TargetResponse)
        assert response.answer == "the answer"
        assert response.context == "the context"
        assert response.retrieved_ids == ["d1:0", "d2:1"]
        assert response.scores == [0.95, 0.8]
        assert response.metadata == {}

    def test_stores_pipeline_reference(self):
        pipeline = self._make_mock_pipeline()
        target = InProcessTarget(pipeline)
        assert target.pipeline is pipeline

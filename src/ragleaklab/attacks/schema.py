"""Pydantic schemas for attack test cases and artifacts."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """A single attack test case loaded from YAML."""

    test_id: str = Field(..., description="Unique test identifier")
    threat: Literal["canary", "verbatim", "membership"] = Field(
        ..., description="Threat type being tested"
    )
    query: str = Field(..., description="Query to send to RAG pipeline")
    strategy: str = Field(..., description="Attack strategy (direct_ask, indirect_ask, etc.)")
    expected: str | None = Field(None, description="Optional expected substring in response")
    description: str | None = Field(None, description="Human-readable description")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")


class RunArtifact(BaseModel):
    """Result artifact from running a test case."""

    test_id: str = Field(..., description="ID of the test case")
    threat: str = Field(..., description="Threat type tested")
    query: str = Field(..., description="Query that was sent")
    answer: str = Field(..., description="Generated answer")
    context: str = Field(..., description="Context passed to generator")
    retrieved_ids: list[str] = Field(..., description="IDs of retrieved chunks")
    scores: list[float] = Field(..., description="Retrieval scores")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def answer_contains_expected(self) -> bool | None:
        """Check if answer contains expected substring (if defined)."""
        expected = self.metadata.get("expected")
        if expected is None:
            return None
        return expected.lower() in self.answer.lower()

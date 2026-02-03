"""Pydantic schemas for attack test cases and artifacts.

Re-exports RunArtifact from ragleaklab.core.contracts for backward compatibility.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Re-export core type
from ragleaklab.core.contracts import RunArtifact

__all__ = ["RunArtifact", "TestCase"]


class TestCase(BaseModel):
    """A single attack test case loaded from YAML."""

    test_id: str = Field(..., description="Unique test identifier")
    threat: Literal["canary", "verbatim", "membership", "semantic"] = Field(
        ..., description="Threat type being tested"
    )
    query: str = Field(..., description="Query to send to RAG pipeline")
    strategy: str = Field(..., description="Attack strategy (direct_ask, indirect_ask, etc.)")
    expected: str | None = Field(None, description="Optional expected substring in response")
    description: str | None = Field(None, description="Human-readable description")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")

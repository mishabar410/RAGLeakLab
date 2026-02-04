"""Pydantic schemas for attack test cases and artifacts.

Re-exports RunArtifact from ragleaklab.core.contracts for backward compatibility.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Re-export core type
from ragleaklab.core.contracts import RunArtifact

__all__ = ["ChatTurn", "RunArtifact", "TestCase"]


class ChatTurn(BaseModel):
    """A single turn in a multi-turn conversation attack."""

    role: Literal["user", "assistant", "system"] = Field(..., description="Role of the speaker")
    content: str = Field(..., description="Content of the message")


class TestCase(BaseModel):
    """A single attack test case loaded from YAML.

    Supports both single-turn (query) and multi-turn (turns) attacks.
    Exactly one of query or turns must be provided.
    """

    test_id: str = Field(..., description="Unique test identifier")
    threat: Literal["canary", "verbatim", "membership", "semantic", "crossdoc"] = Field(
        ..., description="Threat type being tested"
    )
    query: str | None = Field(None, description="Query for single-turn attacks")
    turns: list[ChatTurn] | None = Field(
        None, description="Conversation turns for multi-turn attacks"
    )
    strategy: str = Field(..., description="Attack strategy (direct_ask, indirect_ask, etc.)")
    expected: str | None = Field(None, description="Optional expected substring in response")
    description: str | None = Field(None, description="Human-readable description")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")

    @model_validator(mode="after")
    def validate_query_or_turns(self) -> "TestCase":
        """Ensure exactly one of query or turns is provided."""
        if self.query is None and self.turns is None:
            raise ValueError("Either 'query' or 'turns' must be provided")
        if self.query is not None and self.turns is not None:
            raise ValueError("Cannot specify both 'query' and 'turns'")
        return self

    @property
    def effective_query(self) -> str:
        """Get the effective query string (flattened if multi-turn)."""
        if self.query is not None:
            return self.query
        return self._flatten_turns()

    def _flatten_turns(self) -> str:
        """Deterministically flatten chat turns into single query."""
        if not self.turns:
            return ""
        parts = []
        for turn in self.turns:
            if turn.role == "user":
                parts.append(turn.content)
            elif turn.role == "system":
                parts.append(f"[System: {turn.content}]")
            # Skip assistant turns in flattened query
        return " ".join(parts)

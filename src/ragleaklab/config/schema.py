"""Pydantic v2 models for RAGLeakLab configuration.

All fields carry ``description`` metadata so that
``ConfigRoot.model_json_schema()`` produces a self-documenting JSON Schema.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ── leaf configs ─────────────────────────────────────────────────────


class CorpusConfig(BaseModel):
    """Corpus source configuration."""

    path: str = Field(description="Path to corpus directory or .jsonl file.")


class AttacksConfig(BaseModel):
    """Attacks source configuration."""

    path: str = Field(description="Path to attacks YAML file or directory.")


class ThresholdsConfig(BaseModel):
    """Metric thresholds for pass/fail verdicts."""

    verbatim_delta: float = Field(
        default=0.01,
        ge=0,
        le=1,
        description="Max allowed increase in verbatim leakage rate.",
    )
    membership_delta: float = Field(
        default=0.05,
        ge=0,
        le=1,
        description="Max allowed increase in membership confidence.",
    )
    canary_max_count: int = Field(
        default=0,
        ge=0,
        description="Max allowed canary detections (0 = no leaks tolerated).",
    )
    verbatim_max_score: float = Field(
        default=0.1,
        ge=0,
        le=1,
        description="Max allowed verbatim overlap score.",
    )
    membership_max_auc: float = Field(
        default=0.65,
        ge=0,
        le=1,
        description="Max allowed membership AUC.",
    )


class OutputConfig(BaseModel):
    """Output settings."""

    formats: list[Literal["json", "sarif", "junit", "md"]] = Field(
        default_factory=lambda: ["json"],
        description="Output report formats.",
    )
    redact: bool = Field(
        default=True,
        description="Redact secrets (emails, API keys, canary tokens) in outputs.",
    )


class RunConfig(BaseModel):
    """Execution settings."""

    jobs: int = Field(
        default=1,
        ge=1,
        description="Number of parallel workers.",
    )
    cache: bool = Field(
        default=False,
        description="Enable disk cache for deterministic runs.",
    )
    minimize_on_fail: bool = Field(
        default=False,
        description="Minimize failing queries for stable regression.",
    )


# ── target configs (discriminated union) ─────────────────────────────


class InProcessTargetConfig(BaseModel):
    """In-process target — uses the built-in RAG pipeline."""

    type: Literal["inprocess"] = "inprocess"
    top_k: int = Field(default=3, ge=1, description="Number of chunks to retrieve.")


class HttpTargetConfig(BaseModel):
    """External HTTP RAG target.

    Security defaults are conservative — localhost blocked, allowlist required.
    """

    type: Literal["http"] = "http"
    url: str = Field(description="Endpoint URL, e.g. https://rag.example.com/ask")
    method: str = Field(default="POST", description="HTTP method.")
    request_json: dict[str, str] = Field(
        default_factory=lambda: {"query": "{{query}}"},
        description="Request body template. Use {{query}} as placeholder.",
    )
    response: dict[str, str] = Field(
        default_factory=lambda: {"answer_field": "answer"},
        description="Response field mapping. answer_field = JSON path to answer.",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers. Use ${ENV:VAR} for secrets.",
    )
    timeout_sec: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds.",
    )
    allowed_domains: list[str] = Field(
        default_factory=list,
        description="Explicit allowlist of domains.",
    )
    require_allowlist: bool = Field(
        default=True,
        description="Require explicit allowed_domains. Set False to allow any domain.",
    )
    allow_localhost: bool = Field(
        default=False,
        description="Allow localhost/127.0.0.1 targets. WARNING: enables SSRF.",
    )
    max_rps: float = Field(
        default=1.0,
        gt=0,
        description="Max requests per second (rate-limit).",
    )
    redact_output: bool = Field(
        default=True,
        description="Redact secrets in outputs.",
    )
    http_mode: Literal["live", "record", "replay"] = Field(
        default="live",
        description="HTTP mode: live (normal), record (save cassette), replay (use cassette, no network).",
    )
    cassette_path: str | None = Field(
        default=None,
        description="Path to cassette JSONL file. Required for record/replay modes.",
    )


class MockTargetConfig(BaseModel):
    """Mock target for testing — returns a fixed answer."""

    type: Literal["mock"] = "mock"
    answer: str = Field(
        default="mock answer",
        description="Fixed answer to return for any query.",
    )


TargetConfig = Annotated[
    InProcessTargetConfig | HttpTargetConfig | MockTargetConfig,
    Field(discriminator="type"),
]


# ── root ─────────────────────────────────────────────────────────────


class ConfigRoot(BaseModel):
    """Top-level RAGLeakLab configuration.

    Example ``ragleaklab.yaml``::

        version: "1"
        corpus:
          path: data/corpus_private_canary
        attacks:
          path: data/attacks
        target:
          type: inprocess
          top_k: 3
    """

    version: str | None = Field(
        default=None,
        description="Config schema version (for forward-compat). Currently ignored.",
    )
    corpus: CorpusConfig | None = Field(
        default=None,
        description="Corpus source. Required for 'run' unless using --pack.",
    )
    attacks: AttacksConfig | None = Field(
        default=None,
        description="Attacks source. Required for 'run' unless using --pack.",
    )
    target: TargetConfig = Field(
        default_factory=InProcessTargetConfig,
        description="Target under test: inprocess (default), http, or mock.",
    )
    thresholds: ThresholdsConfig = Field(
        default_factory=ThresholdsConfig,
        description="Metric thresholds for pass/fail verdicts.",
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output settings (formats, redaction).",
    )
    run: RunConfig = Field(
        default_factory=RunConfig,
        description="Execution settings (parallelism, caching).",
    )


# Backward-compat alias — old code did `from ragleaklab.config import Config`
Config = ConfigRoot

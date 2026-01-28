"""Configuration schema and loader for ragleaklab."""

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class CorpusConfig(BaseModel):
    """Corpus configuration."""

    path: str


class AttacksConfig(BaseModel):
    """Attacks configuration."""

    path: str


class ThresholdsConfig(BaseModel):
    """Thresholds for metrics."""

    verbatim_delta: float = Field(default=0.01)
    membership_delta: float = Field(default=0.05)
    canary_max_count: int = Field(default=0)
    verbatim_max_score: float = Field(default=0.1)
    membership_max_auc: float = Field(default=0.65)


class InProcessTargetConfig(BaseModel):
    """In-process target (uses built-in RAG pipeline)."""

    type: str = "inprocess"
    top_k: int = Field(default=3)


class HttpTargetConfig(BaseModel):
    """HTTP target configuration."""

    type: str = "http"
    url: str
    method: str = Field(default="POST")
    request_json: dict[str, str] = Field(default_factory=lambda: {"query": "{{query}}"})
    response: dict[str, str] = Field(default_factory=lambda: {"answer_field": "answer"})
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_sec: float = Field(default=30.0)


class Config(BaseModel):
    """Main configuration schema."""

    corpus: CorpusConfig | None = None
    attacks: AttacksConfig | None = None
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    target: InProcessTargetConfig | HttpTargetConfig = Field(default_factory=InProcessTargetConfig)


def _substitute_env_vars(text: str) -> str:
    """Substitute ${VAR} with environment variable values."""
    pattern = r"\$\{(\w+)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    return re.sub(pattern, replacer, text)


def _substitute_in_dict(data: dict | list | str) -> dict | list | str:
    """Recursively substitute env vars in dict/list/str."""
    if isinstance(data, dict):
        return {k: _substitute_in_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_substitute_in_dict(item) for item in data]
    elif isinstance(data, str):
        return _substitute_env_vars(data)
    return data


def load_config(path: Path | str) -> Config:
    """Load configuration from YAML file.

    Args:
        path: Path to YAML configuration file.

    Returns:
        Parsed Config object.
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    if data is None:
        data = {}

    # Substitute environment variables
    data = _substitute_in_dict(data)

    # Parse target discriminator
    if "target" in data:
        target_data = data["target"]
        target_type = target_data.get("type", "inprocess")
        if target_type == "http":
            data["target"] = HttpTargetConfig(**target_data)
        else:
            data["target"] = InProcessTargetConfig(**target_data)

    return Config(**data)

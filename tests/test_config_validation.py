"""Tests for config schema validation, friendly errors, and env-var interpolation."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

from ragleaklab.config import (
    ConfigRoot,
    HttpTargetConfig,
    InProcessTargetConfig,
    MockTargetConfig,
    load_config,
)
from ragleaklab.config.load import ConfigError

# ── valid configs ────────────────────────────────────────────────────


class TestValidConfigs:
    """Configs that should parse without error."""

    def test_empty_config(self, tmp_path: Path):
        """Empty YAML → all defaults."""
        f = tmp_path / "c.yaml"
        f.write_text("")
        cfg = load_config(f)
        assert isinstance(cfg.target, InProcessTargetConfig)
        assert cfg.thresholds.verbatim_delta == 0.01

    def test_minimal_corpus_attacks(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            corpus:
              path: data/corpus
            attacks:
              path: data/attacks
        """)
        )
        cfg = load_config(f)
        assert cfg.corpus is not None
        assert cfg.corpus.path == "data/corpus"
        assert cfg.attacks is not None
        assert cfg.attacks.path == "data/attacks"

    def test_http_target(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            target:
              type: http
              url: https://rag.example.com/ask
              method: POST
              request_json:
                query: "{{query}}"
              response:
                answer_field: answer
              timeout_sec: 10
        """)
        )
        cfg = load_config(f)
        assert isinstance(cfg.target, HttpTargetConfig)
        assert cfg.target.url == "https://rag.example.com/ask"
        assert cfg.target.timeout_sec == 10

    def test_mock_target(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            target:
              type: mock
              answer: "test answer"
        """)
        )
        cfg = load_config(f)
        assert isinstance(cfg.target, MockTargetConfig)
        assert cfg.target.answer == "test answer"

    def test_full_config(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            version: "1"
            corpus:
              path: data/corpus
            attacks:
              path: data/attacks
            target:
              type: inprocess
              top_k: 5
            thresholds:
              verbatim_delta: 0.02
              membership_delta: 0.10
            output:
              formats: [json, sarif]
              redact: false
            run:
              jobs: 4
              cache: true
        """)
        )
        cfg = load_config(f)
        assert cfg.target.top_k == 5
        assert cfg.thresholds.verbatim_delta == 0.02
        assert cfg.output.formats == ["json", "sarif"]
        assert cfg.output.redact is False
        assert cfg.run.jobs == 4
        assert cfg.run.cache is True


# ── invalid configs → friendly errors ───────────────────────────────


class TestInvalidConfigs:
    """Configs that should fail with clear messages."""

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(ConfigError, match="Config file not found"):
            load_config(tmp_path / "nonexistent.yaml")

    def test_directory_not_file(self, tmp_path: Path):
        with pytest.raises(ConfigError, match="not a file"):
            load_config(tmp_path)

    def test_invalid_yaml_syntax(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text("target: [unclosed")
        with pytest.raises(ConfigError, match="Invalid YAML syntax"):
            load_config(f)

    def test_not_a_mapping(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text("- list\n- of\n- items")
        with pytest.raises(ConfigError, match="mapping"):
            load_config(f)

    def test_wrong_target_type(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            target:
              type: unknown_type
        """)
        )
        with pytest.raises(ConfigError, match="Config validation failed"):
            load_config(f)

    def test_wrong_field_type(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            target:
              type: inprocess
              top_k: "not_a_number"
        """)
        )
        with pytest.raises(ConfigError, match="Config validation failed"):
            load_config(f)

    def test_http_missing_url(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            target:
              type: http
        """)
        )
        with pytest.raises(ConfigError, match="Config validation failed"):
            load_config(f)

    def test_negative_timeout(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            target:
              type: http
              url: https://x.com/ask
              timeout_sec: -5
        """)
        )
        with pytest.raises(ConfigError, match="Config validation failed"):
            load_config(f)

    def test_threshold_out_of_range(self, tmp_path: Path):
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            thresholds:
              verbatim_delta: 2.0
        """)
        )
        with pytest.raises(ConfigError, match="Config validation failed"):
            load_config(f)


# ── env-var interpolation ────────────────────────────────────────────


class TestEnvVarInterpolation:
    """Environment variable substitution in config values."""

    def test_dollar_var_syntax(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "secret123")
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            target:
              type: http
              url: https://api.example.com/ask
              headers:
                Authorization: "Bearer ${MY_TOKEN}"
        """)
        )
        cfg = load_config(f)
        assert isinstance(cfg.target, HttpTargetConfig)
        assert cfg.target.headers["Authorization"] == "Bearer secret123"

    def test_env_colon_syntax(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("API_KEY", "key-abc")
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            target:
              type: http
              url: https://api.example.com/ask
              headers:
                X-Api-Key: "${ENV:API_KEY}"
        """)
        )
        cfg = load_config(f)
        assert isinstance(cfg.target, HttpTargetConfig)
        assert cfg.target.headers["X-Api-Key"] == "key-abc"

    def test_missing_env_var_resolves_empty(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_VAR_12345", raising=False)
        f = tmp_path / "c.yaml"
        f.write_text(
            dedent("""\
            target:
              type: http
              url: https://api.example.com/ask
              headers:
                X-Missing: "${NONEXISTENT_VAR_12345}"
        """)
        )
        cfg = load_config(f)
        assert isinstance(cfg.target, HttpTargetConfig)
        assert cfg.target.headers["X-Missing"] == ""


# ── JSON Schema ──────────────────────────────────────────────────────


class TestJsonSchema:
    """JSON Schema generation from Pydantic models."""

    def test_schema_is_valid_json(self):
        schema = ConfigRoot.model_json_schema()
        # Roundtrip through JSON to ensure it's valid
        text = json.dumps(schema, indent=2)
        parsed = json.loads(text)
        assert parsed["type"] == "object"
        assert "properties" in parsed

    def test_schema_has_target(self):
        schema = ConfigRoot.model_json_schema()
        props = schema.get("properties", {})
        assert "target" in props

    def test_schema_descriptions(self):
        schema = ConfigRoot.model_json_schema()
        # Top-level corpus should have description
        corpus_ref = schema.get("$defs", {}).get("CorpusConfig", {})
        path_desc = corpus_ref.get("properties", {}).get("path", {}).get("description")
        assert path_desc is not None


# ── backward compat ─────────────────────────────────────────────────


class TestBackwardCompat:
    """Old import paths still work."""

    def test_config_alias(self):
        from ragleaklab.config import Config

        assert Config is ConfigRoot

    def test_old_import_paths(self):
        from ragleaklab.config import (  # noqa: F401
            AttacksConfig,
            CorpusConfig,
            HttpTargetConfig,
            InProcessTargetConfig,
            ThresholdsConfig,
            load_config,
        )

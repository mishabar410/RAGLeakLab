"""Tests for configuration loading and HTTP target with config."""

from pathlib import Path
from textwrap import dedent

import responses

from ragleaklab.attacks import TestCase, run_all_with_target
from ragleaklab.config import (
    HttpTargetConfig,
    InProcessTargetConfig,
    load_config,
)
from ragleaklab.targets import HttpTarget


class TestConfigLoading:
    """Tests for config file loading."""

    def test_load_minimal_config(self, tmp_path: Path):
        """Loads minimal config with defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent("""
            corpus:
              path: data/corpus
            attacks:
              path: data/attacks
            """)
        )

        cfg = load_config(config_file)

        assert cfg.corpus is not None
        assert cfg.corpus.path == "data/corpus"
        assert cfg.attacks is not None
        assert cfg.attacks.path == "data/attacks"
        assert isinstance(cfg.target, InProcessTargetConfig)

    def test_load_http_target_config(self, tmp_path: Path):
        """Loads config with HTTP target."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent("""
            corpus:
              path: data/corpus
            attacks:
              path: data/attacks
            target:
              type: http
              url: http://localhost:8000/ask
              method: POST
              request_json:
                question: "{{query}}"
              response:
                answer_field: response
            """)
        )

        cfg = load_config(config_file)

        assert isinstance(cfg.target, HttpTargetConfig)
        assert cfg.target.url == "http://localhost:8000/ask"
        assert cfg.target.request_json == {"question": "{{query}}"}
        assert cfg.target.response == {"answer_field": "response"}

    def test_env_var_substitution(self, tmp_path: Path, monkeypatch):
        """Substitutes environment variables in config."""
        monkeypatch.setenv("MY_TOKEN", "secret123")
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent("""
            corpus:
              path: data/corpus
            attacks:
              path: data/attacks
            target:
              type: http
              url: http://localhost:8000/ask
              headers:
                Authorization: "Bearer ${MY_TOKEN}"
            """)
        )

        cfg = load_config(config_file)

        assert isinstance(cfg.target, HttpTargetConfig)
        assert cfg.target.headers["Authorization"] == "Bearer secret123"

    def test_thresholds_config(self, tmp_path: Path):
        """Loads custom thresholds."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent("""
            corpus:
              path: data/corpus
            attacks:
              path: data/attacks
            thresholds:
              verbatim_delta: 0.02
              membership_delta: 0.10
            """)
        )

        cfg = load_config(config_file)

        assert cfg.thresholds.verbatim_delta == 0.02
        assert cfg.thresholds.membership_delta == 0.10


class TestHttpTargetFromConfig:
    """Tests for HttpTarget.from_config."""

    @responses.activate
    def test_from_config_with_template(self, tmp_path: Path):
        """HttpTarget.from_config uses request_json template."""
        responses.add(
            responses.POST,
            "http://localhost:8000/ask",
            json={"response": "The answer is 42."},
            status=200,
        )

        cfg = HttpTargetConfig(
            type="http",
            url="http://localhost:8000/ask",
            request_json={"question": "{{query}}"},
            response={"answer_field": "response"},
        )

        target = HttpTarget.from_config(cfg)
        response = target.ask("What is the meaning of life?")

        assert response.answer == "The answer is 42."
        # Verify request body had template substituted
        assert responses.calls[0].request.body is not None
        import json

        body = json.loads(responses.calls[0].request.body)
        assert body == {"question": "What is the meaning of life?"}

    @responses.activate
    def test_runner_with_http_config(self, tmp_path: Path):
        """run_all_with_target works with HttpTarget from config."""
        responses.add(
            responses.POST,
            "http://localhost:8000/ask",
            json={"answer": "Secret data here"},
            status=200,
        )

        cfg = HttpTargetConfig(
            type="http",
            url="http://localhost:8000/ask",
            request_json={"q": "{{query}}"},
            response={"answer_field": "answer"},
        )

        target = HttpTarget.from_config(cfg)
        cases = [
            TestCase(
                test_id="config_test_01",
                threat="canary",
                query="Give me secrets",
                strategy="direct_ask",
            )
        ]

        artifacts = run_all_with_target(target, cases)

        assert len(artifacts) == 1
        assert artifacts[0].answer == "Secret data here"

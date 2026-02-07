"""Tests for cassette record/replay in HttpTarget.

Verifies:
- CassetteRecorder writes JSONL with correct format
- CassetteReplayer reads records and matches by request hash
- HttpTarget in replay mode returns cassette data without network
- Replay mode does NOT make network calls (monkeypatched socket)
- normalize_request produces deterministic hashes
- Sensitive headers are redacted in cassettes
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from ragleaklab.targets.cassette import (
    CassetteLookupError,
    CassetteRecord,
    CassetteRecorder,
    CassetteReplayer,
    _filter_headers,
    normalize_request,
)
from ragleaklab.targets.http import HttpTarget

# ── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture()
def cassette_dir(tmp_path: Path) -> Path:
    """Temporary directory for cassette files."""
    d = tmp_path / "cassettes"
    d.mkdir()
    return d


def _make_cassette_file(path: Path, records: list[dict]) -> Path:
    """Write a cassette JSONL fixture."""
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    return path


def _sample_record(query: str = "what is the secret?") -> dict:
    """Build a sample cassette record dict."""
    body = {"query": query}
    req_hash = normalize_request("POST", "https://rag.example.com/ask", body)
    return {
        "request": {
            "method": "POST",
            "url": "https://rag.example.com/ask",
            "body": json.dumps(body, sort_keys=True),
            "headers_filtered": {"Content-Type": "application/json"},
        },
        "response": {
            "status": 200,
            "body": json.dumps({"answer": f"reply to: {query}", "context": "some ctx"}),
            "parsed": {"answer": f"reply to: {query}", "context": "some ctx"},
        },
        "meta": {
            "ts": "2025-01-01T00:00:00+00:00",
            "request_hash": req_hash,
        },
    }


# ── normalize_request ────────────────────────────────────────────────


class TestNormalizeRequest:
    """Tests for deterministic request hashing."""

    def test_same_input_same_hash(self) -> None:
        h1 = normalize_request("POST", "https://x.com/a", {"q": "hi"})
        h2 = normalize_request("POST", "https://x.com/a", {"q": "hi"})
        assert h1 == h2

    def test_different_body_different_hash(self) -> None:
        h1 = normalize_request("POST", "https://x.com/a", {"q": "hello"})
        h2 = normalize_request("POST", "https://x.com/a", {"q": "world"})
        assert h1 != h2

    def test_method_case_insensitive(self) -> None:
        h1 = normalize_request("post", "https://x.com/a", {"q": "hi"})
        h2 = normalize_request("POST", "https://x.com/a", {"q": "hi"})
        assert h1 == h2

    def test_dict_key_order_irrelevant(self) -> None:
        h1 = normalize_request("POST", "https://x.com/a", {"a": "1", "b": "2"})
        h2 = normalize_request("POST", "https://x.com/a", {"b": "2", "a": "1"})
        assert h1 == h2

    def test_none_body(self) -> None:
        h = normalize_request("GET", "https://x.com/a", None)
        assert isinstance(h, str) and len(h) == 64


# ── header redaction ─────────────────────────────────────────────────


class TestHeaderRedaction:
    """Tests for sensitive header filtering."""

    def test_authorization_redacted(self) -> None:
        filtered = _filter_headers({"Authorization": "Bearer secret123"})
        assert filtered["Authorization"] == "***REDACTED***"

    def test_content_type_not_redacted(self) -> None:
        filtered = _filter_headers({"Content-Type": "application/json"})
        assert filtered["Content-Type"] == "application/json"

    def test_multiple_sensitive_headers(self) -> None:
        filtered = _filter_headers(
            {
                "Authorization": "Bearer x",
                "X-Api-Key": "key123",
                "Cookie": "session=abc",
                "Accept": "application/json",
            }
        )
        assert filtered["Authorization"] == "***REDACTED***"
        assert filtered["X-Api-Key"] == "***REDACTED***"
        assert filtered["Cookie"] == "***REDACTED***"
        assert filtered["Accept"] == "application/json"


# ── CassetteRecorder ─────────────────────────────────────────────────


class TestCassetteRecorder:
    """Tests for cassette writing."""

    def test_append_creates_file(self, cassette_dir: Path) -> None:
        path = cassette_dir / "test.jsonl"
        recorder = CassetteRecorder(path)
        record = CassetteRecord.from_dict(_sample_record())
        recorder.append(record)
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1

    def test_append_multiple(self, cassette_dir: Path) -> None:
        path = cassette_dir / "multi.jsonl"
        recorder = CassetteRecorder(path)
        for q in ["q1", "q2", "q3"]:
            record = CassetteRecord.from_dict(_sample_record(q))
            recorder.append(record)
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_record_roundtrip(self, cassette_dir: Path) -> None:
        path = cassette_dir / "roundtrip.jsonl"
        recorder = CassetteRecorder(path)
        original = _sample_record("roundtrip test")
        recorder.append(CassetteRecord.from_dict(original))
        parsed = json.loads(path.read_text().strip())
        assert parsed["meta"]["request_hash"] == original["meta"]["request_hash"]
        assert parsed["response"]["parsed"]["answer"] == "reply to: roundtrip test"


# ── CassetteReplayer ─────────────────────────────────────────────────


class TestCassetteReplayer:
    """Tests for cassette reading and lookup."""

    def test_lookup_found(self, cassette_dir: Path) -> None:
        path = cassette_dir / "found.jsonl"
        rec = _sample_record("hello")
        _make_cassette_file(path, [rec])
        replayer = CassetteReplayer(path)
        result = replayer.lookup("POST", "https://rag.example.com/ask", {"query": "hello"})
        assert result.response["parsed"]["answer"] == "reply to: hello"

    def test_lookup_not_found_raises(self, cassette_dir: Path) -> None:
        path = cassette_dir / "miss.jsonl"
        _make_cassette_file(path, [_sample_record("existing")])
        replayer = CassetteReplayer(path)
        with pytest.raises(CassetteLookupError, match="No cassette match"):
            replayer.lookup("POST", "https://rag.example.com/ask", {"query": "missing"})

    def test_count(self, cassette_dir: Path) -> None:
        path = cassette_dir / "count.jsonl"
        records = [_sample_record(f"q{i}") for i in range(5)]
        _make_cassette_file(path, records)
        replayer = CassetteReplayer(path)
        assert replayer.count == 5

    def test_file_not_found(self, cassette_dir: Path) -> None:
        with pytest.raises(FileNotFoundError):
            CassetteReplayer(cassette_dir / "nonexistent.jsonl")


# ── HttpTarget replay ───────────────────────────────────────────────


class TestHttpTargetReplay:
    """Tests for HttpTarget in replay mode — no network."""

    def test_replay_returns_cassette_answer(self, cassette_dir: Path) -> None:
        path = cassette_dir / "replay.jsonl"
        _make_cassette_file(path, [_sample_record("what is the secret?")])

        target = HttpTarget(
            url="https://rag.example.com/ask",
            http_mode="replay",
            cassette_path=str(path),
        )
        resp = target.ask("what is the secret?")
        assert resp.answer == "reply to: what is the secret?"
        assert resp.metadata.get("cassette") == "replay"

    def test_replay_no_network(self, cassette_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Monkeypatch socket.connect to prove no network calls happen."""
        path = cassette_dir / "nonet.jsonl"
        _make_cassette_file(path, [_sample_record("offline query")])

        def _block_connect(*args, **kwargs):
            raise RuntimeError("Network should not be accessed in replay mode!")

        monkeypatch.setattr(socket.socket, "connect", _block_connect)

        target = HttpTarget(
            url="https://rag.example.com/ask",
            http_mode="replay",
            cassette_path=str(path),
        )
        resp = target.ask("offline query")
        assert resp.answer == "reply to: offline query"

    def test_replay_miss_raises(self, cassette_dir: Path) -> None:
        path = cassette_dir / "miss.jsonl"
        _make_cassette_file(path, [_sample_record("recorded")])

        target = HttpTarget(
            url="https://rag.example.com/ask",
            http_mode="replay",
            cassette_path=str(path),
        )
        with pytest.raises(CassetteLookupError):
            target.ask("not recorded")


# ── HttpTarget record ───────────────────────────────────────────────


class TestHttpTargetRecord:
    """Tests for HttpTarget in record mode (with mocked HTTP)."""

    def test_record_writes_cassette(
        self, cassette_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mock requests.post and verify cassette is written."""
        import requests as req_mod

        class MockResponse:
            status_code = 200
            text = '{"answer": "mocked"}'

            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                return {"answer": "mocked"}

        monkeypatch.setattr(req_mod, "post", lambda *a, **kw: MockResponse())

        cassette_file = cassette_dir / "recorded.jsonl"
        target = HttpTarget(
            url="https://rag.example.com/ask",
            require_allowlist=False,
            http_mode="record",
            cassette_path=str(cassette_file),
        )
        resp = target.ask("record me")
        assert resp.answer == "mocked"

        # Verify cassette was written
        assert cassette_file.exists()
        data = json.loads(cassette_file.read_text().strip())
        assert data["response"]["parsed"]["answer"] == "mocked"
        assert data["request"]["method"] == "POST"

    def test_record_then_replay(self, cassette_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Record a cassette, then replay it without network."""
        import requests as req_mod

        class MockResponse:
            status_code = 200
            text = '{"answer": "end-to-end"}'

            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                return {"answer": "end-to-end"}

        monkeypatch.setattr(req_mod, "post", lambda *a, **kw: MockResponse())

        cassette_file = cassette_dir / "e2e.jsonl"

        # Record
        recorder_target = HttpTarget(
            url="https://rag.example.com/ask",
            require_allowlist=False,
            http_mode="record",
            cassette_path=str(cassette_file),
        )
        recorder_target.ask("e2e test")

        # Replay — block network
        def _block_connect(*args, **kwargs):
            raise RuntimeError("Network blocked!")

        monkeypatch.setattr(socket.socket, "connect", _block_connect)

        replay_target = HttpTarget(
            url="https://rag.example.com/ask",
            http_mode="replay",
            cassette_path=str(cassette_file),
        )
        resp = replay_target.ask("e2e test")
        assert resp.answer == "end-to-end"


# ── config integration ───────────────────────────────────────────────


class TestCassetteConfig:
    """Tests for cassette config validation."""

    def test_missing_cassette_path_raises(self) -> None:
        with pytest.raises(ValueError, match="cassette_path is required"):
            HttpTarget(
                url="https://rag.example.com/ask",
                require_allowlist=False,
                http_mode="record",
                cassette_path=None,
            )

    def test_replay_missing_path_raises(self) -> None:
        with pytest.raises(ValueError, match="cassette_path is required"):
            HttpTarget(
                url="https://rag.example.com/ask",
                http_mode="replay",
                cassette_path=None,
            )

    def test_live_mode_works_without_cassette(self) -> None:
        """Live mode should work normally without cassette_path."""
        target = HttpTarget(
            url="https://rag.example.com/ask",
            require_allowlist=False,
            http_mode="live",
        )
        assert target.http_mode == "live"
        assert target._recorder is None
        assert target._replayer is None

    def test_from_config_wires_mode(self, cassette_dir: Path) -> None:
        """from_config passes http_mode and cassette_path."""
        from ragleaklab.config.schema import HttpTargetConfig

        path = cassette_dir / "cfg.jsonl"
        _make_cassette_file(path, [_sample_record("cfg test")])

        config = HttpTargetConfig(
            url="https://rag.example.com/ask",
            require_allowlist=False,
            http_mode="replay",
            cassette_path=str(path),
        )
        target = HttpTarget.from_config(config)
        assert target.http_mode == "replay"
        resp = target.ask("cfg test")
        assert resp.answer == "reply to: cfg test"

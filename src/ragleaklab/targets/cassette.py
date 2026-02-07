"""Record/replay cassettes for HTTP targets.

Cassette format: JSONL file where each line is::

    {
      "request": {"method": "POST", "url": "...", "body": "...", "headers_filtered": {...}},
      "response": {"status": 200, "body": "...", "parsed": {...}},
      "meta": {"ts": "...", "request_hash": "..."}
    }
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ── sensitive header redaction ───────────────────────────────────────

_SENSITIVE_HEADERS = re.compile(
    r"^(authorization|x-api-key|cookie|x-auth-token|proxy-authorization)$",
    re.IGNORECASE,
)


def _filter_headers(headers: dict[str, str]) -> dict[str, str]:
    """Redact sensitive headers for cassette storage."""
    filtered: dict[str, str] = {}
    for k, v in headers.items():
        if _SENSITIVE_HEADERS.match(k):
            filtered[k] = "***REDACTED***"
        else:
            filtered[k] = v
    return filtered


# ── request normalization ────────────────────────────────────────────


def normalize_request(
    method: str,
    url: str,
    body: dict | str | None,
) -> str:
    """Produce a deterministic hash for a request.

    Normalizes JSON body via sorted-key serialization.
    Volatile headers are excluded (only method + url + body matter).
    """
    parts: list[str] = [method.upper(), url]
    if body is not None:
        if isinstance(body, dict):
            parts.append(json.dumps(body, sort_keys=True, separators=(",", ":")))
        else:
            parts.append(str(body))
    canonical = "\n".join(parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── cassette record ─────────────────────────────────────────────────


class CassetteRecord:
    """Single request/response pair in a cassette."""

    __slots__ = ("meta", "request", "response")

    def __init__(
        self,
        request: dict[str, Any],
        response: dict[str, Any],
        meta: dict[str, Any],
    ) -> None:
        self.request = request
        self.response = response
        self.meta = meta

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "response": self.response,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CassetteRecord:
        return cls(
            request=data["request"],
            response=data["response"],
            meta=data.get("meta", {}),
        )

    @classmethod
    def create(
        cls,
        *,
        method: str,
        url: str,
        body: dict | str | None,
        headers: dict[str, str],
        status: int,
        response_body: str,
        parsed: dict[str, Any],
    ) -> CassetteRecord:
        """Build a record from raw HTTP data."""
        request_hash = normalize_request(method, url, body)
        return cls(
            request={
                "method": method.upper(),
                "url": url,
                "body": body
                if isinstance(body, str)
                else json.dumps(body, sort_keys=True)
                if body
                else None,
                "headers_filtered": _filter_headers(headers),
            },
            response={
                "status": status,
                "body": response_body,
                "parsed": parsed,
            },
            meta={
                "ts": datetime.now(tz=UTC).isoformat(),
                "request_hash": request_hash,
            },
        )


# ── recorder ─────────────────────────────────────────────────────────


class CassetteRecorder:
    """Append cassette records to a JSONL file."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: CassetteRecord) -> None:
        """Append a record to the cassette file."""
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), separators=(",", ":")) + "\n")


# ── replayer ─────────────────────────────────────────────────────────


class CassetteLookupError(LookupError):
    """Raised when no matching cassette record is found for a request."""

    pass


class CassetteReplayer:
    """Look up responses from a pre-recorded JSONL cassette."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._index: dict[str, CassetteRecord] = {}
        self._load()

    def _load(self) -> None:
        """Load cassette and build request_hash index."""
        if not self.path.exists():
            raise FileNotFoundError(f"Cassette file not found: {self.path}")

        with open(self.path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON on line {line_no} of {self.path}: {exc}"
                    ) from exc
                record = CassetteRecord.from_dict(data)
                req_hash = record.meta.get("request_hash")
                if req_hash:
                    self._index[req_hash] = record

    def lookup(self, method: str, url: str, body: dict | str | None) -> CassetteRecord:
        """Find a recorded response matching the request.

        Args:
            method: HTTP method.
            url: Request URL.
            body: Request body.

        Returns:
            Matching CassetteRecord.

        Raises:
            CassetteLookupError: If no matching record is found.
        """
        request_hash = normalize_request(method, url, body)
        record = self._index.get(request_hash)
        if record is None:
            raise CassetteLookupError(
                f"No cassette match for {method} {url} (hash={request_hash[:12]}…). "
                f"Cassette has {len(self._index)} recorded requests. "
                f"Re-record with http_mode: record"
            )
        return record

    @property
    def count(self) -> int:
        """Number of recorded requests in the cassette."""
        return len(self._index)

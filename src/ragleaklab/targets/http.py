"""HTTP target adapter for external RAG services."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests

from ragleaklab.targets.base import TargetResponse
from ragleaklab.targets.ssrf import SSRFValidationError, validate_url

__all__ = ["AllowlistRequiredError", "HttpTarget", "SSRFValidationError"]

if TYPE_CHECKING:
    from ragleaklab.config import HttpTargetConfig


class AllowlistRequiredError(ValueError):
    """Raised when HTTP target requires explicit allowlist but none provided."""

    pass


class HttpTarget:
    """Target adapter for HTTP-based RAG services.

    Sends queries to an external RAG service via HTTP POST
    and parses the response according to configurable field mappings.

    Security features:
    - Allowlist enforcement (require_allowlist=True by default)
    - Localhost blocking (allow_localhost=False by default)
    - Rate limiting (max_rps controls requests per second)
    """

    def __init__(
        self,
        url: str,
        method: str = "POST",
        query_field: str = "query",
        answer_field: str = "answer",
        context_field: str | None = "context",
        retrieved_ids_field: str | None = "retrieved_ids",
        scores_field: str | None = "scores",
        headers: dict | None = None,
        timeout: float = 30.0,
        request_json: dict[str, str] | None = None,
        allowed_domains: list[str] | None = None,
        require_allowlist: bool = True,
        allow_localhost: bool = False,
        max_rps: float = 1.0,
    ) -> None:
        """Initialize HTTP target.

        Args:
            url: The URL of the RAG service endpoint.
            method: HTTP method (POST or GET).
            query_field: Field name for query in request body.
            answer_field: Field name for answer in response.
            context_field: Optional field for context in response.
            retrieved_ids_field: Optional field for retrieved IDs.
            scores_field: Optional field for scores.
            headers: Optional HTTP headers.
            timeout: Request timeout in seconds (default 30s).
            request_json: Optional template dict with {{query}} placeholders.
            allowed_domains: Optional list of allowed domains for SSRF protection.
            require_allowlist: If True, raise error when allowed_domains is empty.
            allow_localhost: If True, allow localhost/127.0.0.1 targets.
            max_rps: Maximum requests per second (rate limiting).

        Raises:
            AllowlistRequiredError: If require_allowlist=True and no allowed_domains.
            SSRFValidationError: If URL fails SSRF validation.
        """
        self.allowed_domains = allowed_domains or []
        self.require_allowlist = require_allowlist
        self.allow_localhost = allow_localhost
        self.max_rps = max_rps
        self._last_request_time: float = 0.0

        # Check localhost
        parsed = urlparse(url)
        is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0")
        if is_localhost and not allow_localhost:
            raise SSRFValidationError(
                f"Localhost URLs blocked by default. Set allow_localhost=True to enable: {url}"
            )

        # Check allowlist requirement
        if require_allowlist and not self.allowed_domains:
            raise AllowlistRequiredError(
                "HTTP target requires explicit allowed_domains list. "
                "Set require_allowlist=False to disable (not recommended) or "
                "add allowed_domains=['example.com'] to your config."
            )

        # Validate URL for SSRF before storing (skip for localhost when allowed)
        if not (is_localhost and allow_localhost):
            validate_url(url, self.allowed_domains if self.allowed_domains else None)

        self.url = url
        self.method = method.upper()
        self.query_field = query_field
        self.answer_field = answer_field
        self.context_field = context_field
        self.retrieved_ids_field = retrieved_ids_field
        self.scores_field = scores_field
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.request_json = request_json

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self.max_rps <= 0:
            return

        min_interval = 1.0 / self.max_rps
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            time.sleep(sleep_time)

        self._last_request_time = time.monotonic()

    @classmethod
    def from_config(cls, config: HttpTargetConfig) -> HttpTarget:
        """Create HttpTarget from config object.

        Args:
            config: HttpTargetConfig with target settings.

        Returns:
            Configured HttpTarget instance.
        """
        return cls(
            url=config.url,
            method=config.method,
            answer_field=config.response.get("answer_field", "answer"),
            context_field=config.response.get("context_field"),
            retrieved_ids_field=config.response.get("retrieved_ids_field"),
            scores_field=config.response.get("scores_field"),
            headers=config.headers if config.headers else None,
            timeout=config.timeout_sec,
            request_json=config.request_json,
            allowed_domains=config.allowed_domains if config.allowed_domains else None,
            require_allowlist=config.require_allowlist,
            allow_localhost=config.allow_localhost,
            max_rps=config.max_rps,
        )

    def _build_payload(self, query: str) -> dict:
        """Build request payload from query.

        If request_json is set, substitutes {{query}} placeholders.
        Otherwise uses simple {query_field: query} format.
        """
        if self.request_json:
            return self._substitute_template(self.request_json, query)
        return {self.query_field: query}

    def _substitute_template(self, template: dict, query: str) -> dict:
        """Recursively substitute {{query}} in template dict."""
        result = {}
        for key, value in template.items():
            if isinstance(value, str):
                result[key] = re.sub(r"\{\{query\}\}", query, value)
            elif isinstance(value, dict):
                result[key] = self._substitute_template(value, query)
            else:
                result[key] = value
        return result

    def ask(self, query: str) -> TargetResponse:
        """Query the HTTP RAG service.

        Args:
            query: The query string.

        Returns:
            TargetResponse parsed from HTTP response.

        Raises:
            requests.RequestException: On HTTP errors.
        """
        # Apply rate limiting
        self._rate_limit()

        payload = self._build_payload(query)

        if self.method == "POST":
            response = requests.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
        else:  # GET
            response = requests.get(
                self.url,
                params=payload,
                headers=self.headers,
                timeout=self.timeout,
            )

        response.raise_for_status()
        data = response.json()

        # Extract fields with defaults
        answer = data.get(self.answer_field, "")
        context = data.get(self.context_field, "") if self.context_field else ""
        retrieved_ids = data.get(self.retrieved_ids_field, []) if self.retrieved_ids_field else []
        scores = data.get(self.scores_field, []) if self.scores_field else []

        return TargetResponse(
            answer=answer,
            context=context,
            retrieved_ids=retrieved_ids,
            scores=scores,
            metadata={"raw_response": data},
        )

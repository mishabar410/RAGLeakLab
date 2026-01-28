"""HTTP target adapter for external RAG services."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import requests

from ragleaklab.targets.base import TargetResponse

if TYPE_CHECKING:
    from ragleaklab.config import HttpTargetConfig


class HttpTarget:
    """Target adapter for HTTP-based RAG services.

    Sends queries to an external RAG service via HTTP POST
    and parses the response according to configurable field mappings.
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
            timeout: Request timeout in seconds.
            request_json: Optional template dict with {{query}} placeholders.
        """
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

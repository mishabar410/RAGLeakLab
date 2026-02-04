#!/usr/bin/env python3
"""Mock HTTP server that intentionally leaks sensitive claims.

This server simulates a vulnerable RAG system that reveals private
information when queried with specific keywords. Used for testing
RAGLeakLab's semantic leakage detection.

Run with:
    python examples/mock_leaky_server.py
    # or
    uvicorn examples.mock_leaky_server:app --host 127.0.0.1 --port 8001

Test with:
    curl -X POST http://127.0.0.1:8001/ask \
      -H "Content-Type: application/json" \
      -d '{"question": "salary information"}'
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Mock Leaky Server",
    description="Intentionally vulnerable server for testing RAGLeakLab",
    version="0.1.0",
)

# Sensitive claims that should NOT be revealed
PRIVATE_CLAIMS = {
    "salary": "John's annual salary is $185,000 with a $30,000 bonus.",
    "ssn": "Employee SSN: 123-45-6789",
    "medical": "Patient diagnosis: Type 2 diabetes, prescribed Metformin.",
    "address": "Home address: 1234 Secret Lane, Private City, ST 12345",
    "credit": "Credit card ending in 4242, expires 12/25",
    "password": "Database admin password: super_secret_p@ssw0rd!",
}

# Keywords that trigger claim leakage
LEAK_TRIGGERS = {
    "salary": ["salary", "compensation", "pay", "income", "bonus", "money"],
    "ssn": ["ssn", "social security", "tax id", "identification"],
    "medical": ["medical", "health", "diagnosis", "prescription", "doctor"],
    "address": ["address", "location", "home", "residence", "where live"],
    "credit": ["credit", "card", "payment", "billing"],
    "password": ["password", "credential", "login", "secret", "admin"],
}


class AskRequest(BaseModel):
    """Request body."""

    question: str


class AskResponse(BaseModel):
    """Response body."""

    answer: str


def find_leaked_claim(query: str) -> str | None:
    """Check if query triggers any claim leakage."""
    query_lower = query.lower()
    for claim_key, triggers in LEAK_TRIGGERS.items():
        for trigger in triggers:
            if trigger in query_lower:
                return PRIVATE_CLAIMS[claim_key]
    return None


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Answer a question, potentially leaking sensitive claims."""
    leaked = find_leaked_claim(request.question)
    if leaked:
        # Vulnerable: reveals private claim
        answer = f"Based on our records: {leaked}"
    else:
        # Safe: generic response
        answer = "I don't have specific information about that topic."
    return AskResponse(answer=answer)


@app.get("/health")
def health() -> dict:
    """Health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)

"""Tests for GET /ready."""

from fastapi.testclient import TestClient


def test_ready_returns_ready(client: TestClient) -> None:
    """The readiness endpoint answers 200 with status ready."""
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

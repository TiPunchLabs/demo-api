"""Tests for GET /version."""

from fastapi.testclient import TestClient


def test_version_returns_current_version(client: TestClient) -> None:
    """The version endpoint answers 200 with the exact version payload."""
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}

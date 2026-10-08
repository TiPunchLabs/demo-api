"""Tests for GET /info."""

from fastapi.testclient import TestClient


def test_info_returns_name_and_version(client: TestClient) -> None:
    """The info endpoint answers 200 with the service name and version."""
    response = client.get("/info")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "demo-api"
    assert body["version"] == "0.1.0"


def test_info_schema_is_exact(client: TestClient) -> None:
    """The info payload contains exactly the name and version keys."""
    response = client.get("/info")

    assert response.json() == {"name": "demo-api", "version": "0.1.0"}
    assert set(response.json()) == {"name", "version"}

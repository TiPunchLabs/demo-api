"""Tests for GET /version."""

from importlib import metadata

from fastapi.testclient import TestClient


def test_version_returns_current_version(client: TestClient) -> None:
    """The version endpoint answers 200 with the exact version payload."""
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}


def test_version_matches_package_metadata(client: TestClient) -> None:
    """The endpoint and the OpenAPI schema both report the installed package version."""
    expected = metadata.version("demo-api")

    assert client.get("/version").json() == {"version": expected}
    assert client.get("/openapi.json").json()["info"]["version"] == expected

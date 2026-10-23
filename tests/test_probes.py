"""Tests for scenario S-001: the service probes answer in sequence."""

from fastapi.testclient import TestClient


def test_probes_answer_in_sequence(client: TestClient) -> None:
    """GET /health then GET /ready both answer 200 with their exact body."""
    health = client.get("/health")
    ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}

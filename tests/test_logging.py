"""Tests for application logging."""

import logging

import pytest
from fastapi.testclient import TestClient

from demo_api.main import create_app


def _task_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Return the records emitted by the tasks module."""
    return [r for r in caplog.records if r.name == "demo_api.routes.tasks"]


def test_logs_task_changes(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Every task change logs one INFO record with action and id."""
    caplog.set_level(logging.INFO)
    client.post("/tasks", json={"title": "a"})
    client.put("/tasks/1", json={"title": "b"})
    client.patch("/tasks/1", json={"completed": True})
    client.post("/tasks/1/toggle")
    client.post("/tasks/1/duplicate")
    client.post("/tasks/bulk", json={"tasks": [{"title": "x"}, {"title": "y"}]})
    client.delete("/tasks/1")
    client.post("/tasks/2/toggle")
    client.delete("/tasks", params={"completed": "true"})
    messages = [(r.levelname, r.getMessage()) for r in _task_records(caplog)]
    assert messages == [
        ("INFO", "task created id=1"),
        ("INFO", "task replaced id=1"),
        ("INFO", "task patched id=1"),
        ("INFO", "task toggled id=1"),
        ("INFO", "task duplicated id=2 from id=1"),
        ("INFO", "task created id=3"),
        ("INFO", "task created id=4"),
        ("INFO", "task deleted id=1"),
        ("INFO", "task toggled id=2"),
        ("INFO", "task deleted id=2"),
    ]


def test_logs_not_found_as_warning(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """A 404 on a missing task logs a WARNING with the id."""
    caplog.set_level(logging.INFO)
    assert client.delete("/tasks/42").status_code == 404
    messages = [(r.levelname, r.getMessage()) for r in _task_records(caplog)]
    assert messages == [("WARNING", "task not found id=42")]


def test_reads_and_validation_errors_log_no_change(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """GET requests and 422 responses emit no task record."""
    caplog.set_level(logging.INFO)
    client.get("/tasks")
    client.get("/tasks/stats")
    client.post("/tasks", json={})
    client.delete("/tasks")
    assert _task_records(caplog) == []


def test_logs_never_contain_titles(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Titles never appear in logged messages."""
    caplog.set_level(logging.INFO)
    title = "SECRET-distinctive-title"
    client.post("/tasks", json={"title": title})
    client.put("/tasks/1", json={"title": title})
    client.post("/tasks/1/duplicate")
    assert caplog.records
    assert all(title not in r.getMessage() for r in caplog.records)


def test_unhandled_exception_logs_error_with_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An unhandled exception logs an ERROR with exc_info and returns 500."""
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        """Raise an unexpected error."""
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/boom")
    assert response.status_code == 500
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert errors
    assert errors[0].exc_info is not None
    assert errors[0].name == "demo_api.main"

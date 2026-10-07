"""Tests for the /tasks CRUD."""

import pytest
from fastapi.testclient import TestClient


def _create(client: TestClient, title: str = "Example") -> dict:
    """Create a task through the API and return its JSON body."""
    response = client.post("/tasks", json={"title": title})
    assert response.status_code == 201
    return response.json()


def test_list_is_empty_initially(client: TestClient) -> None:
    """A fresh app has no tasks."""
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_create_task(client: TestClient) -> None:
    """Creating a task assigns an id and defaults completed to false."""
    assert _create(client) == {"id": 1, "title": "Example", "completed": False}


def test_create_assigns_incremental_ids(client: TestClient) -> None:
    """Ids increase with each creation."""
    assert [_create(client, t)["id"] for t in ("a", "b")] == [1, 2]


@pytest.mark.parametrize("payload", [{}, {"title": ""}, {"title": "x" * 201}])
def test_create_rejects_invalid_payload(client: TestClient, payload: dict) -> None:
    """Missing, empty or too long titles are rejected."""
    assert client.post("/tasks", json=payload).status_code == 422


def test_read_tasks(client: TestClient) -> None:
    """Created tasks are returned by the list and by id."""
    task = _create(client)

    assert client.get("/tasks").json() == [task]
    response = client.get(f"/tasks/{task['id']}")
    assert response.status_code == 200
    assert response.json() == task


def test_update_task(client: TestClient) -> None:
    """PUT replaces the title and completion state, keeping the id."""
    task = _create(client)

    response = client.put(f"/tasks/{task['id']}", json={"title": "Done", "completed": True})

    assert response.status_code == 200
    assert response.json() == {"id": task["id"], "title": "Done", "completed": True}
    assert client.get(f"/tasks/{task['id']}").json()["completed"] is True


def test_delete_task(client: TestClient) -> None:
    """A deleted task is no longer readable."""
    task = _create(client)

    response = client.delete(f"/tasks/{task['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/tasks/{task['id']}").status_code == 404
    assert client.get("/tasks").json() == []


def test_toggle_task(client: TestClient) -> None:
    """Toggling a task inverts its completion state."""
    task = _create(client)

    response = client.post(f"/tasks/{task['id']}/toggle")

    assert response.status_code == 200
    assert response.json()["completed"] is True


@pytest.mark.parametrize(
    ("method", "body"),
    [("get", None), ("put", {"title": "x"}), ("delete", None)],
)
def test_unknown_task_returns_404(client: TestClient, method: str, body: dict | None) -> None:
    """Reading, updating or deleting a missing task answers 404."""
    response = client.request(method, "/tasks/999", json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": "Task 999 not found"}

"""Tests for the /tasks CRUD."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from demo_api.schemas import TaskIn
from demo_api.storage import TaskStore


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


@pytest.mark.parametrize(
    ("method", "body"),
    [("get", None), ("put", {"title": "x"}), ("delete", None)],
)
def test_unknown_task_returns_404(client: TestClient, method: str, body: dict | None) -> None:
    """Reading, updating or deleting a missing task answers 404."""
    response = client.request(method, "/tasks/999", json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": "Task 999 not found"}


def _bulk(client: TestClient, titles: list[str]) -> Any:
    """Post a bulk creation request."""
    return client.post("/tasks/bulk", json={"tasks": [{"title": t} for t in titles]})


def test_stats_empty(client: TestClient) -> None:
    """Stats of an empty store are all zero."""
    response = client.get("/tasks/stats")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "completed": 0, "pending": 0}


def test_stats_non_empty(client: TestClient) -> None:
    """Stats count completed and pending tasks."""
    _bulk(client, ["a", "b", "c"])
    client.put("/tasks/1", json={"title": "a", "completed": True})

    assert client.get("/tasks/stats").json() == {"total": 3, "completed": 1, "pending": 2}


def test_bulk_create_success(client: TestClient) -> None:
    """Bulk creation keeps request order and assigns consecutive ids."""
    _create(client, "first")
    response = _bulk(client, ["a", "b", "c"])

    assert response.status_code == 201
    assert [(t["id"], t["title"]) for t in response.json()] == [(2, "a"), (3, "b"), (4, "c")]
    assert len(client.get("/tasks").json()) == 4


def test_bulk_create_rejects_empty_list(client: TestClient) -> None:
    """Zero tasks is rejected."""
    assert _bulk(client, []).status_code == 422


def test_bulk_create_limits(client: TestClient) -> None:
    """51 tasks are rejected and create nothing; 50 are accepted."""
    assert _bulk(client, ["x"] * 51).status_code == 422
    assert client.get("/tasks").json() == []
    assert _bulk(client, ["x"] * 50).status_code == 201


def test_bulk_create_is_atomic(client: TestClient) -> None:
    """One invalid task means no task is created."""
    response = _bulk(client, ["ok", "", "also ok"])

    assert response.status_code == 422
    assert client.get("/tasks").json() == []
    assert _create(client)["id"] == 1


def test_store_create_many_is_atomic() -> None:
    """The store itself creates nothing when one item is invalid."""
    store = TaskStore()
    items = [TaskIn(title="ok"), TaskIn.model_construct(title="", completed=False)]

    with pytest.raises(ValidationError):
        store.create_many(items)

    assert store.list() == []
    assert store.create(TaskIn(title="next")).id == 1


def test_delete_completed(client: TestClient) -> None:
    """Completed tasks are deleted and pending ones kept."""
    _bulk(client, ["a", "b", "c"])
    client.put("/tasks/1", json={"title": "a", "completed": True})
    client.put("/tasks/3", json={"title": "c", "completed": True})

    response = client.delete("/tasks", params={"completed": "true"})

    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    assert [t["id"] for t in client.get("/tasks").json()] == [2]


def test_delete_completed_none_deleted(client: TestClient) -> None:
    """Nothing to delete returns zero."""
    _create(client)

    response = client.delete("/tasks", params={"completed": "true"})

    assert response.json() == {"deleted": 0}
    assert len(client.get("/tasks").json()) == 1


@pytest.mark.parametrize("params", [{}, {"completed": "false"}])
def test_delete_completed_guard(client: TestClient, params: dict) -> None:
    """Missing or false parameter is rejected and deletes nothing."""
    _create(client)
    client.put("/tasks/1", json={"title": "Example", "completed": True})

    assert client.delete("/tasks", params=params).status_code == 422
    assert len(client.get("/tasks").json()) == 1

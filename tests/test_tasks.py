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
    assert _create(client) == {
        "id": 1,
        "title": "Example",
        "completed": False,
        "priority": "medium",
    }


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
    assert response.json() == {
        "id": task["id"],
        "title": "Done",
        "completed": True,
        "priority": "medium",
    }
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
    [("get", None), ("put", {"title": "x"}), ("patch", {"title": "x"}), ("delete", None)],
)
def test_unknown_task_returns_404(client: TestClient, method: str, body: dict | None) -> None:
    """Reading, updating or deleting a missing task answers 404."""
    response = client.request(method, "/tasks/999", json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": "Task 999 not found"}


def test_create_and_replace_accept_priority(client: TestClient) -> None:
    """POST and PUT accept an explicit priority, defaulting to medium."""
    created = client.post("/tasks", json={"title": "a", "priority": "high"}).json()
    assert created["priority"] == "high"

    replaced = client.put(f"/tasks/{created['id']}", json={"title": "a", "priority": "low"})
    assert replaced.json()["priority"] == "low"

    defaulted = client.put(f"/tasks/{created['id']}", json={"title": "a"})
    assert defaulted.json()["priority"] == "medium"


@pytest.mark.parametrize("method", ["post", "put"])
def test_invalid_priority_rejected(client: TestClient, method: str) -> None:
    """An unknown priority is rejected on POST and PUT."""
    task = _create(client)
    url = "/tasks" if method == "post" else f"/tasks/{task['id']}"

    response = client.request(method, url, json={"title": "x", "priority": "urgent"})

    assert response.status_code == 422


def test_patch_updates_provided_fields(client: TestClient) -> None:
    """PATCH with several valid fields returns the full updated task."""
    task = _create(client)

    response = client.patch(
        f"/tasks/{task['id']}", json={"title": "New", "completed": True, "priority": "high"}
    )

    assert response.status_code == 200
    expected = {"id": task["id"], "title": "New", "completed": True, "priority": "high"}
    assert response.json() == expected
    assert client.get(f"/tasks/{task['id']}").json() == expected


def test_patch_keeps_absent_fields(client: TestClient) -> None:
    """Fields missing from the PATCH body keep their value."""
    body = {"title": "Keep", "completed": True, "priority": "low"}
    task = client.post("/tasks", json=body).json()

    response = client.patch(f"/tasks/{task['id']}", json={"priority": "high"})

    assert response.json() == {**task, "priority": "high"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"foo": 1},
        {"title": None},
        {"completed": None},
        {"priority": None},
        {"title": ""},
        {"title": "x" * 201},
        {"priority": "urgent"},
    ],
)
def test_patch_rejects_invalid_payload(client: TestClient, payload: dict) -> None:
    """Empty, unknown, null or invalid PATCH bodies answer 422 and change nothing."""
    task = _create(client)

    assert client.patch(f"/tasks/{task['id']}", json=payload).status_code == 422
    assert client.get(f"/tasks/{task['id']}").json() == task

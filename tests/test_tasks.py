"""Tests for the /tasks CRUD."""

from typing import Any

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


@pytest.mark.parametrize(
    ("method", "body"),
    [("get", None), ("put", {"title": "x"}), ("delete", None)],
)
def test_unknown_task_returns_404(client: TestClient, method: str, body: dict | None) -> None:
    """Reading, updating or deleting a missing task answers 404."""
    response = client.request(method, "/tasks/999", json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": "Task 999 not found"}


def _seed(client: TestClient) -> None:
    """Create 5 tasks where tasks 2 and 4 are completed."""
    for index in range(1, 6):
        task = _create(client, f"task {index}")
        if index % 2 == 0:
            client.put(f"/tasks/{task['id']}", json={"title": task["title"], "completed": True})


def _ids(response: Any) -> list[int]:
    """Return the ids of a list response."""
    return [task["id"] for task in response.json()]


def test_list_defaults_to_twenty_sorted_by_id(client: TestClient) -> None:
    """Without parameters, at most 20 tasks are returned, sorted by id."""
    for index in range(25):
        _create(client, f"task {index}")

    response = client.get("/tasks")

    assert response.status_code == 200
    assert _ids(response) == list(range(1, 21))


def test_list_filters_completed_true(client: TestClient) -> None:
    """completed=true returns only completed tasks."""
    _seed(client)

    assert _ids(client.get("/tasks", params={"completed": "true"})) == [2, 4]


def test_list_filters_completed_false(client: TestClient) -> None:
    """completed=false returns only pending tasks."""
    _seed(client)

    assert _ids(client.get("/tasks", params={"completed": "false"})) == [1, 3, 5]


def test_list_limit_and_offset(client: TestClient) -> None:
    """Limit and offset paginate the sorted list."""
    _seed(client)

    assert _ids(client.get("/tasks", params={"limit": 2})) == [1, 2]
    assert _ids(client.get("/tasks", params={"limit": 2, "offset": 2})) == [3, 4]
    assert _ids(client.get("/tasks", params={"offset": 4})) == [5]


def test_list_pagination_applies_after_filter(client: TestClient) -> None:
    """The completed filter is applied before limit and offset."""
    _seed(client)

    params = {"completed": "false", "limit": 2, "offset": 1}
    assert _ids(client.get("/tasks", params=params)) == [3, 5]


def test_list_offset_beyond_count_returns_empty(client: TestClient) -> None:
    """An offset past the last task returns an empty list with 200."""
    _seed(client)

    response = client.get("/tasks", params={"offset": 50})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"completed": "abc"}],
)
def test_list_rejects_invalid_query(client: TestClient, params: dict) -> None:
    """Out-of-range or malformed query parameters answer 422."""
    assert client.get("/tasks", params=params).status_code == 422

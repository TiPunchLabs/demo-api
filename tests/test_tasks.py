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


def test_toggle_task(client: TestClient) -> None:
    """Toggling a task inverts its completion state."""
    task = _create(client)

    response = client.post(f"/tasks/{task['id']}/toggle")

    assert response.status_code == 200
    assert response.json() == {
        "id": task["id"],
        "title": task["title"],
        "completed": True,
        "priority": "medium",
    }


def test_toggle_task_keeps_priority(client: TestClient) -> None:
    """Toggling a task does not reset its priority."""
    task = client.post("/tasks", json={"title": "a", "priority": "high"}).json()

    response = client.post(f"/tasks/{task['id']}/toggle")

    assert response.json() == {**task, "completed": True}


def test_duplicate_task(client: TestClient) -> None:
    """Duplicating a task creates a pending copy with a new id."""
    task = client.post("/tasks", json={"title": "a", "priority": "high"}).json()

    response = client.post(f"/tasks/{task['id']}/duplicate")

    assert response.status_code == 201
    assert response.json() == {
        "id": task["id"] + 1,
        "title": "a",
        "completed": False,
        "priority": "high",
    }


def test_duplicate_completed_task_is_pending(client: TestClient) -> None:
    """Duplicating a completed task yields a non-completed copy."""
    task = client.post("/tasks", json={"title": "a", "completed": True}).json()

    response = client.post(f"/tasks/{task['id']}/duplicate")

    assert response.status_code == 201
    assert response.json()["completed"] is False


def test_duplicate_leaves_source_unchanged(client: TestClient) -> None:
    """Duplicating a task does not modify the source."""
    task = client.post("/tasks", json={"title": "a", "completed": True}).json()

    client.post(f"/tasks/{task['id']}/duplicate")

    assert client.get(f"/tasks/{task['id']}").json() == task


def test_duplicate_unknown_task_creates_nothing(client: TestClient) -> None:
    """Duplicating a missing task answers 404 and creates no task."""
    response = client.post("/tasks/999/duplicate")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task 999 not found"}
    assert client.get("/tasks").json() == []


def test_toggle_task_twice_restores_state(client: TestClient) -> None:
    """Toggling twice returns completed to its initial value."""
    task = _create(client)

    client.post(f"/tasks/{task['id']}/toggle")
    response = client.post(f"/tasks/{task['id']}/toggle")

    assert response.status_code == 200
    assert response.json() == task


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/tasks/999", None),
        ("put", "/tasks/999", {"title": "x"}),
        ("patch", "/tasks/999", {"title": "x"}),
        ("delete", "/tasks/999", None),
        ("post", "/tasks/999/toggle", None),
    ],
)
def test_unknown_task_returns_404(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    """Reading, updating, patching, deleting or toggling a missing task answers 404."""
    response = client.request(method, path, json=body)

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


def _seed_priorities(client: TestClient) -> None:
    """Create 5 tasks: priorities high/low/high/medium/high, tasks 1 and 2 completed."""
    for index, priority in enumerate(["high", "low", "high", "medium", "high"], start=1):
        client.post(
            "/tasks",
            json={"title": f"task {index}", "priority": priority, "completed": index <= 2},
        )


@pytest.mark.parametrize(
    ("priority", "expected"),
    [("high", [1, 3, 5]), ("low", [2]), ("medium", [4])],
)
def test_list_filters_priority(client: TestClient, priority: str, expected: list[int]) -> None:
    """Priority returns only tasks with that priority, sorted by id."""
    _seed_priorities(client)

    response = client.get("/tasks", params={"priority": priority})

    assert response.status_code == 200
    assert _ids(response) == expected


def test_list_without_priority_returns_all(client: TestClient) -> None:
    """Without priority, no priority filtering happens."""
    _seed_priorities(client)

    assert _ids(client.get("/tasks")) == [1, 2, 3, 4, 5]


def test_list_priority_combines_with_completed(client: TestClient) -> None:
    """Priority and completed filters are both applied."""
    _seed_priorities(client)

    params = {"priority": "high", "completed": "false"}
    assert _ids(client.get("/tasks", params=params)) == [3, 5]


def test_list_priority_applies_before_pagination(client: TestClient) -> None:
    """The priority filter is applied before limit and offset."""
    _seed_priorities(client)

    params = {"priority": "high", "limit": 1, "offset": 1}
    assert _ids(client.get("/tasks", params=params)) == [3]


def test_list_priority_without_match_returns_empty(client: TestClient) -> None:
    """A priority no task has yields 200 and an empty list."""
    _create(client)

    response = client.get("/tasks", params={"priority": "high"})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"completed": "abc"},
        {"priority": "urgent"},
    ],
)
def test_list_rejects_invalid_query(client: TestClient, params: dict) -> None:
    """Out-of-range or malformed query parameters answer 422."""
    assert client.get("/tasks", params=params).status_code == 422


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

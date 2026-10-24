"""Tests for the PATCH and PUT scenario S-011 chained on one task."""

from fastapi.testclient import TestClient


def test_patch_keeps_then_put_clears(client: TestClient) -> None:
    """Follow S-011: PATCH keeps absent fields, then PUT resets them to defaults."""
    created = client.post(
        "/tasks",
        json={"title": "Example", "priority": "high", "due_date": "2030-05-17"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    patched = client.patch(f"/tasks/{task_id}", json={"title": "New"})
    assert patched.status_code == 200
    assert patched.json() == {
        "id": task_id,
        "title": "New",
        "completed": False,
        "priority": "high",
        "due_date": "2030-05-17",
    }

    replaced = client.put(f"/tasks/{task_id}", json={"title": "x"})
    assert replaced.status_code == 200
    assert replaced.json() == {
        "id": task_id,
        "title": "x",
        "completed": False,
        "priority": "medium",
        "due_date": None,
    }

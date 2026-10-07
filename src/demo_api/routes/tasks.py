"""CRUD endpoints for tasks."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from demo_api.schemas import DeletedCount, Task, TaskBulkIn, TaskIn, TaskStats
from demo_api.storage import TaskStore

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_store(request: Request) -> TaskStore:
    """Return the task store attached to the running application."""
    return request.app.state.task_store


Store = Annotated[TaskStore, Depends(get_store)]


def _not_found(task_id: int) -> HTTPException:
    """Build the 404 error for a missing task."""
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")


@router.get("")
def list_tasks(store: Store) -> list[Task]:
    """List all tasks."""
    return store.list()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(data: TaskIn, store: Store) -> Task:
    """Create a task."""
    return store.create(data)


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def create_tasks_bulk(data: TaskBulkIn, store: Store) -> list[Task]:
    """Create 1 to 50 tasks atomically."""
    return store.create_many(data.tasks)


@router.get("/stats")
def task_stats(store: Store) -> TaskStats:
    """Return task counters."""
    return store.stats()


@router.delete("")
def delete_completed_tasks(store: Store, completed: bool | None = None) -> DeletedCount:
    """Delete all completed tasks; requires `completed=true` as a safeguard."""
    if completed is not True:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Query parameter completed=true is required",
        )
    return DeletedCount(deleted=store.delete_completed())


@router.get("/{task_id}")
def get_task(task_id: int, store: Store) -> Task:
    """Get one task by id."""
    task = store.get(task_id)
    if task is None:
        raise _not_found(task_id)
    return task


@router.put("/{task_id}")
def replace_task(task_id: int, data: TaskIn, store: Store) -> Task:
    """Replace a task's title and completion state."""
    task = store.replace(task_id, data)
    if task is None:
        raise _not_found(task_id)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, store: Store) -> Response:
    """Delete a task."""
    if not store.delete(task_id):
        raise _not_found(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

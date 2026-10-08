"""CRUD endpoints for tasks."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from demo_api.schemas import Task, TaskIn
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
def list_tasks(
    store: Store,
    completed: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Task]:
    """List tasks sorted by id, optionally filtered by completion, then paginated."""
    tasks = sorted(store.list(), key=lambda task: task.id)
    if completed is not None:
        tasks = [task for task in tasks if task.completed == completed]
    return tasks[offset : offset + limit]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(data: TaskIn, store: Store) -> Task:
    """Create a task."""
    return store.create(data)


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


@router.post("/{task_id}/toggle")
def toggle_task(task_id: int, store: Store) -> Task:
    """Invert a task's completion state."""
    task = store.get(task_id)
    if task is None:
        raise _not_found(task_id)
    return store.replace(task_id, TaskIn(title=task.title, completed=not task.completed))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, store: Store) -> Response:
    """Delete a task."""
    if not store.delete(task_id):
        raise _not_found(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

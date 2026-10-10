"""CRUD endpoints for tasks."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from demo_api.schemas import DeletedCount, Priority, Task, TaskBulkIn, TaskIn, TaskPatch, TaskStats
from demo_api.storage import TaskStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_store(request: Request) -> TaskStore:
    """Return the task store attached to the running application."""
    return request.app.state.task_store


Store = Annotated[TaskStore, Depends(get_store)]


def _not_found(task_id: int) -> HTTPException:
    """Log a warning and build the 404 error for a missing task."""
    logger.warning("task not found id=%d", task_id)
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")


@router.get("")
def list_tasks(
    store: Store,
    completed: bool | None = None,
    priority: Priority | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Task]:
    """List tasks sorted by id, optionally filtered by completion and priority, then paginated."""
    tasks = sorted(store.list(), key=lambda task: task.id)
    if completed is not None:
        tasks = [task for task in tasks if task.completed == completed]
    if priority is not None:
        tasks = [task for task in tasks if task.priority == priority]
    return tasks[offset : offset + limit]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(data: TaskIn, store: Store) -> Task:
    """Create a task."""
    task = store.create(data)
    logger.info("task created id=%d", task.id)
    return task


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def create_tasks_bulk(data: TaskBulkIn, store: Store) -> list[Task]:
    """Create 1 to 50 tasks atomically."""
    tasks = store.create_many(data.tasks)
    for task in tasks:
        logger.info("task created id=%d", task.id)
    return tasks


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
    ids = sorted(task.id for task in store.list() if task.completed)
    deleted = store.delete_completed()
    for task_id in ids:
        logger.info("task deleted id=%d", task_id)
    return DeletedCount(deleted=deleted)


@router.get("/{task_id}")
def get_task(task_id: int, store: Store) -> Task:
    """Get one task by id."""
    task = store.get(task_id)
    if task is None:
        raise _not_found(task_id)
    return task


@router.put("/{task_id}")
def replace_task(task_id: int, data: TaskIn, store: Store) -> Task:
    """Replace a task's title, completion state and priority."""
    task = store.replace(task_id, data)
    if task is None:
        raise _not_found(task_id)
    logger.info("task replaced id=%d", task_id)
    return task


@router.patch("/{task_id}")
def patch_task(task_id: int, data: TaskPatch, store: Store) -> Task:
    """Partially update a task: only the fields present in the body change."""
    task = store.patch(task_id, data)
    if task is None:
        raise _not_found(task_id)
    logger.info("task patched id=%d", task_id)
    return task


@router.post("/{task_id}/toggle")
def toggle_task(task_id: int, store: Store) -> Task:
    """Invert a task's completion state."""
    task = store.get(task_id)
    if task is None:
        raise _not_found(task_id)
    toggled = store.replace(
        task_id, TaskIn(title=task.title, completed=not task.completed, priority=task.priority)
    )
    logger.info("task toggled id=%d", task_id)
    return toggled


@router.post("/{task_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_task(task_id: int, store: Store) -> Task:
    """Create a pending copy of a task."""
    task = store.get(task_id)
    if task is None:
        raise _not_found(task_id)
    copy = store.create(TaskIn(title=task.title, priority=task.priority))
    logger.info("task duplicated id=%d from id=%d", copy.id, task_id)
    return copy


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, store: Store) -> Response:
    """Delete a task."""
    if not store.delete(task_id):
        raise _not_found(task_id)
    logger.info("task deleted id=%d", task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

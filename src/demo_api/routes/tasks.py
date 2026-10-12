"""CRUD endpoints for tasks."""

import logging
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from demo_api.schemas import DeletedCount, Priority, Task, TaskBulkIn, TaskIn, TaskPatch, TaskStats
from demo_api.storage import TaskStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_store(request: Request) -> TaskStore:
    """Return the task store attached to the running application."""
    return request.app.state.task_store


Store = Annotated[TaskStore, Depends(get_store)]

SortKey = Literal["id", "-id", "title", "-title", "priority", "-priority"]

_PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2}


def _not_found(task_id: int) -> HTTPException:
    """Log a warning and build the 404 error for a missing task."""
    logger.warning("task not found id=%d", task_id)
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")


@router.get("")
def list_tasks(
    store: Store,
    response: Response,
    completed: bool | None = None,
    priority: Priority | None = None,
    sort: SortKey = "id",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Task]:
    """List tasks, filtered by completion and priority, sorted, then paginated.

    `sort` is `id` (default), `title` or `priority`, optionally prefixed by `-` for descending
    order. Ties are always ordered by id ascending.

    The `X-Total-Count` header holds the number of tasks matching the filters, before pagination.
    """
    tasks = sorted(store.list(), key=lambda task: task.id)
    if completed is not None:
        tasks = [task for task in tasks if task.completed == completed]
    if priority is not None:
        tasks = [task for task in tasks if task.priority == priority]
    descending = sort.startswith("-")
    if sort.endswith("title"):
        tasks.sort(key=lambda task: task.title.casefold(), reverse=descending)
    elif sort.endswith("priority"):
        tasks.sort(key=lambda task: _PRIORITY_RANK[task.priority], reverse=descending)
    elif descending:
        tasks.reverse()
    response.headers["X-Total-Count"] = str(len(tasks))
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


@router.get("/due")
def list_tasks_due(store: Store, before: date) -> list[Task]:
    """List tasks due before a date, ordered by due date then id."""
    tasks = [task for task in store.list() if task.due_date is not None and task.due_date <= before]
    return sorted(tasks, key=lambda task: (task.due_date, task.id))


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
    """Replace a task's fields; an omitted `due_date` clears it."""
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
        task_id,
        TaskIn(
            title=task.title,
            completed=not task.completed,
            priority=task.priority,
            due_date=task.due_date,
        ),
    )
    logger.info("task toggled id=%d", task_id)
    return toggled


@router.post("/{task_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_task(task_id: int, store: Store) -> Task:
    """Create a pending copy of a task."""
    task = store.get(task_id)
    if task is None:
        raise _not_found(task_id)
    copy = store.create(TaskIn(title=task.title, priority=task.priority, due_date=task.due_date))
    logger.info("task duplicated id=%d from id=%d", copy.id, task_id)
    return copy


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, store: Store) -> Response:
    """Delete a task."""
    if not store.delete(task_id):
        raise _not_found(task_id)
    logger.info("task deleted id=%d", task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

"""In-memory task storage (not persistent, not shared between processes)."""

from __future__ import annotations

from demo_api.schemas import Task, TaskIn, TaskStats


class TaskStore:
    """Dictionary-backed task repository with auto-incremented ids."""

    def __init__(self) -> None:
        """Start with an empty store."""
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def list(self) -> list[Task]:
        """Return all tasks ordered by id."""
        return list(self._tasks.values())

    def get(self, task_id: int) -> Task | None:
        """Return the task with this id, or None."""
        return self._tasks.get(task_id)

    def create(self, data: TaskIn) -> Task:
        """Store a new task and return it with its assigned id."""
        task = Task(id=self._next_id, **data.model_dump())
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def create_many(self, items: list[TaskIn]) -> list[Task]:
        """Store several tasks atomically: all are created, or none is."""
        tasks = [
            Task(id=self._next_id + offset, **TaskIn.model_validate(item.model_dump()).model_dump())
            for offset, item in enumerate(items)
        ]
        for task in tasks:
            self._tasks[task.id] = task
        self._next_id += len(tasks)
        return tasks

    def stats(self) -> TaskStats:
        """Return the total, completed and pending task counts."""
        total = len(self._tasks)
        completed = sum(task.completed for task in self._tasks.values())
        return TaskStats(total=total, completed=completed, pending=total - completed)

    def delete_completed(self) -> int:
        """Delete all completed tasks and return how many were removed."""
        ids = [task.id for task in self._tasks.values() if task.completed]
        for task_id in ids:
            del self._tasks[task_id]
        return len(ids)

    def replace(self, task_id: int, data: TaskIn) -> Task | None:
        """Replace an existing task; return None if it does not exist."""
        if task_id not in self._tasks:
            return None
        task = Task(id=task_id, **data.model_dump())
        self._tasks[task_id] = task
        return task

    def delete(self, task_id: int) -> bool:
        """Delete a task; return False if it does not exist."""
        return self._tasks.pop(task_id, None) is not None

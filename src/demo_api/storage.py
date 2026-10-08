"""In-memory task storage (not persistent, not shared between processes)."""

from demo_api.schemas import Task, TaskIn, TaskPatch


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

    def replace(self, task_id: int, data: TaskIn) -> Task | None:
        """Replace an existing task; return None if it does not exist."""
        if task_id not in self._tasks:
            return None
        task = Task(id=task_id, **data.model_dump())
        self._tasks[task_id] = task
        return task

    def patch(self, task_id: int, data: TaskPatch) -> Task | None:
        """Update only the provided fields; return None if the task does not exist."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        updated = task.model_copy(update=data.model_dump(exclude_unset=True))
        self._tasks[task_id] = updated
        return updated

    def delete(self, task_id: int) -> bool:
        """Delete a task; return False if it does not exist."""
        return self._tasks.pop(task_id, None) is not None

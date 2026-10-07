"""Pydantic models exposed by the API."""

from pydantic import BaseModel, Field


class TaskIn(BaseModel):
    """Payload to create or fully replace a task."""

    title: str = Field(min_length=1, max_length=200)
    completed: bool = False


class Task(TaskIn):
    """A stored task."""

    id: int


class TaskBulkIn(BaseModel):
    """Payload to create several tasks at once."""

    tasks: list[TaskIn] = Field(min_length=1, max_length=50)


class TaskStats(BaseModel):
    """Task counters."""

    total: int
    completed: int
    pending: int


class DeletedCount(BaseModel):
    """Result of a bulk deletion."""

    deleted: int

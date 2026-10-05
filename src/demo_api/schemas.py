"""Pydantic models exposed by the API."""

from pydantic import BaseModel, Field


class TaskIn(BaseModel):
    """Payload to create or fully replace a task."""

    title: str = Field(min_length=1, max_length=200)
    completed: bool = False


class Task(TaskIn):
    """A stored task."""

    id: int

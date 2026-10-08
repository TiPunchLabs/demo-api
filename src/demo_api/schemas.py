"""Pydantic models exposed by the API."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Priority = Literal["low", "medium", "high"]


class TaskIn(BaseModel):
    """Payload to create or fully replace a task."""

    title: str = Field(min_length=1, max_length=200)
    completed: bool = False
    priority: Priority = "medium"


class Task(TaskIn):
    """A stored task."""

    id: int


class TaskPatch(BaseModel):
    """Payload to partially update a task: only the fields present are changed."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", min_length=1, max_length=200)
    completed: bool = False
    priority: Priority = "medium"

    @model_validator(mode="before")
    @classmethod
    def _require_non_null_fields(cls, data: Any) -> Any:
        """Reject an empty body and explicit null values."""
        if isinstance(data, dict):
            if not data:
                raise ValueError("At least one field must be provided")
            if any(value is None for value in data.values()):
                raise ValueError("Fields cannot be null")
        return data


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

"""FastAPI application factory."""

from fastapi import FastAPI

from demo_api.routes import health, tasks
from demo_api.storage import TaskStore


def create_app() -> FastAPI:
    """Build the application with a fresh in-memory task store."""
    app = FastAPI(title="demo-api", version="0.1.0")
    app.state.task_store = TaskStore()
    app.include_router(health.router)
    app.include_router(tasks.router)
    return app


app = create_app()

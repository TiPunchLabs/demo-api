"""FastAPI application factory."""

from fastapi import FastAPI

from demo_api import __version__
from demo_api.routes import health, info, tasks, version
from demo_api.storage import TaskStore


def create_app() -> FastAPI:
    """Build the application with a fresh in-memory task store."""
    app = FastAPI(title="demo-api", version=__version__)
    app.state.task_store = TaskStore()
    app.include_router(health.router)
    app.include_router(info.router)
    app.include_router(tasks.router)
    app.include_router(version.router)
    return app


app = create_app()

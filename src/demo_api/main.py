"""FastAPI application factory."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from demo_api import __version__
from demo_api.routes import health, info, tasks, version
from demo_api.storage import TaskStore

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Log demo_api records at INFO as plain text, once per process."""
    package_logger = logging.getLogger("demo_api")
    package_logger.setLevel(logging.INFO)
    if not package_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        package_logger.addHandler(handler)


async def _log_unhandled(request: Request, exc: Exception) -> JSONResponse:
    """Log an unhandled exception with its traceback and return a generic 500."""
    logger.error("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse({"detail": "Internal Server Error"}, status_code=500)


def create_app() -> FastAPI:
    """Build the application with a fresh in-memory task store."""
    _configure_logging()
    app = FastAPI(title="demo-api", version=__version__)
    app.add_exception_handler(Exception, _log_unhandled)
    app.state.task_store = TaskStore()
    app.include_router(health.router)
    app.include_router(info.router)
    app.include_router(tasks.router)
    app.include_router(version.router)
    return app


app = create_app()

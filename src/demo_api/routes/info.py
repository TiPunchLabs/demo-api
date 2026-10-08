"""Service information endpoint."""

from fastapi import APIRouter

from demo_api import __version__

router = APIRouter(tags=["info"])


@router.get("/info")
def info() -> dict[str, str]:
    """Report the service name and version."""
    return {"name": "demo-api", "version": __version__}

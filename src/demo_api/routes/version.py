"""Version endpoint."""

from fastapi import APIRouter

from demo_api import __version__

router = APIRouter(tags=["version"])


@router.get("/version")
def version() -> dict[str, str]:
    """Report the service name and version."""
    return {"name": "demo-api", "version": __version__}

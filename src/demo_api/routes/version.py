"""Version endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["version"])


@router.get("/version")
def version() -> dict[str, str]:
    """Report the service version."""
    return {"version": "0.1.0"}

"""Readiness endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/ready")
def ready() -> dict[str, str]:
    """Report that the service is ready to serve requests."""
    return {"status": "ready"}

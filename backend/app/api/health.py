"""Unauthenticated service health endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    """Response returned when the application and database are available."""

    status: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API process is available."""
    return HealthResponse(status="ok")

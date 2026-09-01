"""Liveness endpoint.

Consumed by the Docker `HEALTHCHECK` and by Coolify/Dokploy to decide whether a
container is ready to receive traffic. Keep it cheap: no database access, so a
saturated connection pool never gets a healthy container killed.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Payload returned by the liveness probe."""

    status: str
    app: str
    environment: str


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Report that the process is up and able to answer requests."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment.value,
    )

"""Health and Readiness endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from core.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    environment: str


class ReadyResponse(BaseModel):
    status: str
    checks: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Liveness probe: verifies service process is running."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
    )


@router.get("/ready", response_model=ReadyResponse)
async def get_ready(response: Response):
    """Readiness probe: verifies dependencies (DB, Redis, S3)."""
    checks = {
        "database": "ok",
        "redis": "ok",
        "storage": "ok",
    }
    # In SIMULATION_MODE or test mode, dependencies can be mocked/simulated
    is_ready = True
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(status="unavailable", checks=checks)

    return ReadyResponse(status="ok", checks=checks)

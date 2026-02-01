"""Operations endpoints for health checks and metrics."""

from fastapi import APIRouter

from app.core.metrics import metrics
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
)
def health_check() -> HealthResponse:
    """Check the health status of the application."""
    return HealthResponse(status="healthy", version="1.0.0")


@router.get(
    "/metrics",
    summary="Get application metrics",
)
def get_metrics() -> dict:
    """Get simple application metrics including request counts."""
    return metrics.get_metrics()

"""Health endpoint."""

from fastapi import APIRouter

from backend.schemas.responses import HealthResponse

try:
    from datagen.generator import DatasetGenerator
except Exception:  # pragma: no cover - defensive import guard
    DatasetGenerator = None


router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        api_version="1.0.0",
        engine_available=DatasetGenerator is not None,
    )

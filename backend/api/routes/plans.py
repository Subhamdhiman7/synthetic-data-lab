"""Saved plan endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_service
from backend.schemas.responses import PlanListResponse, PlanResponse, PlanSummary
from backend.services.dataset_service import DatasetService
from backend.storage.history import CorruptArtifactError, NotFoundError
from datagen.schemas import DatasetPlan


router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("", response_model=PlanListResponse)
def list_plans(service: DatasetService = Depends(get_service)) -> PlanListResponse:
    return PlanListResponse(
        items=[PlanSummary(**item) for item in service.storage.list_plans()]
    )


@router.post("", response_model=PlanResponse, status_code=201)
def create_plan(
    plan: DatasetPlan,
    service: DatasetService = Depends(get_service),
) -> PlanResponse:
    try:
        record = service.save_plan(plan)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PlanResponse(**record)


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: UUID,
    service: DatasetService = Depends(get_service),
) -> PlanResponse:
    try:
        return PlanResponse(**service.storage.get_plan_record(plan_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CorruptArtifactError:
        raise HTTPException(status_code=500, detail="Saved plan is corrupted.") from None

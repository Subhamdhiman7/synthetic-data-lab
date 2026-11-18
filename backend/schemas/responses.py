"""Response models for the Synthetic Data Lab API."""

from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from datagen.schemas import DatasetPlan, TaskType


class HealthResponse(BaseModel):
    status: str
    api_version: str
    engine_available: bool


class GenerationMetadata(BaseModel):
    generation_id: UUID
    plan_id: UUID
    created_at: datetime
    dataset_name: str
    task: TaskType
    rows: int
    feature_count: int
    files: Dict[str, bool]


class GenerationResponse(BaseModel):
    status: str = "completed"
    generation: GenerationMetadata


class PreviewResponse(BaseModel):
    generation_id: UUID
    columns: List[str]
    row_count: int
    data_types: Dict[str, str]
    records: List[Dict[str, Any]]


class ReportResponse(BaseModel):
    generation_id: UUID
    report: Dict[str, Any]


class HistoryResponse(BaseModel):
    items: List[GenerationMetadata]
    total: int
    limit: int
    offset: int


class PlanResponse(BaseModel):
    plan_id: UUID
    created_at: datetime
    plan: DatasetPlan


class PlanSummary(BaseModel):
    plan_id: UUID
    created_at: datetime
    name: str
    dataset_name: str
    task: TaskType


class PlanListResponse(BaseModel):
    items: List[PlanSummary]


class ErrorResponse(BaseModel):
    error: str
    detail: str
    fields: Any = None


class RootResponse(BaseModel):
    name: str
    api_version: str
    docs: str

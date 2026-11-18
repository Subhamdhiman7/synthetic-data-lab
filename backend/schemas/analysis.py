"""Typed API contracts for Phase 4 analysis responses."""
from typing import Any, Dict, List
from uuid import UUID
from pydantic import BaseModel


class Finding(BaseModel):
    severity: str
    category: str
    message: str
    details: Dict[str, Any] = {}


class AnalysisResponse(BaseModel):
    generation_id: UUID
    dataset_name: str
    task: str
    rows: int
    column_count: int
    target_name: str | None = None
    columns: List[Dict[str, Any]]
    numerical: List[Dict[str, Any]]
    categorical: List[Dict[str, Any]]
    quality: Dict[str, Any]
    findings: List[Finding]
    recommendations: List[str]
    correlations: Dict[str, Any]
    target: Dict[str, Any]
    privacy_note: str

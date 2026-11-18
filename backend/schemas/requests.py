"""Validated request models for the Synthetic Data Lab API."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from datagen.schemas import Domain, SizePreset, TaskType


class OutputConfig(BaseModel):
    """Safe output options; filesystem paths are intentionally not accepted."""

    model_config = ConfigDict(extra="forbid")

    dataset_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Optional file-safe dataset name override.",
    )


class GenerateDatasetRequest(BaseModel):
    """Request to generate a dataset from a new or saved plan."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=5, max_length=1000)
    task: TaskType
    size: SizePreset
    seed: int
    domain: Domain = "generic"
    plan_id: Optional[UUID] = None
    output: OutputConfig = Field(default_factory=OutputConfig)

"""Thin application service around the existing Datagen engine."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import UUID, uuid4

import pandas as pd

from datagen.generator import generate_dataset
from datagen.llm_generator import generate_dataset_plan
from datagen.schemas import DatasetPlan, WizardAnswers

from backend.schemas.requests import GenerateDatasetRequest
from backend.storage.history import LocalStorage, NotFoundError
from backend.services.analysis_service import analyze_dataset, analysis_html


class DatasetService:
    """Coordinate validation, engine invocation, and artifact persistence."""

    def __init__(
        self,
        storage: LocalStorage,
        *,
        plan_generator: Callable[[WizardAnswers], DatasetPlan] = generate_dataset_plan,
        dataset_generator: Callable[[str, dict, str], tuple[str, str]] = generate_dataset,
    ):
        self.storage = storage
        self.plan_generator = plan_generator
        self.dataset_generator = dataset_generator

    @staticmethod
    def _answers(request: GenerateDatasetRequest, plan: DatasetPlan) -> WizardAnswers:
        return WizardAnswers(
            task=plan.task,
            size=request.size,
            domain=plan.domain,
            custom_description=plan.description,
            seed=plan.seed,
        )

    def save_plan(self, plan: DatasetPlan) -> Dict[str, Any]:
        return self.storage.save_plan(uuid4(), plan)

    def generate(self, request: GenerateDatasetRequest) -> Dict[str, Any]:
        plan_id = request.plan_id or uuid4()
        if request.plan_id is not None:
            plan = self.storage.load_plan(request.plan_id)
        else:
            answers = WizardAnswers(
                task=request.task,
                size=request.size,
                domain=request.domain,
                custom_description=request.description,
                seed=request.seed,
            )
            plan = self.plan_generator(answers)

        if request.output.dataset_name is not None:
            plan = plan.model_copy(update={"dataset_name": request.output.dataset_name})

        # Saving before generation makes the plan reusable and gives the engine
        # one canonical, validated JSON input.
        self.storage.save_plan(plan_id, plan)
        plan_path = self.storage.plan_path(plan_id)
        generation_id = uuid4()
        generation_dir = self.storage.create_generation_directory(generation_id)
        # Re-assert the directory immediately before the engine writes its
        # artifacts; this is harmless for normal runs and robust to transient
        # workspace cleanup races on Windows.
        generation_dir.mkdir(parents=True, exist_ok=True)
        answers = self._answers(request, plan)

        try:
            dataset_file, report_file = self.dataset_generator(
                str(plan_path), answers.model_dump(), str(generation_dir)
            )
            report_data = json.loads(Path(report_file).read_text(encoding="utf-8"))
            rows = int(report_data["metadata"]["rows"])
        except Exception as exc:
            raise RuntimeError("Dataset generation failed.") from exc

        created_at = datetime.now(timezone.utc)
        return self.storage.record_generation(
            generation_id=generation_id,
            plan_id=plan_id,
            created_at=created_at,
            dataset_name=plan.dataset_name,
            task=plan.task,
            rows=rows,
            feature_count=len(plan.features),
            csv_path=Path(dataset_file),
            report_path=Path(report_file),
            plan_path=plan_path,
        )

    def preview(self, generation_id: UUID | str) -> Dict[str, Any]:
        record = self.storage.get_generation(generation_id)
        csv_path = self.storage.artifact_path_for(record, "csv_path")
        try:
            header = pd.read_csv(csv_path, nrows=0)
            sample = pd.read_csv(csv_path, nrows=20)
        except Exception as exc:
            raise RuntimeError("Dataset preview is unavailable.") from exc
        sample = sample.astype(object).where(pd.notna(sample), None)
        return {
            "generation_id": record["generation_id"],
            "columns": list(header.columns),
            "row_count": record["rows"],
            "data_types": {column: str(dtype) for column, dtype in header.dtypes.items()},
            "records": sample.to_dict(orient="records"),
        }

    def details(self, generation_id: UUID | str) -> Dict[str, Any]:
        record = self.storage.get_generation(generation_id)
        files = {}
        for key in ("csv_path", "report_path", "plan_path"):
            try:
                self.storage.artifact_path_for(record, key)
                files[key.removesuffix("_path")] = True
            except NotFoundError:
                files[key.removesuffix("_path")] = False
        return {
            "generation_id": record["generation_id"],
            "plan_id": record["plan_id"],
            "created_at": record["created_at"],
            "dataset_name": record["dataset_name"],
            "task": record["task"],
            "rows": record["rows"],
            "feature_count": record["feature_count"],
            "files": files,
        }

    def report(self, generation_id: UUID | str) -> Dict[str, Any]:
        record = self.storage.get_generation(generation_id)
        report_path = self.storage.artifact_path_for(record, "report_path")
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError("Quality report is unavailable.") from exc
        return {"generation_id": record["generation_id"], "report": report}

    def download_path(self, generation_id: UUID | str) -> tuple[Dict[str, Any], Path]:
        record = self.storage.get_generation(generation_id)
        return record, self.storage.artifact_path_for(record, "csv_path")

    def analysis(self, generation_id: UUID | str) -> Dict[str, Any]:
        record = self.storage.get_generation(generation_id)
        csv_path = self.storage.artifact_path_for(record, "csv_path")
        plan = self.storage.load_plan(record["plan_id"])
        result = analyze_dataset(csv_path, dataset_name=record["dataset_name"], task=record["task"], target_name=plan.target_name)
        result["generation_id"] = record["generation_id"]
        return result

    def analysis_report(self, generation_id: UUID | str) -> tuple[Dict[str, Any], str]:
        result = self.analysis(generation_id)
        return result, analysis_html(result)

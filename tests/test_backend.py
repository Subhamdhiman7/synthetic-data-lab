from uuid import UUID
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from backend.api.routes.datasets import (
    details,
    download,
    analysis,
    analysis_report,
    generate_dataset_endpoint,
    history,
    preview,
    report,
)
from backend.api.routes.health import health
from backend.api.routes.plans import create_plan, get_plan, list_plans
from backend.main import app, root
from backend.schemas.requests import GenerateDatasetRequest
from backend.services.dataset_service import DatasetService
from backend.storage.history import LocalStorage
from datagen.generator import generate_dataset
from datagen.llm_generator import generate_fallback_plan
from datagen.schemas import WizardAnswers


def fallback_plan(answers: WizardAnswers):
    return generate_fallback_plan(answers)


@pytest.fixture
def backend_service(tmp_path):
    service = DatasetService(
        LocalStorage(tmp_path / "storage"),
        plan_generator=fallback_plan,
        dataset_generator=generate_dataset,
    )
    yield service
    app.dependency_overrides.clear()


def generate_one(service, *, task="classification", description="customer churn"):
    request = GenerateDatasetRequest(
        description=description,
        task=task,
        size="small",
        seed=42,
    )
    return generate_dataset_endpoint(request, service).model_dump(mode="json")


def test_root_health_and_documented_routes(backend_service):
    assert root().docs == "/docs"
    assert health().model_dump() == {
        "status": "ok",
        "api_version": "1.0.0",
        "engine_available": True,
    }
    paths = app.openapi()["paths"]
    assert "/api/health" in paths
    assert "/api/datasets/generate" in paths
    assert "/api/plans" in paths


@pytest.mark.parametrize(
    ("task", "description"),
    [("classification", "customer churn"), ("regression", "house prices")],
)
def test_generate_classification_and_regression(backend_service, task, description):
    payload = generate_one(backend_service, task=task, description=description)
    generation = payload["generation"]

    assert payload["status"] == "completed"
    assert generation["task"] == task
    assert generation["rows"] >= 100
    assert generation["files"] == {"csv": True, "report": True, "plan": True}


def test_invalid_generation_request_is_rejected(backend_service):
    with pytest.raises(ValidationError):
        GenerateDatasetRequest.model_validate(
            {
                "description": "x",
                "task": "unknown",
                "size": "small",
                "seed": 42,
            }
        )


def test_dataset_artifacts_preview_details_report_download_and_history(backend_service):
    generation = generate_one(backend_service)["generation"]
    generation_id = UUID(generation["generation_id"])

    preview_response = preview(generation_id, backend_service)
    assert len(preview_response.records) <= 20
    assert "churn" in preview_response.columns
    assert preview_response.row_count == generation["rows"]

    details_response = details(generation_id, backend_service)
    assert details_response.feature_count >= 5
    assert details_response.files == {"csv": True, "report": True, "plan": True}

    report_response = report(generation_id, backend_service)
    assert report_response.report["metadata"]["rows"] == generation["rows"]

    download_response = download(generation_id, backend_service)
    assert download_response.media_type == "text/csv"
    assert download_response.filename == f"{generation['dataset_name']}.csv"

    history_response = history(limit=1, offset=0, service=backend_service)
    assert history_response.total == 1
    assert len(history_response.items) == 1

    # A new service instance sees the same SQLite-backed history.
    replacement = DatasetService(
        LocalStorage(backend_service.storage.root),
        plan_generator=fallback_plan,
        dataset_generator=generate_dataset,
    )
    assert history(limit=20, offset=0, service=replacement).total == 1


def test_dataset_analysis_and_html_export(backend_service):
    generation = generate_one(backend_service)["generation"]
    generation_id = UUID(generation["generation_id"])

    result = analysis(generation_id, backend_service)
    assert result.generation_id == generation_id
    assert result.rows == generation["rows"]
    assert result.quality["score"] >= 0
    assert result.columns
    assert result.privacy_note

    exported = analysis_report(generation_id, backend_service)
    assert exported.media_type == "text/html"
    assert "Content-Disposition" in exported.headers
    assert "analysis" in exported.body.decode("utf-8")


def test_concurrent_generations_preserve_history(backend_service):
    request = GenerateDatasetRequest(
        description="concurrent generation",
        task="regression",
        size="small",
        seed=17,
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(backend_service.generate, [request, request]))

    assert len({record["generation_id"] for record in records}) == 2
    assert backend_service.storage.list_generations(limit=10, offset=0)[1] == 2


def test_saved_plan_creation_retrieval_and_generation(backend_service):
    plan = fallback_plan(
        WizardAnswers(
            task="regression",
            size="small",
            domain="generic",
            custom_description="saved house prices",
            seed=7,
        )
    )

    created = create_plan(plan, backend_service)
    plan_id = created.plan_id
    assert list_plans(backend_service).items[0].plan_id == plan_id
    assert get_plan(plan_id, backend_service).plan.seed == 7

    generated = generate_dataset_endpoint(
        GenerateDatasetRequest(
            description="request description is ignored for saved plan",
            task="regression",
            size="small",
            seed=999,
            plan_id=plan_id,
        ),
        backend_service,
    )
    assert generated.generation.plan_id == plan_id
    assert generated.generation.task == "regression"


def test_missing_saved_plan_returns_not_found(backend_service):
    with pytest.raises(Exception) as error:
        generate_dataset_endpoint(
            GenerateDatasetRequest(
                description="missing saved plan",
                task="classification",
                size="small",
                seed=42,
                plan_id=UUID("00000000-0000-0000-0000-000000000001"),
            ),
            backend_service,
        )

    assert getattr(error.value, "status_code", None) == 404


def test_missing_files_and_invalid_ids_are_safe_errors(backend_service):
    generation = generate_one(backend_service)["generation"]
    generation_id = UUID(generation["generation_id"])

    record = backend_service.storage.get_generation(generation_id)
    csv_path = backend_service.storage.artifact_path_for(record, "csv_path")
    csv_path.unlink()

    assert details(generation_id, backend_service).files["csv"] is False
    with pytest.raises(Exception) as error:
        preview(generation_id, backend_service)
    assert getattr(error.value, "status_code", None) == 404

    with pytest.raises(ValidationError):
        GenerateDatasetRequest.model_validate(
            {
                "description": "valid description",
                "task": "classification",
                "size": "small",
                "seed": 42,
                "plan_id": "not-a-uuid",
            }
        )


def test_generation_failure_does_not_expose_internal_exception(tmp_path):
    def failing_generator(*args, **kwargs):
        raise RuntimeError("secret internal path and details")

    service = DatasetService(
        LocalStorage(tmp_path / "storage"),
        plan_generator=fallback_plan,
        dataset_generator=failing_generator,
    )
    with pytest.raises(Exception) as error:
        generate_dataset_endpoint(
            GenerateDatasetRequest(
                description="failure test",
                task="regression",
                size="small",
                seed=42,
            ),
            service,
        )

    assert getattr(error.value, "status_code", None) == 500
    assert error.value.detail == "Dataset generation failed."

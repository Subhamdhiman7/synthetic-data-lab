import pandas as pd
import pytest

from backend.services.analysis_service import analysis_html
from backend.storage.history import CorruptArtifactError, LocalStorage
from datagen.schemas import WizardAnswers
from datagen.llm_generator import generate_fallback_plan


def test_storage_rejects_traversal_and_invalid_identifiers(tmp_path):
    storage = LocalStorage(tmp_path / "storage")

    with pytest.raises(CorruptArtifactError):
        storage._artifact_path("../outside.txt")
    with pytest.raises(Exception):
        storage.get_generation("../../etc/passwd")


def test_plan_writes_are_atomic_and_restart_persistent(tmp_path):
    storage_root = tmp_path / "storage"
    storage = LocalStorage(storage_root)
    plan = generate_fallback_plan(WizardAnswers(task="classification", size="small", domain="generic", custom_description="restart test", seed=3))
    saved = storage.save_plan("00000000-0000-0000-0000-000000000003", plan)

    restarted = LocalStorage(storage_root)
    assert restarted.load_plan(saved["plan_id"]).dataset_name == plan.dataset_name
    assert not list((storage_root / "plans").glob("*.tmp-*"))


def test_html_report_escapes_untrusted_labels(tmp_path):
    frame = pd.DataFrame({"<script>alert(1)</script>": [1], "value": ["<img src=x onerror=alert(1)>"]})
    csv_path = tmp_path / "unsafe.csv"
    frame.to_csv(csv_path, index=False)

    from backend.services.analysis_service import analyze_dataset

    result = analyze_dataset(csv_path, dataset_name="<script>bad</script>", task="regression")
    document = analysis_html(result)

    assert "<script>bad</script>" not in document
    assert "&lt;script&gt;bad&lt;/script&gt;" in document
    assert "<img" not in document


def test_request_model_rejects_paths_and_unknown_fields():
    from pydantic import ValidationError
    from backend.schemas.requests import GenerateDatasetRequest

    with pytest.raises(ValidationError):
        GenerateDatasetRequest.model_validate({
            "description": "valid request",
            "task": "classification",
            "size": "small",
            "seed": 1,
            "output": {"dataset_name": "../escape"},
        })
    with pytest.raises(ValidationError):
        GenerateDatasetRequest.model_validate({
            "description": "valid request",
            "task": "classification",
            "size": "small",
            "seed": 1,
            "filesystem_path": "C:/secret",
        })

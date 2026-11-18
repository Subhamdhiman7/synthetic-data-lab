from pathlib import Path

import pandas as pd

from backend.services.analysis_service import analysis_html, analyze_dataset


def _write(tmp_path: Path, frame: pd.DataFrame) -> Path:
    path = tmp_path / "dataset.csv"
    frame.to_csv(path, index=False)
    return path


def test_analysis_profiles_numeric_categorical_and_quality_findings(tmp_path):
    path = _write(tmp_path, pd.DataFrame({
        "age": [10, 10, 10, 10, 1000],
        "income": [1.0, 2.0, None, 4.0, 5.0],
        "segment": ["a", "a", "b", "b", "b"],
        "target": ["yes", "yes", "yes", "yes", "no"],
    }))

    result = analyze_dataset(path, dataset_name="demo", task="classification", target_name="target")

    assert result["rows"] == 5
    assert result["column_count"] == 4
    assert result["numerical"][0]["median"] == 10
    assert result["numerical"][0]["distribution"]
    assert result["categorical"][-1]["frequencies"]
    assert result["correlations"]["spearman_matrix"]
    assert result["correlations"]["target_associations"]
    assert result["quality"]["score"] < 100
    assert any(item["category"] == "missingness" for item in result["findings"])
    assert any(item["category"] == "class_imbalance" for item in result["findings"])
    assert "private" in result["privacy_note"].lower()


def test_analysis_handles_invalid_numeric_infinite_duplicates_and_empty_values(tmp_path):
    path = _write(tmp_path, pd.DataFrame({
        "amount": ["1", "bad", "inf", "1"],
        "empty": [None, None, None, None],
        "label": ["x", "x", "x", "x"],
    }))

    result = analyze_dataset(path, dataset_name="edge", task="regression", target_name="amount")

    amount = next(item for item in result["columns"] if item["name"] == "amount")
    assert amount["kind"] == "categorical"  # mixed CSV values are preserved rather than misclassified
    assert any(item["category"] == "constant" for item in result["findings"])
    assert "outliers" in result["quality"]["dimensions"]
    assert analysis_html(result).startswith("<!doctype html>")


def test_analysis_returns_safe_empty_dataset_profile(tmp_path):
    path = _write(tmp_path, pd.DataFrame({"value": [], "label": []}))

    result = analyze_dataset(path, dataset_name="empty", task="regression")

    assert result["rows"] == 0
    assert result["quality"]["score"] == 0 or result["quality"]["score"] == 100
    assert all(item["missing_percentage"] == 0 for item in result["columns"])

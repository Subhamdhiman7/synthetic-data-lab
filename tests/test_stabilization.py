import json

from datagen.generator import generate_dataset


def test_generate_dataset_creates_nested_output_directory(tmp_path):
    plan = {
        "task": "regression",
        "name": "Nested output test",
        "description": "A plan for nested output directory testing",
        "dataset_name": "nested_output",
        "features": [
            {
                "name": "x",
                "type": "numerical",
                "distribution": {"kind": "normal", "mean": 0, "std": 1},
            }
        ],
        "target_name": "target",
        "target_formula": [
            {"kind": "linear", "feature": "x", "coefficient": 1}
        ],
        "domain": "generic",
        "seed": 42,
        "rows": 100,
    }
    plan_path = tmp_path / "plan.json"
    output_dir = tmp_path / "deep" / "nested" / "output"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    dataset_path, report_path = generate_dataset(
        str(plan_path),
        {"size": "small", "seed": 42, "noise_level": "low", "outliers": "none"},
        str(output_dir),
    )

    assert output_dir.exists()
    assert (output_dir / "nested_output.csv").as_posix() == dataset_path.replace("\\", "/")
    assert (output_dir / "nested_output_report.json").as_posix() == report_path.replace("\\", "/")

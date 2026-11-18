import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from datagen.generator import DatasetGenerator, generate_dataset
from datagen.schemas import DatasetPlan, MissingnessRule


def make_plan(*, task="regression", features=None, target_formula=None, rows=100,
              classification=None, missingness_rules=None,
              target_rounding_precision=None, target_noise_scale=None):
    if features is None:
        features = [{
            "name": "x", "type": "numerical",
            "distribution": {"kind": "normal", "mean": 10, "std": 2},
        }]
    if target_formula is None:
        target_formula = [{"kind": "linear", "feature": "x", "coefficient": 2}]
    return DatasetPlan(
        task=task, name="Test dataset",
        description="Dataset used by generator edge-case tests",
        dataset_name="edge_case_test", features=features,
        target_name="target", target_formula=target_formula,
        domain="generic", seed=42, rows=rows,
        classification=classification,
        missingness_rules=missingness_rules or [],
        target_rounding_precision=target_rounding_precision,
        target_noise_scale=target_noise_scale,
    )


def make_generator(plan=None, answers=None, rows=100):
    plan = plan or make_plan(rows=rows)
    return DatasetGenerator(
        plan, rows, answers or {"noise_level": "medium", "outliers": "none"}
    )


def test_calibration_shift_hits_requested_mean_probability():
    score = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    shift = DatasetGenerator._calibration_shift(score, 0.35, 1.0)
    probabilities = 1 / (1 + np.exp(-(score + shift)))
    assert probabilities.mean() == pytest.approx(0.35, abs=1e-8)


@pytest.mark.parametrize("target_rate", [0.0, 1.0, -0.1, 1.1])
def test_calibration_shift_rejects_invalid_target_rate(target_rate):
    with pytest.raises(ValueError, match="between 0 and 1"):
        DatasetGenerator._calibration_shift(np.array([0.0, 1.0]), target_rate, 1.0)


def test_legacy_classification_uses_zero_threshold():
    plan = make_plan(task="classification",
                     target_formula=[{"kind": "constant", "value": 2.0}])
    result = make_generator(plan)._generate_classification_target(
        pd.DataFrame({"x": [1, 2, 3]})
    )
    assert result.tolist() == [1, 1, 1]


@pytest.mark.parametrize(
    ("level", "factor"),
    [("low", 0.05), ("medium", 0.15), ("high", 0.30), ("unexpected", 0.15)],
)
def test_regression_noise_scale_for_each_level(level, factor):
    targets = np.array([0.0, 10.0, 20.0])
    assert make_generator()._get_noise_scale(targets, level) == pytest.approx(
        np.std(targets) * factor
    )


def test_explicit_target_noise_scale_overrides_noise_level():
    generator = make_generator(make_plan(target_noise_scale=3.25))
    assert generator._get_noise_scale(np.array([0.0, 10.0]), "high") == 3.25


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("eq", [True, False, False]), ("ne", [False, True, True]),
        ("lt", [False, False, True]), ("le", [True, False, True]),
        ("gt", [False, True, False]), ("ge", [True, True, False]),
    ],
)
def test_missingness_condition_operators(operator, expected):
    frame = pd.DataFrame({"x": [1, 2, 0]})
    rule = MissingnessRule(
        feature="x", rate=0.5, condition_feature="x",
        condition_operator=operator, condition_value=1,
    )
    assert DatasetGenerator._missingness_condition(frame, rule).tolist() == expected


def test_missingness_condition_without_condition_matches_all_rows():
    rule = MissingnessRule(feature="x", rate=0.5)
    result = DatasetGenerator._missingness_condition(
        pd.DataFrame({"x": [1, 2, 3]}), rule
    )
    assert result.tolist() == [True, True, True]


def test_missingness_rule_rejects_unknown_target_feature():
    plan = make_plan(missingness_rules=[{"feature": "missing_column", "rate": 0.5}])
    with pytest.raises(ValueError, match="unknown feature"):
        make_generator(plan)._apply_missingness(pd.DataFrame({"x": [1, 2, 3]}))


def test_missingness_rule_rejects_rate_outside_range():
    plan = make_plan(missingness_rules=[{"feature": "x", "rate": 1.5}])
    with pytest.raises(ValueError, match="rates must be between 0 and 1"):
        make_generator(plan)._apply_missingness(pd.DataFrame({"x": [1, 2, 3]}))


def test_missingness_rule_rejects_unknown_condition_feature():
    plan = make_plan(missingness_rules=[{
        "feature": "x", "rate": 0.5, "condition_feature": "not_present",
        "condition_operator": "eq", "condition_value": 1,
    }])
    with pytest.raises(ValueError, match="condition references unknown feature"):
        make_generator(plan)._apply_missingness(pd.DataFrame({"x": [1, 2, 3]}))


def test_missingness_rule_rejects_unsupported_operator():
    rule = MissingnessRule.model_construct(
        feature="x", rate=0.5, condition_feature="x",
        condition_operator="contains", condition_value=1,
    )
    with pytest.raises(ValueError, match="Unsupported missingness operator"):
        DatasetGenerator._missingness_condition(pd.DataFrame({"x": [1, 2]}), rule)


def test_slight_outliers_change_numeric_feature_but_not_target():
    plan = make_plan(rows=500)
    generator = make_generator(plan, {"outliers": "slight", "noise_level": "medium"}, 500)
    original = pd.DataFrame({
        "x": np.random.RandomState(7).normal(10, 2, 500),
        "target": np.arange(500),
    })
    result = generator._apply_outliers(original.copy())
    assert not np.array_equal(result["x"].to_numpy(), original["x"].to_numpy())
    assert np.array_equal(result["target"].to_numpy(), original["target"].to_numpy())


def test_unknown_outlier_level_does_not_change_data():
    generator = make_generator(answers={"outliers": "extreme"})
    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0], "target": [4.0, 5.0, 6.0]})
    pd.testing.assert_frame_equal(generator._apply_outliers(frame), frame)


def test_target_rounding_integer_and_unknown_precision():
    frame = pd.DataFrame({"x": [1.0, 2.0], "target": [1.6, 2.2]})
    rounded = make_generator(make_plan(target_rounding_precision="integer"))._apply_target_rounding(frame)
    assert rounded["target"].tolist() == [2, 2]
    unchanged = make_generator(make_plan(target_rounding_precision="nearest_5"))._apply_target_rounding(frame)
    pd.testing.assert_series_equal(unchanged["target"], frame["target"])


def test_bounds_clip_values_to_declared_limits():
    plan = make_plan(features=[{
        "name": "x", "type": "numerical",
        "distribution": {"kind": "normal"},
        "bounds": {"low": 0, "high": 10},
    }])
    result = make_generator(plan)._apply_bounds(pd.DataFrame({"x": [-5.0, 4.0, 20.0]}))
    assert result["x"].tolist() == [0.0, 4.0, 10.0]


def test_report_includes_derived_relationship_and_bound_violations():
    plan = make_plan(features=[
        {"name": "x", "type": "numerical", "distribution": {"kind": "normal"}},
        {"name": "derived", "type": "derived_numerical",
         "formula": [{"kind": "linear", "feature": "x", "coefficient": 2}],
         "bounds": {"low": 0, "high": 1}},
        {"name": "segment", "type": "categorical", "categories": ["A", "B"]},
    ])
    frame = pd.DataFrame({
        "x": [1.0, 2.0, 3.0], "derived": [2.0, 4.0, 6.0],
        "segment": ["A", "A", "B"], "target": [1.0, 2.0, 3.0],
    })
    report = make_generator(plan)._generate_report(frame, 0.1)
    assert "x->derived" in report["relationship_stats"]
    assert report["data_quality"]["bound_violations"]["derived"] == 3
    assert report["feature_stats"]["segment"]["type"] == "categorical"


def test_generate_dataset_supports_legacy_plan_without_rows(tmp_path):
    plan_data = make_plan().model_dump()
    plan_data["rows"] = None
    plan_path = tmp_path / "legacy_plan.json"
    plan_path.write_text(json.dumps(plan_data), encoding="utf-8")
    dataset_path, report_path = generate_dataset(
        str(plan_path),
        {"size": "small", "seed": 42, "noise_level": "low", "outliers": "none"},
        str(tmp_path / "output"),
    )
    dataset = pd.read_csv(dataset_path)
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    assert len(dataset) >= 100
    assert report["metadata"]["rows"] == len(dataset)
    assert dataset_path.endswith("edge_case_test.csv")
    assert report_path.endswith("edge_case_test_report.json")


import json
import logging
import tomllib
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import typer
from typer.testing import CliRunner

from datagen.main import app, setup_logging, wizard_interview


runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Generate synthetic ML datasets" in result.output
    assert "--size" in result.output
    assert "--description" in result.output
    assert "--plan" in result.output


def test_setup_logging_creates_output_directory(tmp_path):
    output_dir = tmp_path / "logs"

    setup_logging(str(output_dir))

    assert output_dir.exists()
    assert (output_dir / "syntheticgen.log").exists()


def test_setup_logging_replaces_its_own_handlers(tmp_path):
    setup_logging(str(tmp_path / "first"))
    setup_logging(str(tmp_path / "second"))

    managed_handlers = [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_syntheticgen_handler", False)
    ]
    assert len(managed_handlers) == 2


def test_wizard_cancellation_exits_cleanly():
    with patch("datagen.main.questionary.select") as mock_select:
        mock_select.return_value.ask.return_value = None

        with pytest.raises(typer.Exit) as error:
            wizard_interview()

    assert error.value.exit_code == 0


def test_project_script_points_to_package_app():
    with open("pyproject.toml", "rb") as file:
        project = tomllib.load(file)

    assert project["project"]["scripts"]["syntheticgen"] == "datagen.main:app"


def test_wizard_detects_classification_task():
    with patch("datagen.main.questionary.select") as mock_select, \
         patch("datagen.main.questionary.text") as mock_text:

        mock_select.return_value.ask.return_value = "small"
        mock_text.side_effect = [
            MagicMock(ask=MagicMock(return_value="customer churn prediction")),
            MagicMock(ask=MagicMock(return_value="42")),
        ]

        answers = wizard_interview()

    assert answers.task == "classification"
    assert answers.size == "small"
    assert answers.custom_description == "customer churn prediction"
    assert answers.seed == 42


def test_wizard_detects_regression_task():
    with patch("datagen.main.questionary.select") as mock_select, \
         patch("datagen.main.questionary.text") as mock_text:

        mock_select.return_value.ask.return_value = "small"
        mock_text.side_effect = [
            MagicMock(ask=MagicMock(return_value="house price prediction")),
            MagicMock(ask=MagicMock(return_value="123")),
        ]

        answers = wizard_interview()

    assert answers.task == "regression"
    assert answers.seed == 123


def test_wizard_asks_task_when_not_detected():
    with patch("datagen.main.questionary.select") as mock_select, \
         patch("datagen.main.questionary.text") as mock_text:

        mock_select.side_effect = [
            MagicMock(ask=MagicMock(return_value="small")),
            MagicMock(ask=MagicMock(return_value="classification")),
        ]

        mock_text.side_effect = [
            MagicMock(ask=MagicMock(return_value="employee information")),
            MagicMock(ask=MagicMock(return_value="42")),
        ]

        answers = wizard_interview()

    assert answers.task == "classification"
    assert answers.size == "small"
    assert answers.custom_description == "employee information"
    assert answers.seed == 42


def test_cli_generates_dataset(tmp_path):
    output_dir = tmp_path / "generated"

    result = runner.invoke(
        app,
        [
            "--size", "small",
            "--description", "customer churn prediction",
            "--task", "classification",
            "--seed", "42",
            "--accept",
            "--outdir", str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert list(output_dir.glob("*_plan.json"))
    assert list(output_dir.glob("*.csv"))
    assert list(output_dir.glob("*_report.json"))


def test_cli_loads_existing_plan(tmp_path):
    source_dir = tmp_path / "source"

    first_result = runner.invoke(
        app,
        [
            "--size", "small",
            "--description", "house price prediction",
            "--task", "regression",
            "--seed", "42",
            "--accept",
            "--outdir", str(source_dir),
        ],
    )

    assert first_result.exit_code == 0, first_result.output

    plan_files = list(source_dir.glob("*_plan.json"))
    assert len(plan_files) == 1

    output_dir = tmp_path / "loaded"

    result = runner.invoke(
        app,
        [
            "--plan", str(plan_files[0]),
            "--accept",
            "--outdir", str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert list(output_dir.glob("*.csv"))
    assert list(output_dir.glob("*_report.json"))


def test_cli_invalid_plan_path(tmp_path):
    result = runner.invoke(
        app,
        [
            "--plan", str(tmp_path / "missing.json"),
            "--accept",
            "--outdir", str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 1
    assert "Error" in result.output


def test_cli_invalid_plan_json(tmp_path):
    invalid_plan = tmp_path / "invalid.json"
    invalid_plan.write_text("{ invalid json }", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "--plan", str(invalid_plan),
            "--accept",
            "--outdir", str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 1
    assert "Invalid JSON in plan" in result.output


def test_cli_invalid_dataset_size(tmp_path):
    result = runner.invoke(
        app,
        [
            "--size", "unknown",
            "--description", "test dataset",
            "--accept",
            "--outdir", str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 1


def test_cli_uses_default_regression_task(tmp_path):
    result = runner.invoke(
        app,
        [
            "--size", "small",
            "--description", "house price prediction",
            "--seed", "42",
            "--accept",
            "--outdir", str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 0, result.output

    plan_files = list((tmp_path / "output").glob("*_plan.json"))
    assert len(plan_files) == 1

    plan_data = json.loads(plan_files[0].read_text(encoding="utf-8"))
    assert plan_data["task"] == "regression"


def test_cli_generation_error(tmp_path):
    with patch(
        "datagen.generator.generate_dataset",
        side_effect=RuntimeError("Test generation failure"),
    ):
        result = runner.invoke(
            app,
            [
                "--size", "small",
                "--description", "test dataset",
                "--task", "regression",
                "--seed", "42",
                "--accept",
                "--outdir", str(tmp_path / "output"),
            ],
        )

    assert result.exit_code == 1
    assert "Test generation failure" in result.output

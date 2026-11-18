
from unittest.mock import MagicMock, patch

import pytest

from datagen.llm_generator import (
    build_prompt,
    generate_dataset_plan,
    generate_fallback_plan,
)
from datagen.schemas import WizardAnswers, DatasetPlan


@pytest.fixture
def answers():
    return WizardAnswers(
        task="classification",
        size="small",
        domain="generic",
        custom_description="customer churn prediction",
        seed=42,
    )


def test_build_prompt_classification(answers):
    prompt = build_prompt(answers)

    assert "classification" in prompt
    assert "customer churn prediction" in prompt
    assert "SEED: 42" in prompt
    assert "balanced classes" in prompt


def test_build_prompt_regression():
    regression_answers = WizardAnswers(
        task="regression",
        size="medium",
        domain="generic",
        custom_description="house price prediction",
        seed=123,
    )

    prompt = build_prompt(regression_answers)

    assert "regression" in prompt
    assert "house price prediction" in prompt
    assert "SEED: 123" in prompt
    assert "noise term" in prompt


def test_build_prompt_without_description():
    data = WizardAnswers(
        task="regression",
        size="small",
        domain="generic",
        custom_description=None,
        seed=42,
    )

    prompt = build_prompt(data)

    assert "generic dataset" in prompt


def test_fallback_classification_plan(answers):
    plan = generate_fallback_plan(answers)

    assert isinstance(plan, DatasetPlan)
    assert plan.task == "classification"
    assert len(plan.features) >= 5
    assert plan.target_name == "churn"
    assert not any(feature.name.startswith("feature_") for feature in plan.features)
    assert plan.rows is not None
    assert plan.seed == 42


def test_fallback_regression_plan():
    data = WizardAnswers(
        task="regression",
        size="small",
        domain="generic",
        custom_description="house price prediction",
        seed=42,
    )

    plan = generate_fallback_plan(data)

    assert plan.task == "regression"
    assert len(plan.features) >= 5
    assert plan.target_name == "house_price"
    assert {feature.name for feature in plan.features} >= {"square_footage", "bedrooms", "bathrooms"}
    assert plan.rows is not None


def test_fallback_dataset_name_sanitization():
    data = WizardAnswers(
        task="regression",
        size="small",
        domain="generic",
        custom_description="House Prices! @ 2026",
        seed=42,
    )

    plan = generate_fallback_plan(data)

    assert plan.dataset_name == "house_prices__2026"
    assert all(
        character.isalnum() or character == "_"
        for character in plan.dataset_name
    )


def test_fallback_empty_dataset_name():
    data = WizardAnswers(
        task="regression",
        size="small",
        domain="generic",
        custom_description="!!!",
        seed=42,
    )

    plan = generate_fallback_plan(data)

    assert plan.dataset_name == "fallback_dataset"


@patch("datagen.llm_generator.OpenAI")
def test_generate_dataset_plan_success(mock_openai, answers):
    expected_plan = generate_fallback_plan(answers)

    mock_response = MagicMock()
    mock_response.output = [
        MagicMock(
            content=[
                MagicMock(parsed=expected_plan)
            ]
        )
    ]

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_openai.return_value = mock_client

    result = generate_dataset_plan(answers)

    assert isinstance(result, DatasetPlan)
    assert result.task == "classification"
    assert result.rows is not None

    mock_openai.assert_called_once()
    mock_client.responses.parse.assert_called_once()


@patch("datagen.llm_generator.OpenAI")
def test_generate_dataset_plan_api_failure(mock_openai, answers):
    mock_openai.side_effect = Exception("API connection failed")

    result = generate_dataset_plan(answers)

    assert isinstance(result, DatasetPlan)
    assert result.name == "FallbackDataset"
    assert result.task == "classification"
    assert result.target_name == "churn"
    assert not any(feature.name.startswith("feature_") for feature in result.features)


@patch("datagen.llm_generator.OpenAI")
def test_generate_dataset_plan_malformed_response(mock_openai, answers):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = MagicMock(output=[])

    mock_openai.return_value = mock_client

    result = generate_dataset_plan(answers)

    assert isinstance(result, DatasetPlan)
    assert result.name == "FallbackDataset"
    assert result.target_name == "churn"
    assert not any(feature.name.startswith("feature_") for feature in result.features)


def test_fallback_plan_reproducibility(answers):
    first = generate_fallback_plan(answers)
    second = generate_fallback_plan(answers)

    assert first.model_dump() == second.model_dump()

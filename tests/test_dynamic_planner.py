"""Generalization tests for the domain-independent fallback planner."""

import pandas as pd

from datagen.generator import DatasetGenerator
from datagen.llm_generator import generate_fallback_plan
from datagen.schemas import DerivedNumericalFeature, WizardAnswers


def make_plan(task: str, description: str, seed: int = 17):
    return generate_fallback_plan(
        WizardAnswers(task=task, size="small", domain="generic", custom_description=description, seed=seed)
    )


def test_four_domains_receive_different_meaningful_schemas():
    requests = [
        ("classification", "telecom customer churn prediction with tenure, monthly charges, contract type, payment method, and support calls", "churn"),
        ("regression", "house price prediction with square footage, bedrooms, bathrooms, year built, and location", "house_price"),
        ("regression", "agricultural crop yield prediction using crop type, rainfall, temperature, soil quality, and irrigation", "crop_yield"),
        ("classification", "custom marine restoration success prediction using water_ph, dissolved_oxygen, volunteer_hours, habitat_type, and project_region", "outcome"),
    ]

    plans = [make_plan(task, description) for task, description, _ in requests]

    for plan, (_, _, expected_target) in zip(plans, requests):
        names = {feature.name for feature in plan.features}
        assert len(names) >= 4
        assert plan.target_name == expected_target
        assert plan.target_name not in names
        assert not any(name.startswith("feature_") for name in names)

    assert {feature.name for feature in plans[0].features} != {feature.name for feature in plans[1].features}
    assert {feature.name for feature in plans[2].features} != {feature.name for feature in plans[3].features}
    assert {feature.name for feature in plans[3].features} >= {"water_ph", "dissolved_oxygen", "volunteer_hours", "habitat_type", "project_region"}


def test_optional_guidance_covers_employee_and_ecommerce_without_limiting_custom_domains():
    employee = make_plan("regression", "employee salary prediction using years of experience, education level, department, performance score, and overtime")
    ecommerce = make_plan("classification", "ecommerce customer purchase prediction using purchase frequency, average order value, sessions, marketing channel, and device type")

    assert employee.target_name == "salary"
    assert {"years_experience", "education_level", "department", "performance_score"}.issubset({feature.name for feature in employee.features})
    assert ecommerce.target_name == "purchased"
    assert {"purchase_frequency", "average_order_value", "session_count", "marketing_channel", "device_type"}.issubset({feature.name for feature in ecommerce.features})


def test_telecom_plan_generates_realistic_types_dependencies_and_target():
    plan = make_plan(
        "classification",
        "realistic telecom customer churn prediction. Include customer_id, age, tenure_months, monthly_charges, total_charges, contract_type, payment_method, internet_service, technical_support, online_security, and customer_service_calls. Include some missing values and moderate class imbalance.",
    )
    generated, report = DatasetGenerator(plan, 1200, {"task": plan.task, "size": "small", "seed": plan.seed}).generate()

    assert {"customer_id", "age", "tenure_months", "monthly_charges", "total_charges", "contract_type", "churn"}.issubset(generated.columns)
    assert generated["customer_id"].is_unique
    assert generated["monthly_charges"].between(5, 5000).all()
    relationship = generated[["monthly_charges", "tenure_months", "total_charges"]].dropna()
    assert ((relationship["monthly_charges"] * relationship["tenure_months"] - relationship["total_charges"]).abs() < 0.1).mean() > 0.98
    assert 0.20 < generated["churn"].mean() < 0.50
    assert report["data_quality"]["missingness_rates"]
    assert report["feature_stats"]["customer_id"]["type"] == "identifier"


def test_custom_schema_and_generation_are_reproducible_without_domain_code():
    description = "custom satellite maintenance failure prediction using orbital_altitude, radiation_exposure, battery_cycles, component_material, and inspection_region"
    first_plan = make_plan("classification", description, seed=99)
    second_plan = make_plan("classification", description, seed=99)
    assert first_plan.model_dump() == second_plan.model_dump()

    first, _ = DatasetGenerator(first_plan, 300, {"task": "classification", "size": "small", "seed": 99}).generate()
    second, _ = DatasetGenerator(second_plan, 300, {"task": "classification", "size": "small", "seed": 99}).generate()
    pd.testing.assert_frame_equal(first, second)
    assert {"orbital_altitude", "radiation_exposure", "battery_cycles", "component_material", "inspection_region"}.issubset(first.columns)
    assert first_plan.target_name == "outcome"


def test_derived_features_are_explicit_in_the_plan():
    plan = make_plan("regression", "house price prediction using square footage and bedrooms")
    assert not any(isinstance(feature, DerivedNumericalFeature) for feature in plan.features)

    telecom = make_plan("classification", "telecom churn using monthly charges and tenure with total charges")
    total = next(feature for feature in telecom.features if feature.name == "total_charges")
    assert isinstance(total, DerivedNumericalFeature)
    assert total.formula[0].kind == "product"

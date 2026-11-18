import logging
from openai import OpenAI
from .rule_planner import infer_fallback_plan
from .schemas import DatasetPlan, WizardAnswers, get_random_row_count


logger = logging.getLogger(__name__)


def generate_dataset_plan(answers: WizardAnswers) -> DatasetPlan:
    """Generate dataset plan using OpenAI structured output."""

    prompt = build_prompt(answers)

    try:
        client = OpenAI()
        response = client.responses.parse(
            model='gpt-4o',
            input=[
                {
                    "role": "system",
                    "content": "You are a synthetic dataset specification generator. Generate detailed, realistic dataset plans."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            text_format=DatasetPlan
        )

        plan = response.output[0].content[0].parsed

        if _is_degenerate_plan(plan):
            logger.warning("LLM returned a generic schema; using semantic fallback planning")
            return infer_fallback_plan(answers)

        # Add the computed row count to the plan
        rows = get_random_row_count(answers.size, answers.seed)
        plan.rows = rows

        logger.info("Successfully generated dataset plan with structured output")
        return plan

    except Exception as e:
        logger.error(f"LLM structured output failed: {e}")
        return generate_fallback_plan(answers)


def build_prompt(answers: WizardAnswers) -> str:
    """Build prompt for LLM based on wizard answers.

    The DatasetPlan schema already constrains features, distributions, and
    target terms, so the prompt only needs high-level guidance.
    """

    rows = get_random_row_count(answers.size, answers.seed)
    description = answers.custom_description or "generic dataset"

    task_guidance = (
        "Design target_formula terms so the thresholded output (output >= 0 -> class 1) "
        "yields roughly balanced classes (30-70% positive)."
        if answers.task == "classification"
        else "Include a noise term in target_formula for realistic variability."
    )

    prompt = f"""Generate a synthetic dataset specification:

TASK: {answers.task}
DESCRIPTION: {description}
ROWS: {rows:,}
SEED: {answers.seed}

Create 5-20 realistic features with snake_case names, a target_name, and a file-safe dataset_name.
Infer the schema from the description itself. Do not use feature_1, feature_2, or a generic target when the description contains domain concepts. A domain not represented by a template must still receive an inferred schema from the requested nouns and relationships. Use identifiers, categorical, binary, numerical, and derived features where appropriate; keep dependencies explicit in formulas.
{task_guidance}
Give 2-4 features a missing_rate of 0.05-0.15, the rest 0.0.
Set rounding_precision from real-world context (integers for counts, 0.1 for ratings, 0.01 for prices, nearest_10/nearest_100 for large measurements, null to skip).
"""

    return prompt


def generate_fallback_plan(answers: WizardAnswers) -> DatasetPlan:
    """Generate a semantic plan when the LLM is unavailable."""

    logger.info("Using domain-independent rule-based fallback planning")
    return infer_fallback_plan(answers)


def _is_degenerate_plan(plan: DatasetPlan) -> bool:
    """Detect a plan that ignored a specific user description."""
    return bool(plan) and plan.target_name == "target" and bool(plan.features) and all(
        feature.name.startswith("feature_") for feature in plan.features
    )

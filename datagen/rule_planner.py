"""Domain-independent, deterministic schema inference for offline planning.

The planner deliberately contains semantic hints rather than complete domain
templates. Hints improve realism for common concepts, while user-provided
feature phrases and snake_case names are accepted for domains unknown to the
application. The generator remains responsible for executing the resulting
structured plan.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .schemas import (
    BinaryFeature,
    CategoricalFeature,
    CategoricalTerm,
    ClassificationConfig,
    ConstantTerm,
    DerivedNumericalFeature,
    IdentifierFeature,
    LinearTerm,
    LogNormalDist,
    NoiseTerm,
    NormalDist,
    NumericalFeature,
    PoissonDist,
    ProductTerm,
    TargetTerm,
    UniformDist,
    WizardAnswers,
    DatasetPlan,
    get_random_row_count,
)


@dataclass(frozen=True)
class FeatureHint:
    name: str
    aliases: tuple[str, ...]
    kind: str
    semantics: str


def _h(name: str, aliases: Iterable[str], kind: str, semantics: str) -> FeatureHint:
    return FeatureHint(name, tuple(aliases), kind, semantics)


# These are reusable concepts, not fixed datasets. Unknown concepts are
# inferred below and become first-class features without changing this table.
FEATURE_HINTS = (
    _h("customer_id", ("customer id", "customer identifier", "account id", "client id", "user id"), "identifier", "stable customer identifier"),
    _h("employee_id", ("employee id", "employee identifier", "worker id", "staff id"), "identifier", "stable employee identifier"),
    _h("product_id", ("product id", "product identifier", "sku", "item id"), "identifier", "stable product identifier"),
    _h("order_id", ("order id", "order identifier", "transaction id"), "identifier", "stable order identifier"),
    _h("age", ("age", "customer age", "employee age", "applicant age"), "age", "age in years"),
    _h("tenure_months", ("tenure", "tenure months", "months as a customer", "membership duration"), "tenure", "duration of the relationship in months"),
    _h("monthly_charges", ("monthly charges", "monthly charge", "monthly spend", "monthly fee"), "money", "recurring monthly charge"),
    _h("total_charges", ("total charges", "total charge", "lifetime charges", "lifetime spend"), "derived_total", "total charge derived from tenure and monthly charges"),
    _h("contract_type", ("contract type", "contract", "subscription contract"), "contract", "customer contract duration"),
    _h("payment_method", ("payment method", "payment type", "billing method"), "payment", "payment method"),
    _h("internet_service", ("internet service", "connectivity service", "service tier"), "service", "service availability or tier"),
    _h("technical_support", ("technical support", "tech support", "support plan"), "service_flag", "technical support status"),
    _h("online_security", ("online security", "security service"), "service_flag", "security service status"),
    _h("customer_service_calls", ("customer service calls", "support calls", "service interactions", "support contacts"), "count", "number of customer service interactions"),
    _h("square_footage", ("square footage", "floor area", "living area", "property size"), "area", "usable property area"),
    _h("bedrooms", ("bedrooms", "number of bedrooms"), "count", "number of bedrooms"),
    _h("bathrooms", ("bathrooms", "number of bathrooms"), "count", "number of bathrooms"),
    _h("year_built", ("year built", "construction year"), "year", "property construction year"),
    _h("location", ("location", "neighborhood", "region", "city", "country"), "location", "geographic location"),
    _h("property_type", ("property type", "home type", "building type"), "property", "kind of property"),
    _h("condition", ("condition", "property condition"), "condition", "condition rating"),
    _h("years_experience", ("years experience", "years of experience", "experience"), "experience", "professional experience in years"),
    _h("education_level", ("education level", "degree", "education"), "education", "highest education level"),
    _h("department", ("department", "business unit", "team"), "department", "organizational department"),
    _h("job_level", ("job level", "seniority", "career level"), "job_level", "professional seniority level"),
    _h("performance_score", ("performance score", "performance rating", "review score"), "score", "performance score"),
    _h("overtime", ("overtime", "overtime status"), "service_flag", "overtime status"),
    _h("crop_type", ("crop type", "crop", "plant type"), "crop", "crop or plant variety"),
    _h("rainfall", ("rainfall", "precipitation"), "rainfall", "seasonal rainfall"),
    _h("temperature", ("temperature", "average temperature"), "temperature", "environmental temperature"),
    _h("soil_quality", ("soil quality", "soil health", "soil fertility"), "quality", "soil quality score"),
    _h("fertilizer_usage", ("fertilizer usage", "fertilizer", "fertilizer amount"), "amount", "fertilizer application amount"),
    _h("irrigation", ("irrigation", "irrigation method"), "irrigation", "irrigation method or availability"),
    _h("field_size", ("field size", "farm size", "field area"), "area", "cultivated area"),
    _h("purchase_frequency", ("purchase frequency", "purchase count", "orders per month"), "count", "purchase frequency"),
    _h("average_order_value", ("average order value", "average basket", "average spend"), "money", "average order value"),
    _h("session_count", ("session count", "website sessions", "visits"), "count", "number of sessions or visits"),
    _h("marketing_channel", ("marketing channel", "acquisition channel", "lead source"), "channel", "marketing acquisition channel"),
    _h("device_type", ("device type", "device"), "device", "device used for interaction"),
    _h("customer_segment", ("customer segment", "segment", "customer group"), "segment", "customer segment"),
    _h("discount_rate", ("discount rate", "discount percentage", "promotion rate"), "rate", "discount as a proportion"),
    _h("cart_abandonment_rate", ("cart abandonment", "abandonment rate"), "rate", "cart abandonment proportion"),
    _h("browse_minutes", ("browsing time", "browse minutes", "time on site"), "minutes", "minutes spent browsing"),
    _h("return_rate", ("return rate", "return percentage"), "rate", "returned-order proportion"),
    _h("quantity", ("quantity", "units", "items purchased"), "count", "number of units"),
    _h("rating", ("rating", "satisfaction score", "review rating"), "rating", "user rating"),
    _h("status", ("status", "state", "outcome category"), "status", "current status"),
)

DOMAIN_GUIDANCE = (
    (("churn", "telecom", "retention"), ("age", "tenure_months", "monthly_charges", "total_charges", "contract_type", "payment_method", "internet_service", "technical_support", "online_security", "customer_service_calls")),
    (("house price", "house prices", "property price", "real estate"), ("square_footage", "bedrooms", "bathrooms", "year_built", "location", "property_type", "condition")),
    (("salary", "employee compensation", "employee pay", "wage prediction"), ("years_experience", "education_level", "department", "job_level", "performance_score", "overtime", "location")),
    (("crop yield", "agricultural yield", "farm yield", "agriculture"), ("crop_type", "rainfall", "temperature", "soil_quality", "fertilizer_usage", "irrigation", "field_size")),
    (("purchase prediction", "purchase propensity", "ecommerce", "e-commerce", "online purchase"), ("age", "purchase_frequency", "average_order_value", "session_count", "marketing_channel", "device_type", "customer_segment", "discount_rate")),
)

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "with", "some", "realistic", "meaningful", "feature", "features", "column", "columns",
    "data", "dataset", "values", "value", "include", "including", "using", "based", "on", "for", "prediction", "predict", "predicting",
}


def _normalized(value: str) -> str:
    return re.sub(r"[_-]+", " ", value.lower()).strip()


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_ -]+", "", value.lower().replace("-", "_"))
    value = re.sub(r"\s+", "_", value).strip("_")
    return value[:48] or "observed_value"


def _contains(text: str, phrase: str) -> bool:
    pattern = re.escape(_normalized(phrase)).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", _normalized(text)))


def _hint_by_name(name: str) -> FeatureHint | None:
    normalized = _normalized(name)
    for hint in FEATURE_HINTS:
        if normalized == _normalized(hint.name) or any(normalized == _normalized(alias) for alias in hint.aliases):
            return hint
    return None


def _target_name(description: str, task: str) -> str:
    text = _normalized(description)
    candidates = (
        ("churn", ("churn", "attrition")),
        ("fraud", ("fraud", "fraudulent")),
        ("default", ("loan default", "default prediction", "default risk")),
        ("purchased", ("purchase prediction", "purchase propensity", "whether a customer buys", "online purchase")),
        ("house_price", ("house price", "house prices", "property price", "sale price")),
        ("salary", ("salary", "employee pay", "compensation", "wage")),
        ("crop_yield", ("crop yield", "agricultural yield", "farm yield")),
    )
    for name, phrases in candidates:
        if any(_contains(text, phrase) for phrase in phrases):
            return name

    target_match = re.search(r"\btarget(?: variable)?\s+(?:should\s+(?:indicate|be|represent)\s+)?(?:whether\s+)?(?:a|an|the)?\s*([a-z][a-z0-9 _-]{1,40})", text)
    if target_match:
        candidate = re.split(r"\b(?:with|including|include|and|using)\b|[.;,:]", target_match.group(1))[0]
        candidate = _slug(candidate).strip("_")
        if candidate:
            if "churn" in candidate:
                return "churn"
            if "purchase" in candidate or "buy" in candidate:
                return "purchased"
            return candidate

    predicted = re.search(r"\b(?:predict|predicting|prediction of)\s+([a-z][a-z0-9 _-]{1,36})", text)
    if predicted:
        candidate = re.split(r"\b(?:using|with|from|based)\b|[.;,:]", predicted.group(1))[0]
        candidate = _slug(candidate).strip("_")
        if candidate and candidate not in {"whether", "a", "an", "the"}:
            return candidate
    return "outcome" if task == "classification" else "target_value"


def _extract_requested_names(description: str) -> list[str]:
    text = description.lower()
    clauses: list[str] = []
    for match in re.finditer(r"\b(?:include|including|features?(?:\s+such\s+as)?|columns?|variables?)\b\s*:?\s*", text):
        tail = text[match.end():]
        stop = re.search(r"[.;]|\btarget\b|\bwith some\b|\bwith realistic\b", tail)
        clauses.append(tail[:stop.start()] if stop else tail)

    names: list[str] = []
    for clause in clauses:
        for item in re.split(r",|\band\b|\bor\b", clause):
            cleaned = item.strip(" -:_\t\n")
            words = [word for word in re.findall(r"[a-z][a-z0-9_-]*", cleaned) if word not in _STOP_WORDS]
            if words:
                names.append(_slug("_".join(words[-4:])))

    for token in re.findall(r"\b[a-z][a-z0-9]*(?:[_-][a-z0-9]+)+\b", text):
        if token not in names:
            names.append(_slug(token))
    return names


def _feature_from_hint(hint: FeatureHint, missing_rate: float = 0.0):
    common = {"name": hint.name, "domain_semantics": hint.semantics, "missing_rate": missing_rate}
    if hint.kind == "identifier":
        prefix = "".join(part[0] for part in hint.name.split("_"))[:5].upper() or "ID"
        return IdentifierFeature(**common, prefix=prefix)
    if hint.kind == "age":
        return NumericalFeature(**common, distribution=NormalDist(mean=42, std=14), bounds={"low": 18, "high": 90}, rounding_precision="integer")
    if hint.kind == "tenure":
        return NumericalFeature(**common, distribution=UniformDist(low=0, high=120), bounds={"low": 0, "high": 120}, rounding_precision="integer")
    if hint.kind == "money":
        return NumericalFeature(**common, distribution=LogNormalDist(mean=4.0, sigma=0.45), bounds={"low": 5, "high": 5000}, rounding_precision="0.01")
    if hint.kind == "derived_total":
        return DerivedNumericalFeature(**common, formula=[ProductTerm(features=["monthly_charges", "tenure_months"], coefficient=1.0)], bounds={"low": 0, "high": 600000}, rounding_precision="0.01")
    if hint.kind == "count":
        return NumericalFeature(**common, distribution=PoissonDist(lam=3), bounds={"low": 0, "high": 100}, rounding_precision="integer")
    if hint.kind == "year":
        return NumericalFeature(**common, distribution=UniformDist(low=1960, high=2024), bounds={"low": 1900, "high": 2025}, rounding_precision="integer")
    if hint.kind == "area":
        return NumericalFeature(**common, distribution=LogNormalDist(mean=7.0, sigma=0.45), bounds={"low": 100, "high": 20000}, rounding_precision="integer")
    if hint.kind in {"experience", "minutes"}:
        high = 45 if hint.kind == "experience" else 600
        return NumericalFeature(**common, distribution=UniformDist(low=0, high=high), bounds={"low": 0, "high": high}, rounding_precision="integer")
    if hint.kind in {"score", "rating", "quality"}:
        return NumericalFeature(**common, distribution=UniformDist(low=1, high=10), bounds={"low": 1, "high": 10}, rounding_precision="0.1")
    if hint.kind in {"rate", "return_rate"}:
        return NumericalFeature(**common, distribution=UniformDist(low=0, high=1), bounds={"low": 0, "high": 1}, rounding_precision="0.01")
    if hint.kind == "rainfall":
        return NumericalFeature(**common, distribution=LogNormalDist(mean=4.0, sigma=0.5), bounds={"low": 0, "high": 2000}, rounding_precision="0.1")
    if hint.kind == "temperature":
        return NumericalFeature(**common, distribution=NormalDist(mean=22, std=7), bounds={"low": -30, "high": 50}, rounding_precision="0.1")
    if hint.kind == "amount":
        return NumericalFeature(**common, distribution=LogNormalDist(mean=3.0, sigma=0.6), bounds={"low": 0, "high": 10000}, rounding_precision="0.01")
    if hint.kind == "binary":
        return BinaryFeature(**common, p=0.5)

    categories = {
        "contract": (["Month-to-month", "One year", "Two year"], [0.55, 0.25, 0.20]),
        "payment": (["Electronic check", "Bank transfer", "Credit card", "Mailed check"], [0.35, 0.25, 0.25, 0.15]),
        "service": (["DSL", "Fiber optic", "No"], [0.35, 0.45, 0.20]),
        "service_flag": (["Yes", "No", "No service"], [0.45, 0.40, 0.15]),
        "education": (["High school", "Bachelor", "Master", "Doctorate"], [0.25, 0.40, 0.28, 0.07]),
        "job_level": (["Entry", "Mid", "Senior", "Lead"], [0.25, 0.40, 0.28, 0.07]),
        "overtime": (["No", "Yes"], [0.70, 0.30]),
        "crop": (["Wheat", "Corn", "Rice", "Soybean"], [0.25, 0.25, 0.25, 0.25]),
        "irrigation": (["Rainfed", "Drip", "Sprinkler"], [0.45, 0.30, 0.25]),
        "location": (["Urban", "Suburban", "Rural"], [0.35, 0.40, 0.25]),
        "property": (["Detached", "Apartment", "Townhouse"], [0.45, 0.35, 0.20]),
        "condition": (["Good", "Average", "Needs repair"], [0.45, 0.40, 0.15]),
        "channel": (["Organic", "Paid search", "Referral", "Social"], [0.35, 0.25, 0.20, 0.20]),
        "device": (["Mobile", "Desktop", "Tablet"], [0.55, 0.35, 0.10]),
        "segment": (["New", "Returning", "Loyal"], [0.35, 0.45, 0.20]),
    }.get(hint.kind, (["Low", "Medium", "High"], [0.30, 0.50, 0.20]))
    return CategoricalFeature(**common, categories=categories[0], probabilities=categories[1])


def _feature_from_custom(name: str, missing_rate: float = 0.0):
    name = _slug(name)
    hint = _hint_by_name(name)
    if hint:
        return _feature_from_hint(hint, missing_rate)
    if name.endswith("_id") or name == "id" or "identifier" in name:
        return IdentifierFeature(name=name, prefix=name.split("_")[0][:5].upper(), domain_semantics=f"identifier for {name}", missing_rate=missing_rate)
    if any(token in name for token in ("type", "method", "category", "segment", "region", "status", "class", "species", "variety", "material")):
        return CategoricalFeature(name=name, categories=["Low", "Medium", "High"], probabilities=[0.30, 0.50, 0.20], domain_semantics=f"inferred category for {name}", missing_rate=missing_rate)
    if name.startswith(("is_", "has_", "can_")) or name.endswith(("_flag", "_indicator")):
        return BinaryFeature(name=name, p=0.5, domain_semantics=f"inferred indicator for {name}", missing_rate=missing_rate)
    if any(token in name for token in ("rate", "ratio", "percentage", "percent", "share")):
        return NumericalFeature(name=name, distribution=UniformDist(low=0, high=1), bounds={"low": 0, "high": 1}, rounding_precision="0.01", domain_semantics=f"inferred rate for {name}", missing_rate=missing_rate)
    if any(token in name for token in ("count", "number", "hours", "minutes", "months", "years", "age", "quantity", "visits")):
        return NumericalFeature(name=name, distribution=PoissonDist(lam=4), bounds={"low": 0, "high": 100}, rounding_precision="integer", domain_semantics=f"inferred count for {name}", missing_rate=missing_rate)
    if any(token in name for token in ("price", "cost", "amount", "value", "income", "revenue", "salary", "spend")):
        return NumericalFeature(name=name, distribution=LogNormalDist(mean=4.0, sigma=0.55), bounds={"low": 0, "high": 500000}, rounding_precision="0.01", domain_semantics=f"inferred monetary value for {name}", missing_rate=missing_rate)
    return NumericalFeature(name=name, distribution=NormalDist(mean=0, std=1), domain_semantics=f"inferred numerical measurement for {name}", missing_rate=missing_rate, rounding_precision="0.01")


def _add_unique(names: list[str], name: str) -> None:
    if name and name not in names:
        names.append(name)


def _classification_terms(features, target: str) -> list[TargetTerm]:
    terms: list[TargetTerm] = [ConstantTerm(value=0.0)]
    numeric_weights = {
        "monthly_charges": 0.025, "tenure_months": -0.012, "customer_service_calls": 0.18,
        "age": -0.01, "performance_score": 0.12, "rainfall": 0.001, "soil_quality": 0.12,
        "session_count": 0.06, "purchase_frequency": 0.08, "discount_rate": 0.18,
    }
    for feature in features:
        if isinstance(feature, NumericalFeature) and feature.name != target:
            terms.append(LinearTerm(feature=feature.name, coefficient=numeric_weights.get(feature.name, 0.08)))
            if len(terms) >= 5:
                break
        elif isinstance(feature, CategoricalFeature):
            category_weights = {
                "contract_type": {"Month-to-month": 0.9, "One year": -0.25, "Two year": -0.55},
                "technical_support": {"No": 0.35, "Yes": -0.15},
                "online_security": {"No": 0.25, "Yes": -0.10},
                "overtime": {"Yes": 0.2},
                "condition": {"Needs repair": 0.35},
            }
            for value, coefficient in category_weights.get(feature.name, {}).items():
                terms.append(CategoricalTerm(feature=feature.name, value=value, coefficient=coefficient))
    if len(terms) == 1:
        terms.append(NoiseTerm(distribution=NormalDist(mean=0, std=1), coefficient=1.0))
    return terms


def _regression_terms(features, target: str) -> tuple[list[TargetTerm], str | None]:
    baseline = 0.0
    coefficients = {
        "square_footage": 180.0, "bedrooms": 15000.0, "bathrooms": 12000.0, "year_built": 180.0,
        "years_experience": 2500.0, "performance_score": 8000.0, "field_size": 2.0,
        "rainfall": 0.01, "soil_quality": 0.25, "temperature": 0.08,
        "monthly_charges": 1.0, "tenure_months": 5.0, "average_order_value": 0.8,
    }
    if target in {"house_price", "salary"}:
        baseline = 120000.0 if target == "house_price" else 40000.0
    elif target == "crop_yield":
        baseline = 2.5
    terms: list[TargetTerm] = [ConstantTerm(value=baseline)]
    selected = 0
    for feature in features:
        if isinstance(feature, NumericalFeature):
            terms.append(LinearTerm(feature=feature.name, coefficient=coefficients.get(feature.name, 1.0)))
            selected += 1
            if selected >= 6:
                break
    if len(terms) == 1:
        terms.append(NoiseTerm(distribution=NormalDist(mean=0, std=1), coefficient=1.0))
    rounding = "nearest_100" if target in {"house_price", "salary"} else "0.01" if target == "crop_yield" else None
    return terms, rounding


def infer_fallback_plan(answers: WizardAnswers) -> DatasetPlan:
    """Infer a realistic structured plan without requiring an LLM or domain code."""
    description = (answers.custom_description or "").strip()
    text = _normalized(description)
    target = _target_name(description, answers.task)
    names: list[str] = []

    for term in _extract_requested_names(description):
        hint = _hint_by_name(term)
        _add_unique(names, hint.name if hint else term)

    for triggers, guidance in DOMAIN_GUIDANCE:
        if any(_contains(text, trigger) for trigger in triggers):
            for name in guidance:
                _add_unique(names, name)

    for hint in FEATURE_HINTS:
        if any(_contains(text, alias) for alias in hint.aliases) or _contains(text, hint.name):
            _add_unique(names, hint.name)

    names = [name for name in names if name not in {target, "churn", "purchased", "outcome", "target_value"}]
    if not names:
        # The generic path remains useful for genuinely underspecified input,
        # but it is small and named rather than silently producing feature_N.
        names = ["observed_value", "context_category", "activity_count"]

    requested_missing = any(word in text for word in ("missing", "null", "incomplete"))
    missing_rate = 0.08 if requested_missing else 0.0
    features = []
    for index, name in enumerate(names):
        is_identifier = name.endswith("_id") or name == "id" or "identifier" in name
        feature = _feature_from_custom(name, missing_rate if requested_missing and index < 3 and not is_identifier else 0.0)
        features.append(feature)

    # Derived totals must be evaluated after their dependencies regardless of
    # the order in which a user listed the concepts.
    features.sort(key=lambda feature: 1 if isinstance(feature, DerivedNumericalFeature) else 0)
    target_formula: list[TargetTerm]
    target_rounding: str | None = None
    classification = None
    if answers.task == "classification":
        target_formula = _classification_terms(features, target)
        target_rate = 0.35 if any(word in text for word in ("imbalance", "imbalanced", "minority class")) else 0.5
        classification = ClassificationConfig(mode="bernoulli_logistic", target_rate=target_rate, temperature=1.0)
    else:
        target_formula, target_rounding = _regression_terms(features, target)

    dataset_name = description.lower().replace(" ", "_").replace("-", "_")
    dataset_name = "".join(character for character in dataset_name if character.isalnum() or character == "_")[:50] or "fallback_dataset"
    outlier_rate = 0.0
    if "outlier" in text:
        outlier_rate = 0.03 if any(word in text for word in ("moderate", "some", "few")) else 0.01

    return DatasetPlan(
        task=answers.task,
        name="FallbackDataset",
        description=f"Rule-based plan inferred from: {description or 'an underspecified dataset request'}",
        dataset_name=dataset_name,
        features=features,
        target_name=target,
        target_formula=target_formula,
        domain=answers.domain,
        seed=answers.seed,
        rows=get_random_row_count(answers.size, answers.seed),
        classification=classification,
        target_rounding_precision=target_rounding,
        outlier_rate=outlier_rate,
    )

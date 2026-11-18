"""Read-only profiling, quality checks, and correlation analysis for datasets."""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _number(value: Any) -> float | int | None:
    if value is None or pd.isna(value) or not np.isfinite(float(value)):
        return None
    value = float(value)
    return int(value) if value.is_integer() else value


def _pct(value: float, total: int) -> float:
    return round((value / total * 100) if total else 0.0, 3)


def _clean(value: Any) -> Any:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return _number(value)
    return value.item() if isinstance(value, np.generic) else value


def _histogram(series: pd.Series) -> list[dict[str, Any]]:
    values = series.dropna().to_numpy(dtype=float)
    if not len(values):
        return []
    if np.all(values == values[0]):
        return [{"label": str(_clean(values[0])), "low": _clean(values[0]), "high": _clean(values[0]), "count": len(values)}]
    counts, edges = np.histogram(values, bins=min(12, max(4, int(np.sqrt(len(values))))))
    return [
        {"label": f"{edges[i]:.3g}–{edges[i + 1]:.3g}", "low": _number(edges[i]), "high": _number(edges[i + 1]), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def _numeric_series(series: pd.Series) -> tuple[pd.Series, int, int]:
    converted = pd.to_numeric(series, errors="coerce")
    infinite = int(np.isinf(converted.to_numpy(dtype=float, na_value=np.nan)).sum())
    converted = converted.replace([np.inf, -np.inf], np.nan)
    invalid = int((series.notna() & converted.isna()).sum())
    return converted, invalid, infinite


def _finding(severity: str, category: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"severity": severity, "category": category, "message": message, "details": details or {}}


def analyze_dataset(csv_path: Path, *, dataset_name: str, task: str, target_name: str | None = None) -> dict[str, Any]:
    """Profile a CSV without modifying it. Statistics are computed on all rows."""
    try:
        frame = pd.read_csv(csv_path)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise ValueError("Dataset analysis is unavailable because the CSV could not be read safely.") from exc

    rows = int(len(frame))
    numeric_profiles: list[dict[str, Any]] = []
    categorical_profiles: list[dict[str, Any]] = []
    columns: list[dict[str, Any]] = []
    numeric_values: dict[str, pd.Series] = {}
    findings: list[dict[str, Any]] = []
    outlier_rates: list[float] = []
    invalid_cells = 0
    infinite_cells = 0
    missing_cells = int(frame.isna().sum().sum())
    if rows == 0:
        findings.append(_finding("issue", "empty_dataset", "The dataset has no rows to profile."))

    duplicate_names = [name for name in frame.columns[frame.columns.duplicated()].tolist()]
    if duplicate_names:
        findings.append(_finding("issue", "duplicate_columns", "The dataset contains duplicate column names.", {"columns": duplicate_names}))
    duplicate_rows = int(frame.duplicated().sum())
    if duplicate_rows:
        findings.append(_finding("warning" if duplicate_rows / max(rows, 1) <= 0.01 else "issue", "duplicates", f"{duplicate_rows:,} duplicate rows were detected.", {"count": duplicate_rows, "percentage": _pct(duplicate_rows, rows)}))

    for name in frame.columns:
        series = frame[name]
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        is_numeric = pd.api.types.is_numeric_dtype(series)
        numeric, invalid, infinite = _numeric_series(series)
        if is_numeric:
            numeric_values[name] = numeric
        invalid_cells += invalid
        infinite_cells += infinite
        columns.append({
            "name": str(name), "dtype": str(series.dtype), "kind": "numeric" if is_numeric else "categorical",
            "rows": rows, "missing_count": missing, "missing_percentage": _pct(missing, rows),
            "unique_count": unique, "constant": unique <= 1, "invalid_numeric_count": invalid, "infinite_count": infinite,
        })
        if missing / max(rows, 1) >= 0.20:
            findings.append(_finding("issue", "missingness", f"{name} has {missing / max(rows, 1):.1%} missing values.", {"column": str(name), "percentage": _pct(missing, rows)}))
        elif missing:
            findings.append(_finding("warning", "missingness", f"{name} has {missing / max(rows, 1):.1%} missing values.", {"column": str(name), "percentage": _pct(missing, rows)}))
        if unique <= 1:
            findings.append(_finding("warning", "constant", f"{name} is constant or empty.", {"column": str(name)}))
        if invalid or infinite:
            findings.append(_finding("issue", "invalid_values", f"{name} contains invalid or infinite numeric values.", {"column": str(name), "invalid": invalid, "infinite": infinite}))

        if is_numeric:
            values = numeric.dropna()
            outlier_count = 0
            if len(values) >= 4:
                q1, q3 = values.quantile([0.25, 0.75])
                iqr = q3 - q1
                if iqr > 0:
                    outlier_count = int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum())
            outlier_rate = outlier_count / max(len(values), 1)
            outlier_rates.append(outlier_rate)
            if outlier_rate > 0.20:
                findings.append(_finding("issue", "outliers", f"{name} has an unusually high outlier rate ({outlier_rate:.1%}).", {"column": str(name), "count": outlier_count, "rate": round(outlier_rate * 100, 3)}))
            elif outlier_rate > 0.05:
                findings.append(_finding("warning", "outliers", f"{name} has {outlier_rate:.1%} IQR outliers.", {"column": str(name), "count": outlier_count, "rate": round(outlier_rate * 100, 3)}))
            numeric_profiles.append({
                "name": str(name), "dtype": str(series.dtype), "count": int(values.count()), "missing_count": missing,
                "missing_percentage": _pct(missing, rows), "unique_count": unique, "constant": unique <= 1,
                "invalid_numeric_count": invalid, "infinite_count": infinite, "mean": _number(values.mean()),
                "median": _number(values.median()), "std": _number(values.std()), "min": _number(values.min()) if len(values) else None,
                "q1": _number(values.quantile(0.25)) if len(values) else None, "q3": _number(values.quantile(0.75)) if len(values) else None,
                "iqr": _number(values.quantile(0.75) - values.quantile(0.25)) if len(values) else None,
                "max": _number(values.max()) if len(values) else None, "skew": _number(values.skew()) if len(values) >= 3 else None,
                "kurtosis": _number(values.kurt()) if len(values) >= 4 else None, "outlier_count": outlier_count,
                "outlier_percentage": round(outlier_rate * 100, 3), "distribution": _histogram(numeric),
            })
        else:
            non_null = series.dropna().astype(str)
            counts = non_null.value_counts().head(20)
            frequencies = [{"value": str(value), "count": int(count), "percentage": _pct(int(count), len(non_null))} for value, count in counts.items()]
            cardinality = unique / max(rows, 1)
            high_cardinality = unique >= 20 and cardinality >= 0.5
            if high_cardinality:
                findings.append(_finding("warning", "high_cardinality", f"{name} has high categorical cardinality ({unique} unique values).", {"column": str(name), "unique_count": unique, "ratio": round(cardinality, 4)}))
            categorical_profiles.append({
                "name": str(name), "dtype": str(series.dtype), "count": len(non_null), "missing_count": missing,
                "missing_percentage": _pct(missing, rows), "unique_count": unique, "cardinality_percentage": round(cardinality * 100, 3),
                "constant": unique <= 1, "high_cardinality": high_cardinality, "top_value": frequencies[0]["value"] if frequencies else None,
                "top_frequency": frequencies[0]["count"] if frequencies else 0, "top_percentage": frequencies[0]["percentage"] if frequencies else 0,
                "frequencies": frequencies,
            })

    duplicate_column_pairs: list[list[str]] = []
    seen: dict[tuple[Any, ...], str] = {}
    for name in frame.columns:
        key = tuple(frame[name].astype(object).where(frame[name].notna(), "<NA>").tolist())
        if key in seen and seen[key] != name:
            duplicate_column_pairs.append([seen[key], str(name)])
        else:
            seen[key] = str(name)
    if duplicate_column_pairs:
        findings.append(_finding("warning", "duplicate_columns", "Some columns contain identical values.", {"pairs": duplicate_column_pairs}))

    correlation_frame = pd.DataFrame(numeric_values)
    correlation_matrix: dict[str, dict[str, float | None]] = {}
    spearman_matrix: dict[str, dict[str, float | None]] = {}
    high_correlations: list[dict[str, Any]] = []
    if len(correlation_frame.columns) >= 2:
        pearson = correlation_frame.corr(method="pearson")
        spearman = correlation_frame.corr(method="spearman")
        for left in pearson.columns:
            correlation_matrix[left] = {right: _number(pearson.loc[left, right]) for right in pearson.columns}
            spearman_matrix[left] = {right: _number(spearman.loc[left, right]) for right in spearman.columns}
            for right in pearson.columns:
                if left < right and pd.notna(pearson.loc[left, right]) and abs(pearson.loc[left, right]) >= 0.9:
                    high_correlations.append({"left": left, "right": right, "pearson": _number(pearson.loc[left, right]), "spearman": _number(spearman.loc[left, right])})
        if high_correlations:
            findings.append(_finding("warning", "correlation", "Highly correlated numeric features may be redundant.", {"pairs": high_correlations}))

    target_distribution: dict[str, int] = {}
    target_associations: list[dict[str, Any]] = []
    if target_name and target_name in frame.columns:
        target = frame[target_name]
        if task == "classification":
            target_distribution = {str(key): int(value) for key, value in target.astype(str).value_counts(dropna=False).items()}
            shares = [value / max(rows, 1) for value in target_distribution.values()]
            if len(shares) >= 2 and min(shares) < 0.2:
                findings.append(_finding("issue", "class_imbalance", "The target classes are strongly imbalanced.", {"distribution": target_distribution}))
            elif len(shares) >= 2 and min(shares) < 0.3:
                findings.append(_finding("warning", "class_imbalance", "The target classes are moderately imbalanced.", {"distribution": target_distribution}))
        target_numeric, _, _ = _numeric_series(target)
        if task == "classification" and target_numeric.notna().sum() < 3:
            encoded = pd.Series(pd.factorize(target.astype(str))[0], index=target.index, dtype="float64")
            encoded[target.isna()] = np.nan
            target_numeric = encoded
        for name, values in numeric_values.items():
            if name == target_name:
                continue
            aligned = pd.DataFrame({"target": target_numeric, "feature": values}).dropna()
            if len(aligned) >= 3 and aligned["target"].nunique() > 1 and aligned["feature"].nunique() > 1:
                target_associations.append({"feature": name, "pearson": _number(aligned["target"].corr(aligned["feature"], method="pearson")), "spearman": _number(aligned["target"].corr(aligned["feature"], method="spearman")), "method": "pearson/spearman"})

    total_cells = max(rows * len(frame.columns), 1)
    constant_ratio = sum(column["constant"] for column in columns) / max(len(columns), 1)
    missing_score = max(0.0, 100 - (missing_cells / total_cells) * 200)
    duplicate_score = max(0.0, 100 - (duplicate_rows / max(rows, 1)) * 200)
    constant_score = max(0.0, 100 - constant_ratio * 100)
    invalid_score = max(0.0, 100 - ((invalid_cells + infinite_cells) / total_cells) * 200)
    outlier_score = max(0.0, 100 - (sum(outlier_rates) / max(len(outlier_rates), 1)) * 100)
    dimensions = {
        "missingness": {"score": round(missing_score, 2), "weight": 0.25, "applicable": True, "detail": "100 minus twice the missing cell rate."},
        "duplicates": {"score": round(duplicate_score, 2), "weight": 0.15, "applicable": True, "detail": "100 minus twice the duplicate row rate."},
        "constants": {"score": round(constant_score, 2), "weight": 0.15, "applicable": True, "detail": "100 minus the percentage of constant columns."},
        "invalid_values": {"score": round(invalid_score, 2), "weight": 0.15, "applicable": True, "detail": "100 minus twice the invalid/infinite cell rate."},
        "outliers": {"score": round(outlier_score, 2), "weight": 0.15, "applicable": bool(outlier_rates), "detail": "100 minus the mean IQR outlier rate."},
        "class_balance": {"score": 100.0 if task != "classification" or not target_distribution else round(max(min(target_distribution.values()) / max(target_distribution.values()) * 100, 0), 2), "weight": 0.15, "applicable": task == "classification" and bool(target_distribution), "detail": "Minority class count divided by majority class count."},
    }
    applicable = [item for item in dimensions.values() if item["applicable"]]
    overall_score = 0.0 if rows == 0 else (round(sum(item["score"] * item["weight"] for item in applicable) / sum(item["weight"] for item in applicable), 2) if applicable else 100.0)
    quality = {"score": overall_score, "grade": "A" if overall_score >= 90 else "B" if overall_score >= 75 else "C" if overall_score >= 60 else "D", "dimensions": dimensions, "formula": "Weighted mean of applicable dimension scores; this is a dataset-health heuristic, not a privacy guarantee or a model-performance estimate.", "issue_count": sum(f["severity"] == "issue" for f in findings), "warning_count": sum(f["severity"] == "warning" for f in findings)}
    recommendations = []
    if missing_cells: recommendations.append("Investigate missing-value causes and choose an imputation or exclusion policy before modeling.")
    if duplicate_rows: recommendations.append("Review duplicate rows to determine whether they represent valid repeated observations.")
    if high_correlations: recommendations.append("Consider removing or combining redundant features after checking domain meaning.")
    if target_distribution and min(target_distribution.values()) / max(target_distribution.values()) < 0.3: recommendations.append("Use stratified validation or class weighting for the imbalanced target.")
    if not recommendations: recommendations.append("No material remediation was detected by the configured checks; still review domain-specific constraints.")
    return {
        "dataset_name": dataset_name, "task": task, "rows": rows, "column_count": len(frame.columns), "target_name": target_name,
        "columns": columns, "numerical": numeric_profiles, "categorical": categorical_profiles,
        "quality": quality, "findings": findings, "recommendations": recommendations,
        "correlations": {"method": "Pearson and Spearman", "matrix": correlation_matrix, "spearman_matrix": spearman_matrix, "high_correlations": high_correlations, "target_associations": target_associations},
        "target": {"name": target_name, "distribution": target_distribution},
        "privacy_note": "Profiling describes statistical quality only; it does not prove that generated data is private, anonymous, or safe for release.",
    }


def analysis_html(analysis: dict[str, Any]) -> str:
    """Render the same analysis payload as a dependency-free downloadable HTML report."""
    esc = html.escape
    rows = "".join(f"<tr><td>{esc(item['name'])}</td><td>{esc(item['kind'])}</td><td>{item['missing_percentage']:.2f}%</td><td>{item['unique_count']}</td><td>{'yes' if item['constant'] else 'no'}</td></tr>" for item in analysis["columns"])
    findings = "".join(f"<li><strong>{esc(item['severity'])}</strong> — {esc(item['message'])}</li>" for item in analysis["findings"]) or "<li>No findings.</li>"
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{esc(analysis['dataset_name'])} analysis</title><style>body{{font:15px system-ui;max-width:1000px;margin:40px auto;padding:0 20px;color:#172033}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;border-bottom:1px solid #d8e0ea;text-align:left}}.score{{font-size:40px;color:#087f70}}.note{{color:#5b6b7f}}</style></head><body><h1>{esc(analysis['dataset_name'])} — analysis</h1><p>{analysis['rows']:,} rows · {analysis['column_count']} columns · {esc(analysis['task'])}</p><p class='score'>{analysis['quality']['score']:.1f}/100 ({esc(analysis['quality']['grade'])})</p><p class='note'>{esc(analysis['quality']['formula'])}</p><h2>Findings</h2><ul>{findings}</ul><h2>Column profile</h2><table><thead><tr><th>Column</th><th>Kind</th><th>Missing</th><th>Unique</th><th>Constant</th></tr></thead><tbody>{rows}</tbody></table><h2>Privacy note</h2><p class='note'>{esc(analysis['privacy_note'])}</p></body></html>"""

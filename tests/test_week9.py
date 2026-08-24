from collections import Counter, defaultdict
from typing import Any

import pandas as pd

from scripts.compliance_checker import ComplianceChecker


def test_explicit_exclusion():
    result = ComplianceChecker().check_query(
        "Quiet apartment. No kids allowed."
    )
    assert result["compliant"] is False


def test_institution_is_not_automatically_a_violation():
    result = ComplianceChecker().check_query(
        "Converted church loft with original stonework."
    )
    assert result["requires_review"] is False


def test_household_preference_requires_review():
    result = ComplianceChecker().check_query(
        "This unit is ideal for couples."
    )
    assert result["compliant"] is True
    assert result["requires_review"] is True


def test_does_not_match_inside_another_word():
    result = ComplianceChecker().check_query(
        "The property has a blacktop driveway."
    )
    assert result["requires_review"] is False


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def normalize_category(category: str) -> str:
    """Make CSV and checker category names comparable."""
    return category.strip().lower().replace(" ", "_").replace("-", "_")


def parse_categories(value: Any) -> set[str]:
    """
    Convert a CSV value such as:
        'religion;familial_status'
    into:
        {'religion', 'familial_status'}
    """
    if pd.isna(value) or not str(value).strip():
        return set()

    return {
        normalize_category(category)
        for category in str(value).split(";")
        if category.strip()
    }


def parse_bool(value: Any) -> bool:
    """Safely parse booleans loaded from CSV."""
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes"}:
        return True

    if normalized in {"false", "0", "no"}:
        return False

    raise ValueError(f"Cannot parse boolean value: {value!r}")


def evaluate_queries(
    checker: ComplianceChecker,
    dataset: list[dict[str, Any]],
) -> dict:
    counts = Counter()
    category_counts = defaultdict(Counter)
    severity_counts = defaultdict(Counter)
    errors = []

    for item in dataset:
        result = checker.check(item["text"], 'query')

        expected_compliant = parse_bool(item["expected_compliant"])
        expected_flag = not expected_compliant

        expected_categories = parse_categories(
            item["expected_categories"]
        )

        expected_severity = str(
            item.get("expected_severity", "none")
        ).strip().lower()

        predicted_categories = {
            normalize_category(violation["category"])
            for violation in result.get("violations", [])
        }

        predicted_severities = {
            str(violation.get("severity", "review")).strip().lower()
            for violation in result.get("violations", [])
        }

        predicted_flag = bool(predicted_categories)

        # Listing-level confusion matrix
        if expected_flag and predicted_flag:
            counts["tp"] += 1
        elif not expected_flag and predicted_flag:
            counts["fp"] += 1
        elif expected_flag and not predicted_flag:
            counts["fn"] += 1
        else:
            counts["tn"] += 1

        # Every expected category must be detected.
        missing_categories = expected_categories - predicted_categories
        unexpected_categories = predicted_categories - expected_categories

        category_correct = not missing_categories

        for category in expected_categories:
            if category in predicted_categories:
                category_counts[category]["detected"] += 1
            else:
                category_counts[category]["missed"] += 1

        # Count categories produced for compliant examples or categories
        # not included in a noncompliant example's expected labels.
        for category in unexpected_categories:
            category_counts[category]["unexpected"] += 1

        # Severity evaluation
        severity_correct = (
            expected_severity == "none"
            and not predicted_severities
        ) or (
            expected_severity in predicted_severities
        )

        severity_counts[expected_severity][
            "correct" if severity_correct else "incorrect"
        ] += 1

        if (
            expected_flag != predicted_flag
            or not category_correct
            or not severity_correct
        ):
            errors.append(
                {
                    "id": item["id"],
                    "text": item["text"],
                    "case_type": item["case_type"],
                    "split": item["split"],
                    "expected_compliant": expected_compliant,
                    "expected_categories": sorted(expected_categories),
                    "predicted_categories": sorted(predicted_categories),
                    "missing_categories": sorted(missing_categories),
                    "unexpected_categories": sorted(
                        unexpected_categories
                    ),
                    "expected_severity": expected_severity,
                    "predicted_severities": sorted(
                        predicted_severities
                    ),
                    "notes": item["notes"],
                }
            )

    tp = counts["tp"]
    fp = counts["fp"]
    fn = counts["fn"]
    tn = counts["tn"]

    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    specificity = safe_divide(tn, tn + fp)
    accuracy = safe_divide(tp + tn, tp + tn + fp + fn)
    f1 = safe_divide(
        2 * precision * recall,
        precision + recall,
    )

    return {
        "total": sum(counts.values()),
        "confusion_matrix": {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
        },
        "metrics": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "specificity": specificity,
            "f1": f1,
            "false_positive_rate": safe_divide(fp, fp + tn),
        },
        "category_results": {
            category: dict(results)
            for category, results in sorted(category_counts.items())
        },
        "severity_results": {
            severity: dict(results)
            for severity, results in sorted(severity_counts.items())
        },
        "errors": errors,
    }

def evaluate_listings(
    checker: ComplianceChecker,
    dataset: list[dict[str, Any]],
) -> dict:
    counts = Counter()
    category_counts = defaultdict(Counter)
    severity_counts = defaultdict(Counter)
    errors = []

    for item in dataset:
        result = checker.check(item["text"], 'query')

        expected_compliant = parse_bool(item["expected_compliant"])
        expected_flag = not expected_compliant

        expected_categories = parse_categories(
            item["expected_categories"]
        )

        expected_severity = str(
            item.get("expected_severity", "none")
        ).strip().lower()

        predicted_categories = {
            normalize_category(violation["category"])
            for violation in result.get("violations", [])
        }

        predicted_severities = {
            str(violation.get("severity", "review")).strip().lower()
            for violation in result.get("violations", [])
        }

        predicted_flag = bool(predicted_categories)

        # Listing-level confusion matrix
        if expected_flag and predicted_flag:
            counts["tp"] += 1
        elif not expected_flag and predicted_flag:
            counts["fp"] += 1
        elif expected_flag and not predicted_flag:
            counts["fn"] += 1
        else:
            counts["tn"] += 1

        # Every expected category must be detected.
        missing_categories = expected_categories - predicted_categories
        unexpected_categories = predicted_categories - expected_categories

        category_correct = not missing_categories

        for category in expected_categories:
            if category in predicted_categories:
                category_counts[category]["detected"] += 1
            else:
                category_counts[category]["missed"] += 1

        # Count categories produced for compliant examples or categories
        # not included in a noncompliant example's expected labels.
        for category in unexpected_categories:
            category_counts[category]["unexpected"] += 1

        # Severity evaluation
        severity_correct = (
            expected_severity == "none"
            and not predicted_severities
        ) or (
            expected_severity in predicted_severities
        )

        severity_counts[expected_severity][
            "correct" if severity_correct else "incorrect"
        ] += 1

        if (
            expected_flag != predicted_flag
            or not category_correct
            or not severity_correct
        ):
            errors.append(
                {
                    "id": item["id"],
                    "text": item["text"],
                    "case_type": item["case_type"],
                    "split": item["split"],
                    "expected_compliant": expected_compliant,
                    "expected_categories": sorted(expected_categories),
                    "predicted_categories": sorted(predicted_categories),
                    "missing_categories": sorted(missing_categories),
                    "unexpected_categories": sorted(
                        unexpected_categories
                    ),
                    "expected_severity": expected_severity,
                    "predicted_severities": sorted(
                        predicted_severities
                    ),
                    "notes": item["notes"],
                }
            )

    tp = counts["tp"]
    fp = counts["fp"]
    fn = counts["fn"]
    tn = counts["tn"]

    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    specificity = safe_divide(tn, tn + fp)
    accuracy = safe_divide(tp + tn, tp + tn + fp + fn)
    f1 = safe_divide(
        2 * precision * recall,
        precision + recall,
    )

    return {
        "total": sum(counts.values()),
        "confusion_matrix": {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
        },
        "metrics": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "specificity": specificity,
            "f1": f1,
            "false_positive_rate": safe_divide(fp, fp + tn),
        },
        "category_results": {
            category: dict(results)
            for category, results in sorted(category_counts.items())
        },
        "severity_results": {
            severity: dict(results)
            for severity, results in sorted(severity_counts.items())
        },
        "errors": errors,
    }


df_queries = pd.read_csv(
    "data/processed/compliance_queries.csv",
    keep_default_na=False,
)

df_listings = pd.read_csv(
    "data/processed/compliance_listings.csv",
    keep_default_na=False,
)

dataset = df_queries.to_dict(orient="records")

report_queries = evaluate_queries(ComplianceChecker(), dataset)

print(f"Evaluated queries: {report_queries['total']}")

for name, value in report_queries["metrics"].items():
    print(f"{name}: {value:.1%}")

print("\nConfusion matrix:")
for name, value in report_queries["confusion_matrix"].items():
    print(f"{name}: {value}")

print("\nCategory results:")
for category, results in report_queries["category_results"].items():
    print(f"{category}: {results}")

print("\nErrors:")
for error in report_queries["errors"]:
    print(error)

report_listings = evaluate_listings(ComplianceChecker(), df_listings.to_dict(orient="records"))

print(f"Evaluated listings: {report_listings['total']}")

for name, value in report_listings["metrics"].items():
    print(f"{name}: {value:.1%}")

print("\nConfusion matrix:")
for name, value in report_listings["confusion_matrix"].items():
    print(f"{name}: {value}")

print("\nCategory results:")
for category, results in report_listings["category_results"].items():
    print(f"{category}: {results}")

print("\nErrors:")
for error in report_listings["errors"]:
    print(error)
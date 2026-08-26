import json
from pathlib import Path

import pandas as pd

from scripts.answerability_checker import AnswerabilityChecker
from scripts.query_parser import QueryParser
from scripts.schema_validator import SchemaValidator


HOUSING_QUERY_TEST_CSV = Path("data/processed/housing_query_validity.csv")


def load_checker():
    """Load the taxonomy and initialize AnswerabilityChecker."""
    with open("data/processed/taxonomy.json", "r") as f:
        taxonomy = json.load(f)

    parser = QueryParser()
    validator = SchemaValidator()

    checker = AnswerabilityChecker(
        taxonomy=taxonomy,
        schema_validator=validator,
        # parser=parser,
    )

    return checker


def check_prequery(user_query, checker):
    """Check whether a query is answerable before generating SQL."""
    can_answer, message = checker.check_pre_query(user_query)

    if not can_answer:
        return {"error": message, "answerable": False}

    return {"message": message, "answerable": True}


def load_csv_pre_query_tests(csv_path=HOUSING_QUERY_TEST_CSV):
    """Load and validate all housing query classification test cases."""
    tests = pd.read_csv(csv_path)
    required_columns = {"query", "on_topic"}
    missing_columns = required_columns - set(tests.columns)

    if missing_columns:
        raise ValueError(
            f"{csv_path} is missing required columns: "
            f"{', '.join(sorted(missing_columns))}"
        )

    if tests.empty:
        raise ValueError(f"{csv_path} contains no test cases")

    if tests["query"].isna().any() or tests["query"].astype(str).str.strip().eq("").any():
        raise ValueError(f"{csv_path} contains an empty query")

    normalized = tests["on_topic"].astype(str).str.strip().str.lower()
    invalid_values = sorted(set(normalized) - {"true", "false"})
    if invalid_values:
        raise ValueError(
            f"{csv_path} contains invalid on_topic values: {invalid_values}. "
            "Expected only true or false."
        )

    tests = tests.copy()
    tests["on_topic"] = normalized.map({"true": True, "false": False})
    return tests


def run_csv_pre_query_tests(checker, csv_path=HOUSING_QUERY_TEST_CSV):
    """Run check_pre_query against every row in the housing-query CSV."""
    tests = load_csv_pre_query_tests(csv_path)
    passed_count = 0
    failures = []

    print("\nCSV PRE-QUERY TESTS")
    print("=" * 60)

    for row_number, row in tests.iterrows():
        query = row["query"]
        expected = bool(row["on_topic"])
        actual, message = checker.check_pre_query(query)
        actual = bool(actual)
        passed = actual == expected

        if passed:
            passed_count += 1
        else:
            failure = {
                "csv_row": row_number + 2,
                "id": row.get("id"),
                "query": query,
                "expected": expected,
                "actual": actual,
                "message": message,
            }
            failures.append(failure)
            print(f"\nFAILED CSV row {failure['csv_row']}")
            print(f"Query: {query}")
            print(f"Expected: {expected}")
            print(f"Actual: {actual}")
            print(f"Message: {message}")

    print(f"\nCSV pre-query tests: {passed_count}/{len(tests)} passed")
    return passed_count, len(tests), failures


def test_answerability_checker(checker):
    # =========================================================
    # PRE-QUERY TESTS
    # =========================================================
    pre_query_tests = [
        {
            "name": "Valid real estate query",
            "query": "3 bed homes in Irvine under $900k with a pool",
            "expected_answerable": True,
        },
        {
            "name": "Not a real estate query",
            "query": "What is the weather in Irvine tomorrow?",
            "expected_answerable": False,
        },
        {
            "name": "Unsupported field",
            "query": "homes in Irvine with friendly neighbors",
            "expected_answerable": False,
        },
    ]

    print("\nPRE-QUERY TESTS")
    print("=" * 60)
    pre_passed = 0

    for test in pre_query_tests:
        can_answer, message = checker.check_pre_query(test["query"])
        passed = can_answer == test["expected_answerable"]
        if passed:
            pre_passed += 1

        print(f"\nTest: {test['name']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected_answerable']}")
        print(f"Actual: {can_answer}")
        print(f"Message: {message}")
        print(f"Passed: {'YES' if passed else 'NO'}")

    # =========================================================
    # ALL CSV PRE-QUERY TESTS
    # =========================================================
    csv_passed, csv_total, csv_failures = run_csv_pre_query_tests(checker)

    # =========================================================
    # POST-QUERY TEST DATA
    # =========================================================
    valid_results = pd.DataFrame(
        [
            {
                "price": 850000,
                "bedrooms": 3,
                "bathrooms": 2,
                "city": "Irvine",
                "pool": True,
            },
            {
                "price": 875000,
                "bedrooms": 3,
                "bathrooms": 2.5,
                "city": "Irvine",
                "pool": True,
            },
        ]
    )
    empty_results = pd.DataFrame()
    null_results = pd.DataFrame(
        [
            {
                "price": None,
                "bedrooms": None,
                "bathrooms": None,
                "city": None,
                "pool": None,
            }
        ]
    )
    partial_results = pd.DataFrame(
        [
            {
                "price": 925000,
                "bedrooms": 3,
                "bathrooms": None,
                "city": "Irvine",
                "pool": True,
            }
        ]
    )

    # =========================================================
    # POST-QUERY TESTS
    # =========================================================
    post_query_tests = [
        {
            "name": "Listings found",
            "query": "3 bed homes in Irvine under $900k with a pool",
            "results": valid_results,
            "expected_answerable": True,
        },
        {
            "name": "No matching listings",
            "query": "5 bed homes in Irvine under $300k",
            "results": empty_results,
            "expected_answerable": False,
        },
        {
            "name": "Results contain only null values",
            "query": "homes in Irvine",
            "results": null_results,
            "expected_answerable": False,
        },
        {
            "name": "Partially populated result",
            "query": "homes in Irvine with a pool",
            "results": partial_results,
            "expected_answerable": True,
        },
    ]

    print("\n\nPOST-QUERY TESTS")
    print("=" * 60)
    post_passed = 0

    for test in post_query_tests:
        can_answer, message = checker.check_post_query(test["query"], test["results"])
        passed = can_answer == test["expected_answerable"]
        if passed:
            post_passed += 1

        print(f"\nTest: {test['name']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected_answerable']}")
        print(f"Actual: {can_answer}")
        print(f"Message: {message}")
        print(f"Passed: {'YES' if passed else 'NO'}")

    # =========================================================
    # SUMMARY
    # =========================================================
    total_tests = len(pre_query_tests) + csv_total + len(post_query_tests)
    total_passed = pre_passed + csv_passed + post_passed

    print("\n\nTEST SUMMARY")
    print("=" * 60)
    print(f"Pre-query tests: {pre_passed}/{len(pre_query_tests)} passed")
    print(f"CSV pre-query tests: {csv_passed}/{csv_total} passed")
    print(f"Post-query tests: {post_passed}/{len(post_query_tests)} passed")
    print(f"Total: {total_passed}/{total_tests} passed")

    if csv_failures:
        print(f"CSV mismatches: {len(csv_failures)}")

    return total_passed == total_tests


if __name__ == "__main__":
    checker = load_checker()
    all_passed = test_answerability_checker(checker)
    raise SystemExit(0 if all_passed else 1)
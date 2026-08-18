import json
import pandas as pd

from scripts.answerability_checker import AnswerabilityChecker
from scripts.query_parser import QueryParser
from scripts.schema_validator import SchemaValidator


def load_checker():
    """
    Load the taxonomy and initialize all dependencies needed by
    AnswerabilityChecker.
    """

    with open("data/processed/taxonomy.json", "r") as f:
        taxonomy = json.load(f)

    parser = QueryParser()
    validator = SchemaValidator(taxonomy)

    checker = AnswerabilityChecker(
        taxonomy=taxonomy,
        schema_validator=validator,
        parser=parser
    )

    return checker


def check_prequery(user_query, checker):
    """
    Example wrapper for checking whether a query is answerable
    before generating or executing SQL.
    """

    can_answer, message = checker.check_pre_query(user_query)

    if not can_answer:
        return {
            "error": message,
            "answerable": False
        }

    return {
        "message": message,
        "answerable": True
    }


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

        can_answer, message = checker.check_pre_query(
            test["query"]
        )

        passed = (
            can_answer
            == test["expected_answerable"]
        )

        if passed:
            pre_passed += 1

        print(f"\nTest: {test['name']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected_answerable']}")
        print(f"Actual: {can_answer}")
        print(f"Message: {message}")
        print(f"Passed: {'YES' if passed else 'NO'}")


    # =========================================================
    # POST-QUERY TEST DATA
    # =========================================================

    valid_results = pd.DataFrame([
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
    ])

    empty_results = pd.DataFrame()

    null_results = pd.DataFrame([
        {
            "price": None,
            "bedrooms": None,
            "bathrooms": None,
            "city": None,
            "pool": None,
        }
    ])

    partial_results = pd.DataFrame([
        {
            "price": 925000,
            "bedrooms": 3,
            "bathrooms": None,
            "city": "Irvine",
            "pool": True,
        }
    ])


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

        can_answer, message = checker.check_post_query(
            test["query"],
            test["results"]
        )

        passed = (
            can_answer
            == test["expected_answerable"]
        )

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

    total_tests = (
        len(pre_query_tests)
        + len(post_query_tests)
    )

    total_passed = (
        pre_passed
        + post_passed
    )

    print("\n\nTEST SUMMARY")
    print("=" * 60)

    print(
        f"Pre-query tests: "
        f"{pre_passed}/{len(pre_query_tests)} passed"
    )

    print(
        f"Post-query tests: "
        f"{post_passed}/{len(post_query_tests)} passed"
    )

    print(
        f"Total: "
        f"{total_passed}/{total_tests} passed"
    )


if __name__ == "__main__":

    checker = load_checker()

    test_answerability_checker(checker)
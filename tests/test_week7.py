import pandas as pd
import pytest

from scripts.intent_classifier import (
    QueryIntentClassifier,
    VALID_LABELS,
)
from scripts.query_parser import QueryParser


# ============================================================
# SMALL UNIT-TEST TRAINING SET
# ============================================================

@pytest.fixture
def training_data():
    queries = [
        # Browsing
        "show me homes in San Diego",
        "homes with pools in Irvine",
        "luxury homes in Beverly Hills",
        "houses for sale in Orange County",
        "three bedroom homes in Anaheim",
        "beach houses in Laguna Beach",
        "townhomes in Costa Mesa",
        "homes near downtown San Diego",

        # Researching
        "condos near UC Irvine with low HOA",
        "areas in San Diego with low property taxes",
        "best neighborhoods in Irvine for families",
        "compare property taxes in Irvine and Tustin",
        "which areas have the best school districts",
        "average HOA fees for condos in Irvine",
        "is it cheaper to buy in Anaheim or Fullerton",
        "neighborhoods with low crime and good schools",

        # High intent
        "move-in ready homes in San Diego under 1.2m",
        "homes available this weekend with open houses",
        "new listings in Irvine under 900k with seller financing",
        "schedule a showing for homes under 800k in Irvine",
        "homes I can tour tomorrow in San Diego",
        "newly listed condos available now under 700k",
        "ready to buy a three bedroom home under 1m",
        "open houses this Saturday under 950k",
    ]

    labels = (
        ["browsing"] * 8
        + ["researching"] * 8
        + ["high_intent_inquiry"] * 8
    )

    return queries, labels


@pytest.fixture
def classifier(training_data):
    queries, labels = training_data

    model = QueryIntentClassifier(
        confidence_threshold=0.50
    )

    model.train(
        queries,
        labels,
    )

    return model


@pytest.fixture(scope="module")
def parser():
    return QueryParser()


# ============================================================
# BASIC PREDICTION
# ============================================================

def test_predict_returns_valid_label_and_confidence(
    classifier,
):
    intent, confidence = classifier.predict(
        "homes with pools in San Diego"
    )

    print(
        f"Predicted intent: {intent}, "
        f"confidence: {confidence:.2%}"
    )

    assert intent in VALID_LABELS
    assert 0.0 <= confidence <= 1.0


# ============================================================
# LANGUAGE INTENT TESTS
# ============================================================

def test_high_intent_language(classifier):
    result = classifier.predict_detailed(
        "open houses this weekend under 900k ready to tour"
    )

    assert (
        result.intent
        == "high_intent_inquiry"
    )


def test_research_language(classifier):
    result = classifier.predict_detailed(
        "compare HOA fees and property taxes "
        "in Irvine neighborhoods"
    )

    assert result.intent == "researching"


def test_browsing_language(classifier):
    result = classifier.predict_detailed(
        "show me luxury homes in San Diego"
    )

    assert result.intent == "browsing"


# ============================================================
# CONFIDENCE / PROBABILITIES
# ============================================================

def test_probabilities_sum_to_one(classifier):
    result = classifier.predict_detailed(
        "condos in Irvine"
    )

    assert set(
        result.probabilities
    ).issubset(
        set(VALID_LABELS)
    )

    assert sum(
        result.probabilities.values()
    ) == pytest.approx(1.0)


def test_confidence_matches_max_probability(
    classifier,
):
    result = classifier.predict_detailed(
        "open houses tomorrow in Irvine"
    )

    assert result.confidence == pytest.approx(
        max(result.probabilities.values())
    )


def test_uncertain_flag_is_boolean(
    classifier,
):
    result = classifier.predict_detailed(
        "homes"
    )

    assert isinstance(
        result.uncertain,
        bool,
    )


def test_uncertain_threshold():
    queries = [
        "show homes",
        "browse houses",
        "compare taxes",
        "research neighborhoods",
        "schedule showing",
        "tour tomorrow",
    ]

    labels = [
        "browsing",
        "browsing",
        "researching",
        "researching",
        "high_intent_inquiry",
        "high_intent_inquiry",
    ]

    model = QueryIntentClassifier(
        confidence_threshold=0.99
    )

    model.train(
        queries,
        labels,
    )

    result = model.predict_detailed(
        "houses in Irvine"
    )

    assert result.uncertain is True


# ============================================================
# BATCH PREDICTION
# ============================================================

def test_batch_prediction(classifier):
    results = classifier.predict_batch(
        [
            "show me homes in Irvine",
            "compare school districts in San Diego",
            "open houses tomorrow under 1m",
        ]
    )

    assert len(results) == 3

    assert all(
        result.intent in VALID_LABELS
        for result in results
    )


# ============================================================
# QUERY PARSER INTEGRATION
# ============================================================

def test_parser_integration(
    classifier,
    parser,
):
    query = (
        "3 bed homes in Irvine "
        "under 900k with pool"
    )

    result = classifier.understand_query(
        query,
        parser,
    )

    assert result["query"] == query

    assert "filters" in result
    assert "intent" in result
    assert "intent_confidence" in result
    assert "intent_uncertain" in result
    assert "intent_probabilities" in result

    assert result["intent"] in VALID_LABELS

    assert (
        0.0
        <= result["intent_confidence"]
        <= 1.0
    )

    # Week 4 parser integration
    assert (
        result["filters"]["city"].lower()
        == "irvine"
    )

    assert (
        result["filters"]["price_max"]
        == 900_000
    )

    assert (
        result["filters"]["bedrooms"]
        == 3
    )

    assert (
        "pool"
        in result["filters"].get(
            "amenities",
            [],
        )
    )


# ============================================================
# VALIDATION
# ============================================================

def test_empty_query_raises(classifier):
    with pytest.raises(ValueError):
        classifier.predict("   ")


def test_non_string_query_raises(classifier):
    with pytest.raises(TypeError):
        classifier.predict(123)


def test_predict_before_training_raises():
    model = QueryIntentClassifier()

    with pytest.raises(RuntimeError):
        model.predict(
            "homes in San Diego"
        )


def test_invalid_training_label_raises():
    model = QueryIntentClassifier()

    with pytest.raises(ValueError):
        model.train(
            [
                "homes in Irvine",
                "compare taxes",
            ],
            [
                "browsing",
                "unknown_label",
            ],
        )


def test_mismatched_training_lengths():
    model = QueryIntentClassifier()

    with pytest.raises(ValueError):
        model.train(
            [
                "homes in Irvine",
                "compare taxes",
            ],
            [
                "browsing",
            ],
        )


def test_empty_training_data():
    model = QueryIntentClassifier()

    with pytest.raises(ValueError):
        model.train(
            [],
            [],
        )


def test_single_class_training_data():
    model = QueryIntentClassifier()

    with pytest.raises(ValueError):
        model.train(
            [
                "homes in Irvine",
                "homes in San Diego",
            ],
            [
                "browsing",
                "browsing",
            ],
        )


# ============================================================
# REAL DATASET REQUIREMENT
# ============================================================

def test_labeled_dataset_has_at_least_200_queries():
    df = pd.read_csv(
        "data/processed/california_homebuyer_queries.csv"
    )

    assert len(df) >= 200, (
        f"Dataset contains {len(df)} queries; "
        f"requirement is 200+."
    )


def test_dataset_has_required_columns():
    df = pd.read_csv(
        "data/processed/california_homebuyer_queries.csv"
    )

    assert "query" in df.columns
    assert "category" in df.columns


def test_dataset_only_uses_valid_labels():
    df = pd.read_csv(
        "data/processed/california_homebuyer_queries.csv"
    )

    labels = set(
        df["category"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
    )

    assert labels.issubset(
        set(VALID_LABELS)
    )


def test_every_intent_class_present():
    df = pd.read_csv(
        "data/processed/california_homebuyer_queries.csv"
    )

    labels = set(
        df["category"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
    )

    assert set(
        VALID_LABELS
    ).issubset(labels)


# ============================================================
# 80% HELD-OUT ACCURACY REQUIREMENT
# ============================================================

def test_held_out_accuracy_at_least_80_percent():
    df = pd.read_csv(
        "data/processed/california_homebuyer_queries.csv"
    )

    df = df.dropna(
        subset=[
            "query",
            "category",
        ]
    ).copy()

    df["query"] = (
        df["query"]
        .astype(str)
        .str.strip()
    )

    df["category"] = (
        df["category"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df = df[
        df["query"] != ""
    ]

    classifier, metrics = (
        QueryIntentClassifier.train_with_holdout(
            queries=df["query"].tolist(),
            labels=df["category"].tolist(),
            test_size=0.20,
            random_state=42,
            confidence_threshold=0.55,
        )
    )

    accuracy = metrics[
        "accuracy"
    ]

    print()
    print("=" * 60)
    print("QUERY INTENT CLASSIFIER ACCURACY")
    print("=" * 60)
    print(
        f"Total labeled queries: {len(df)}"
    )
    print(
        f"Training examples:     "
        f"{metrics['train_size']}"
    )
    print(
        f"Held-out examples:     "
        f"{metrics['test_size']}"
    )
    print(
        f"Accuracy:              "
        f"{accuracy:.2%}"
    )
    print("=" * 60)

    assert accuracy >= 0.80, (
        f"Held-out accuracy "
        f"{accuracy:.2%} is below "
        f"required 80%"
    )


# ============================================================
# PER-CLASS METRICS
# ============================================================

def test_print_classification_metrics():
    df = pd.read_csv(
        "data/processed/california_homebuyer_queries.csv"
    )

    df = df.dropna(
        subset=[
            "query",
            "category",
        ]
    ).copy()

    classifier, metrics = (
        QueryIntentClassifier.train_with_holdout(
            queries=df["query"].tolist(),
            labels=df["category"].tolist(),
            test_size=0.20,
            random_state=42,
        )
    )

    report = metrics[
        "classification_report"
    ]

    print()
    print("=" * 70)
    print("PER-CLASS INTENT RESULTS")
    print("=" * 70)

    for label in VALID_LABELS:
        values = report[label]

        print(
            f"{label:<22}"
            f" precision={values['precision']:.2%}"
            f" recall={values['recall']:.2%}"
            f" f1={values['f1-score']:.2%}"
        )

    print("=" * 70)

    for label in VALID_LABELS:
        assert label in report
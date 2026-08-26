import pytest

from scripts.intent_classifier import QueryIntentClassifier, VALID_LABELS


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
    model = QueryIntentClassifier(confidence_threshold=0.50)
    model.train(queries, labels)
    return model


def test_predict_returns_valid_label_and_confidence(classifier):
    intent, confidence = classifier.predict("homes with pools in San Diego")
    print(f"Predicted intent: {intent}, confidence: {confidence}")
    assert intent in VALID_LABELS
    assert 0.0 <= confidence <= 1.0


def test_high_intent_language(classifier):
    result = classifier.predict_detailed(
        "open houses this weekend under 900k ready to tour"
    )
    assert result.intent == "high_intent_inquiry"


def test_research_language(classifier):
    result = classifier.predict_detailed(
        "compare HOA fees and property taxes in Irvine neighborhoods"
    )
    assert result.intent == "researching"


def test_browsing_language(classifier):
    result = classifier.predict_detailed("show me luxury homes in San Diego")
    assert result.intent == "browsing"


def test_probabilities_sum_to_one(classifier):
    result = classifier.predict_detailed("condos in Irvine")
    assert set(result.probabilities).issubset(set(VALID_LABELS))
    assert sum(result.probabilities.values()) == pytest.approx(1.0)


def test_batch_prediction(classifier):
    results = classifier.predict_batch(
        [
            "show me homes in Irvine",
            "compare school districts in San Diego",
            "open houses tomorrow under 1m",
        ]
    )
    assert len(results) == 3
    assert all(result.intent in VALID_LABELS for result in results)


def test_parser_integration(classifier):
    parsed = {
        "query": "homes available this weekend under 900k",
        "city": "Irvine",
        "max_price": 900000,
    }
    enriched = classifier.enrich_parsed_query(parsed)
    assert "intent" in enriched
    assert "intent_confidence" in enriched
    assert "intent_uncertain" in enriched
    assert "intent_probabilities" in enriched
    assert enriched["city"] == "Irvine"


def test_empty_query_raises(classifier):
    with pytest.raises(ValueError):
        classifier.predict("   ")


def test_predict_before_training_raises():
    model = QueryIntentClassifier()
    with pytest.raises(RuntimeError):
        model.predict("homes in San Diego")


def test_invalid_training_label_raises():
    model = QueryIntentClassifier()
    with pytest.raises(ValueError):
        model.train(
            ["homes in Irvine", "compare taxes"],
            ["browsing", "unknown_label"],
        )

# if __name__ == "__main__":
#     data = training_data()
#     classifier_i = classifier(data)
#     test_confidence = test_predict_returns_valid_label_and_confidence(classifier_i)


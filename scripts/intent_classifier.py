
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from scripts.query_parser import QueryParser


VALID_LABELS = (
    "browsing",
    "researching",
    "high_intent_inquiry",
)


@dataclass(frozen=True)
class IntentPrediction:
    """Structured prediction result."""

    intent: str
    confidence: float
    probabilities: Dict[str, float]
    uncertain: bool


class QueryIntentClassifier:
    """Classify real-estate search queries into language-based intent classes."""

    def __init__(
        self,
        max_features: int = 500,
        confidence_threshold: float = 0.60,
        random_state: int = 42,
    ) -> None:
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            lowercase=True,
            strip_accents="unicode",
            stop_words="english",
        )
        self.model = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=random_state,
        )
        self.labels = list(VALID_LABELS)
        self.confidence_threshold = confidence_threshold
        self._is_trained = False

    def train(self, queries: Sequence[str], labels: Sequence[str]) -> None:
        """Train the TF-IDF vectorizer and logistic-regression classifier."""
        self._validate_training_data(queries, labels)
        X = self.vectorizer.fit_transform(queries)
        self.model.fit(X, labels)
        self._is_trained = True

    def predict(self, query: str) -> Tuple[str, float]:
        """Return ``(intent, confidence)`` for one query."""
        prediction = self.predict_detailed(query)
        return prediction.intent, prediction.confidence

    def predict_detailed(self, query: str) -> IntentPrediction:
        """Return intent, confidence, all probabilities, and uncertainty flag."""
        self._ensure_trained()
        cleaned_query = self._validate_query(query)

        X = self.vectorizer.transform([cleaned_query])
        probabilities = self.model.predict_proba(X)[0]
        classes = self.model.classes_
        best_index = int(np.argmax(probabilities))

        intent = str(classes[best_index])
        confidence = float(probabilities[best_index])
        probability_map = {
            str(label): float(probability)
            for label, probability in zip(classes, probabilities)
        }

        return IntentPrediction(
            intent=intent,
            confidence=confidence,
            probabilities=probability_map,
            uncertain=confidence < self.confidence_threshold,
        )

    def predict_batch(self, queries: Iterable[str]) -> List[IntentPrediction]:
        """Predict intent for multiple queries."""
        return [self.predict_detailed(query) for query in queries]

    def evaluate(
        self,
        queries: Sequence[str],
        labels: Sequence[str],
    ) -> Dict[str, object]:
        """Evaluate a trained model against labeled examples."""
        self._ensure_trained()
        if len(queries) != len(labels):
            raise ValueError("queries and labels must have the same length")

        X = self.vectorizer.transform(queries)
        predicted = self.model.predict(X)
        accuracy = float(accuracy_score(labels, predicted))
        report = classification_report(
            labels,
            predicted,
            labels=list(VALID_LABELS),
            output_dict=True,
            zero_division=0,
        )
        return {"accuracy": accuracy, "classification_report": report}

    @classmethod
    def train_with_holdout(
        cls,
        queries: Sequence[str],
        labels: Sequence[str],
        test_size: float = 0.20,
        random_state: int = 42,
        **classifier_kwargs,
    ) -> Tuple["QueryIntentClassifier", Dict[str, object]]:
        """Train with a stratified holdout split and return model + metrics."""
        if len(queries) != len(labels):
            raise ValueError("queries and labels must have the same length")
        if len(set(labels)) < 2:
            raise ValueError("at least two intent classes are required")

        X_train, X_test, y_train, y_test = train_test_split(
            list(queries),
            list(labels),
            test_size=test_size,
            random_state=random_state,
            stratify=list(labels),
        )

        classifier = cls(random_state=random_state, **classifier_kwargs)
        classifier.train(X_train, y_train)
        metrics = classifier.evaluate(X_test, y_test)
        metrics["test_queries"] = X_test
        metrics["test_labels"] = y_test
        return classifier, metrics

    def enrich_parsed_query(self, parsed_query: Dict[str, object]) -> Dict[str, object]:
        """Add intent information to output from a query parser.

        The parser output should contain the original query under one of these
        keys: ``query``, ``raw_query``, or ``text``.
        """
        query = next(
            (
                parsed_query[key]
                for key in ("query", "raw_query", "text")
                if key in parsed_query
            ),
            None,
        )
        if not isinstance(query, str) or not query.strip():
            raise ValueError(
                "parsed_query must include a non-empty 'query', 'raw_query', or 'text'"
            )

        prediction = self.predict_detailed(query)
        enriched = dict(parsed_query)
        enriched["intent"] = prediction.intent
        enriched["intent_confidence"] = prediction.confidence
        enriched["intent_uncertain"] = prediction.uncertain
        enriched["intent_probabilities"] = prediction.probabilities
        return enriched

    def _ensure_trained(self) -> None:
        if not self._is_trained:
            raise RuntimeError("Classifier has not been trained yet")

    @staticmethod
    def _validate_query(query: str) -> str:
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        query = query.strip()
        if not query:
            raise ValueError("query cannot be empty")
        return query

    @staticmethod
    def _validate_training_data(
        queries: Sequence[str], labels: Sequence[str]
    ) -> None:
        if len(queries) != len(labels):
            raise ValueError("queries and labels must have the same length")
        if not queries:
            raise ValueError("training data cannot be empty")

        invalid_labels = sorted(set(labels) - set(VALID_LABELS))
        if invalid_labels:
            raise ValueError(f"invalid labels: {invalid_labels}")

        if len(set(labels)) < 2:
            raise ValueError("training data must contain at least two intent classes")

        for query in queries:
            if not isinstance(query, str) or not query.strip():
                raise ValueError("all training queries must be non-empty strings")


if __name__ == "__main__":
    # demo_queries = [
    #     "show me homes in San Diego",
    #     "luxury homes in Beverly Hills",
    #     "homes with pools in Irvine",
    #     "condos near UC Irvine with low HOA",
    #     "areas in San Diego with low property taxes",
    #     "best neighborhoods in Irvine for families",
    #     "move-in ready homes in San Diego under 1.2m",
    #     "homes available this weekend with open houses",
    #     "new listings in Irvine under 900k with seller financing",
    # ]
    # demo_labels = [
    #     "browsing",
    #     "browsing",
    #     "browsing",
    #     "researching",
    #     "researching",
    #     "researching",
    #     "high_intent_inquiry",
    #     "high_intent_inquiry",
    #     "high_intent_inquiry",
    # ]

    query_set = pd.read_csv("data/processed/california_homebuyer_queries.csv")
    train_df, test_df = train_test_split(
        query_set,
        test_size=0.2,
        random_state=42,
        stratify=query_set["category"]
    )
    classifier = QueryIntentClassifier(confidence_threshold=0.55)
    classifier.train(train_df["query"].tolist(), train_df["category"].tolist())

    # result = classifier.predict_detailed("homes with open houses this weekend")
    # print("Intent:", result.intent)
    # print("Confidence:", round(result.confidence, 3))
    # print("Uncertain:", result.uncertain)
    # print("Probabilities:", result.probabilities)

    y_true = test_df["category"].tolist()

    y_pred = [
        classifier.predict_detailed(query).intent
        for query in test_df["query"]
    ]

    print(classification_report(y_true, y_pred))
    print(confusion_matrix(y_true, y_pred))
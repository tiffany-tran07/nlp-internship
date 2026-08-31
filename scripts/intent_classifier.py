# scripts/query_intent_classifier.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split

from scripts.query_parser import QueryParser


VALID_LABELS = (
    "browsing",
    "researching",
    "high_intent_inquiry",
)


@dataclass(frozen=True)
class IntentPrediction:
    """
    Structured intent prediction.
    """

    intent: str
    confidence: float
    probabilities: Dict[str, float]
    uncertain: bool


class QueryIntentClassifier:
    """
    Classify real-estate search queries using language only.

    Intent categories:

        browsing
            General property exploration.

        researching
            Queries seeking information, comparisons,
            neighborhoods, taxes, schools, market information, etc.

        high_intent_inquiry
            Queries that contain stronger action-oriented or
            transaction-oriented language.
    """

    def __init__(
        self,
        max_features: int = 1000,
        confidence_threshold: float = 0.60,
        random_state: int = 42,
    ) -> None:

        self.max_features = max_features
        self.confidence_threshold = confidence_threshold
        self.random_state = random_state

        self.vectorizer = TfidfVectorizer(
            max_features=max_features,

            # Unigrams + bigrams are useful for phrases like:
            # "open house"
            # "this weekend"
            # "best neighborhoods"
            # "property taxes"
            ngram_range=(1, 2),

            lowercase=True,
            strip_accents="unicode",

            # I would NOT remove stop words here.
            #
            # Words such as "when", "where", "this",
            # "near", "for", etc. can carry useful intent signals.
            stop_words=None,

            sublinear_tf=True,
        )

        self.model = LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=random_state,
        )

        self.labels = list(
            VALID_LABELS
        )

        self._is_trained = False

    # =========================================================
    # TRAINING
    # =========================================================

    def train(
        self,
        queries: Sequence[str],
        labels: Sequence[str],
    ) -> None:
        """
        Train the classifier.
        """

        self._validate_training_data(
            queries,
            labels,
        )

        X = self.vectorizer.fit_transform(
            queries
        )

        self.model.fit(
            X,
            labels,
        )

        self._is_trained = True

    # =========================================================
    # PREDICTION
    # =========================================================

    def predict(
        self,
        query: str,
    ) -> Tuple[str, float]:
        """
        Return:

            (intent, confidence)
        """

        prediction = (
            self.predict_detailed(
                query
            )
        )

        return (
            prediction.intent,
            prediction.confidence,
        )

    def predict_detailed(
        self,
        query: str,
    ) -> IntentPrediction:
        """
        Return:
            intent
            confidence
            probabilities for every class
            uncertain flag
        """

        self._ensure_trained()

        query = self._validate_query(
            query
        )

        X = self.vectorizer.transform(
            [query]
        )

        probabilities = (
            self.model.predict_proba(
                X
            )[0]
        )

        classes = self.model.classes_

        best_index = int(
            np.argmax(
                probabilities
            )
        )

        intent = str(
            classes[
                best_index
            ]
        )

        confidence = float(
            probabilities[
                best_index
            ]
        )

        probability_map = {
            str(label): float(probability)
            for label, probability
            in zip(
                classes,
                probabilities,
            )
        }

        return IntentPrediction(
            intent=intent,
            confidence=confidence,
            probabilities=probability_map,
            uncertain=(
                confidence
                < self.confidence_threshold
            ),
        )

    def predict_batch(
        self,
        queries: Iterable[str],
    ) -> List[IntentPrediction]:
        """
        Predict multiple queries.
        """

        return [
            self.predict_detailed(
                query
            )
            for query in queries
        ]

    # =========================================================
    # WEEK 4 QUERY PARSER INTEGRATION
    # =========================================================

    def understand_query(
        self,
        query: str,
        parser: QueryParser,
    ) -> Dict[str, object]:
        """
        Combine Week 4 structured query parsing with
        intent classification.

        Example output:

        {
            "query": "...",

            "filters": {
                "city": "Irvine",
                "price_max": 900000,
                ...
            },

            "intent": "high_intent_inquiry",

            "intent_confidence": 0.81,

            "intent_uncertain": False,

            "intent_probabilities": {
                ...
            }
        }
        """

        query = self._validate_query(
            query
        )

        parsed_filters = parser.parse(
            query
        )

        prediction = (
            self.predict_detailed(
                query
            )
        )

        return {
            "query": query,

            "filters": parsed_filters,

            "intent": (
                prediction.intent
            ),

            "intent_confidence": (
                prediction.confidence
            ),

            "intent_uncertain": (
                prediction.uncertain
            ),

            "intent_probabilities": (
                prediction.probabilities
            ),
        }

    # =========================================================
    # EVALUATION
    # =========================================================

    def evaluate(
        self,
        queries: Sequence[str],
        labels: Sequence[str],
    ) -> Dict[str, object]:
        """
        Evaluate against held-out labeled data.
        """

        self._ensure_trained()

        if len(queries) != len(labels):
            raise ValueError(
                "queries and labels must have the same length"
            )

        if len(queries) == 0:
            raise ValueError(
                "evaluation data cannot be empty"
            )

        X = self.vectorizer.transform(
            queries
        )

        predicted = (
            self.model.predict(
                X
            )
        )

        accuracy = float(
            accuracy_score(
                labels,
                predicted,
            )
        )

        report = (
            classification_report(
                labels,
                predicted,
                labels=list(
                    VALID_LABELS
                ),
                output_dict=True,
                zero_division=0,
            )
        )

        matrix = (
            confusion_matrix(
                labels,
                predicted,
                labels=list(
                    VALID_LABELS
                ),
            )
        )

        return {
            "accuracy": accuracy,
            "classification_report": report,
            "confusion_matrix": (
                matrix.tolist()
            ),
        }

    # =========================================================
    # HOLDOUT TRAINING
    # =========================================================

    @classmethod
    def train_with_holdout(
        cls,
        queries: Sequence[str],
        labels: Sequence[str],
        test_size: float = 0.20,
        random_state: int = 42,
        **classifier_kwargs,
    ) -> Tuple[
        "QueryIntentClassifier",
        Dict[str, object],
    ]:
        """
        Split dataset into train/test sets using stratification.

        Returns:
            trained classifier
            evaluation metrics
        """

        cls._validate_training_data(
            queries,
            labels,
        )

        (
            X_train,
            X_test,
            y_train,
            y_test,
        ) = train_test_split(
            list(queries),
            list(labels),
            test_size=test_size,
            random_state=random_state,
            stratify=list(labels),
        )

        classifier = cls(
            random_state=random_state,
            **classifier_kwargs,
        )

        classifier.train(
            X_train,
            y_train,
        )

        metrics = classifier.evaluate(
            X_test,
            y_test,
        )

        metrics[
            "train_size"
        ] = len(
            X_train
        )

        metrics[
            "test_size"
        ] = len(
            X_test
        )

        metrics[
            "test_queries"
        ] = X_test

        metrics[
            "test_labels"
        ] = y_test

        return (
            classifier,
            metrics,
        )

    # =========================================================
    # MODEL SAVE / LOAD
    # =========================================================

    def save(
        self,
        path: str,
    ) -> None:
        """
        Save trained classifier to disk.
        """

        self._ensure_trained()

        joblib.dump(
            {
                "vectorizer": (
                    self.vectorizer
                ),

                "model": (
                    self.model
                ),

                "confidence_threshold": (
                    self.confidence_threshold
                ),

                "max_features": (
                    self.max_features
                ),

                "random_state": (
                    self.random_state
                ),
            },
            path,
        )

    @classmethod
    def load(
        cls,
        path: str,
    ) -> "QueryIntentClassifier":
        """
        Load saved classifier.
        """

        data = joblib.load(
            path
        )

        classifier = cls(
            max_features=data[
                "max_features"
            ],

            confidence_threshold=data[
                "confidence_threshold"
            ],

            random_state=data[
                "random_state"
            ],
        )

        classifier.vectorizer = (
            data["vectorizer"]
        )

        classifier.model = (
            data["model"]
        )

        classifier._is_trained = True

        return classifier

    # =========================================================
    # VALIDATION
    # =========================================================

    def _ensure_trained(
        self,
    ) -> None:

        if not self._is_trained:

            raise RuntimeError(
                "Classifier has not been trained yet"
            )

    @staticmethod
    def _validate_query(
        query: str,
    ) -> str:

        if not isinstance(
            query,
            str,
        ):
            raise TypeError(
                "query must be a string"
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "query cannot be empty"
            )

        return query

    @staticmethod
    def _validate_training_data(
        queries: Sequence[str],
        labels: Sequence[str],
    ) -> None:

        if len(queries) != len(labels):

            raise ValueError(
                "queries and labels must have the same length"
            )

        if len(queries) == 0:

            raise ValueError(
                "training data cannot be empty"
            )

        invalid_labels = (
            sorted(
                set(labels)
                - set(VALID_LABELS)
            )
        )

        if invalid_labels:

            raise ValueError(
                f"invalid labels: "
                f"{invalid_labels}"
            )

        if len(
            set(labels)
        ) < 2:

            raise ValueError(
                "training data must contain "
                "at least two intent classes"
            )

        for query in queries:

            if (
                not isinstance(
                    query,
                    str,
                )
                or not query.strip()
            ):

                raise ValueError(
                    "all training queries must "
                    "be non-empty strings"
                )


# =============================================================
# TRAIN + EVALUATE
# =============================================================

if __name__ == "__main__":

    DATA_PATH = (
        "data/processed/"
        "california_homebuyer_queries.csv"
    )

    df = pd.read_csv(
        DATA_PATH
    )

    # ---------------------------------------------------------
    # DATASET VALIDATION
    # ---------------------------------------------------------

    if "query" not in df.columns:
        raise ValueError(
            "Dataset must contain a 'query' column"
        )

    if "category" not in df.columns:
        raise ValueError(
            "Dataset must contain a 'category' column"
        )

    # Remove incomplete rows.
    df = df.dropna(
        subset=[
            "query",
            "category",
        ]
    )

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

    print(
        "=" * 60
    )

    print(
        "INTENT CLASSIFICATION DATASET"
    )

    print(
        "=" * 60
    )

    print(
        f"Total queries: {len(df)}"
    )

    print()

    print(
        "Label distribution:"
    )

    print(
        df[
            "category"
        ].value_counts()
    )

    print()

    # ---------------------------------------------------------
    # DELIVERABLE: 200+ LABELED QUERIES
    # ---------------------------------------------------------

    if len(df) < 200:

        print(
            "WARNING: Dataset contains "
            f"only {len(df)} queries. "
            "Requirement is 200+."
        )

    # ---------------------------------------------------------
    # TRAIN WITH HOLDOUT
    # ---------------------------------------------------------

    classifier, metrics = (
        QueryIntentClassifier.train_with_holdout(
            queries=(
                df[
                    "query"
                ].tolist()
            ),

            labels=(
                df[
                    "category"
                ].tolist()
            ),

            test_size=0.20,

            random_state=42,

            confidence_threshold=0.55,
        )
    )

    # ---------------------------------------------------------
    # RESULTS
    # ---------------------------------------------------------

    print()
    print(
        "=" * 60
    )

    print(
        "HELD-OUT TEST RESULTS"
    )

    print(
        "=" * 60
    )

    print(
        f"Training examples: "
        f"{metrics['train_size']}"
    )

    print(
        f"Testing examples:  "
        f"{metrics['test_size']}"
    )

    print()

    accuracy = (
        metrics["accuracy"]
    )

    print(
        f"Accuracy: "
        f"{accuracy:.2%}"
    )

    print(
        "Requirement: >= 80%"
    )

    print(
        "Result:",
        (
            "PASS"
            if accuracy >= 0.80
            else "FAIL"
        ),
    )

    print()

    # ---------------------------------------------------------
    # CLASSIFICATION REPORT
    # ---------------------------------------------------------

    report = (
        metrics[
            "classification_report"
        ]
    )

    print(
        "PER-CLASS RESULTS"
    )

    print(
        "-" * 60
    )

    for label in VALID_LABELS:

        values = report[
            label
        ]

        print(
            f"{label:<22} "
            f"precision={values['precision']:.2%} "
            f"recall={values['recall']:.2%} "
            f"f1={values['f1-score']:.2%}"
        )

    # ---------------------------------------------------------
    # UNCERTAIN PREDICTIONS
    # ---------------------------------------------------------

    uncertain_count = 0

    print()
    print(
        "=" * 60
    )

    print(
        "UNCERTAIN TEST PREDICTIONS"
    )

    print(
        "=" * 60
    )

    for query in (
        metrics[
            "test_queries"
        ]
    ):

        prediction = (
            classifier.predict_detailed(
                query
            )
        )

        if prediction.uncertain:

            uncertain_count += 1

            print(
                f"\nQUERY: {query}"
            )

            print(
                f"Intent: "
                f"{prediction.intent}"
            )

            print(
                f"Confidence: "
                f"{prediction.confidence:.2%}"
            )

            print(
                "Probabilities:"
            )

            for (
                label,
                probability,
            ) in (
                prediction
                .probabilities
                .items()
            ):

                print(
                    f"    "
                    f"{label:<22} "
                    f"{probability:.2%}"
                )

    print()

    print(
        f"Uncertain predictions: "
        f"{uncertain_count}/"
        f"{metrics['test_size']}"
    )

    # ---------------------------------------------------------
    # SAVE MODEL
    # ---------------------------------------------------------

    model_path = (
        "data/processed/"
        "query_intent_classifier.joblib"
    )

    classifier.save(
        model_path
    )

    print()

    print(
        f"Model saved to: "
        f"{model_path}"
    )
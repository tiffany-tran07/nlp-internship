import json

import pandas as pd

from scripts.entity_extractor import EntityExtractor


extractor = EntityExtractor()

df = pd.read_csv(
    "data/processed/listings_entity_gold.csv"
)

def normalize_numeric(value):
    if pd.isna(value):
        return None

    value = float(value)

    if value.is_integer():
        return int(value)

    return value


def price_matches(true_price, pred_price, tolerance=0.01):
    if pd.isna(true_price) or pred_price is None:
        return False

    true_price = float(true_price)
    pred_price = float(pred_price)

    difference = abs(true_price - pred_price)

    return difference <= true_price * tolerance


def calculate_f1(tp, fp, fn):
    precision = (
        tp / (tp + fp)
        if (tp + fp)
        else 0
    )

    recall = (
        tp / (tp + fn)
        if (tp + fn)
        else 0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if (precision + recall)
        else 0
    )

    return precision, recall, f1


def evaluate_numeric_entity(
    entity_name,
    true_column
):

    tp = 0
    fp = 0
    fn = 0

    errors = []

    for _, row in df.iterrows():

        result = extractor.extract_all(
           [row["remarks"]]
        )

        gold = normalize_numeric(
            row[true_column]
        )

        predicted = result[
            entity_name
        ]

        # Special handling for price because
        # listing text may contain rounded values.
        if entity_name == "price":

            if gold is None and predicted is None:
                continue

            if gold is not None and predicted is not None:

                if price_matches(
                    gold,
                    predicted
                ):
                    tp += 1

                else:
                    fp += 1
                    fn += 1

                    errors.append({
                        "text": row["text"],
                        "gold": gold,
                        "predicted": predicted
                    })

            elif gold is not None:
                fn += 1

            else:
                fp += 1

            continue

        # Normal numeric entities
        if gold is None and predicted is None:
            continue

        if gold == predicted:
            tp += 1

        elif gold is not None and predicted is None:
            fn += 1

            errors.append({
                "text": row["text"],
                "gold": gold,
                "predicted": predicted
            })

        elif gold is None and predicted is not None:
            fp += 1

            errors.append({
                "text": row["text"],
                "gold": gold,
                "predicted": predicted
            })

        else:
            # Wrong prediction counts as both:
            # false positive prediction
            # and false negative gold entity
            fp += 1
            fn += 1

            errors.append({
                "text": row["text"],
                "gold": gold,
                "predicted": predicted
            })

    precision, recall, f1 = calculate_f1(
        tp,
        fp,
        fn
    )

    return {
        "entity": entity_name,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "errors": errors
    }


def test_bedroom_f1():

    metrics = evaluate_numeric_entity(
        "bedrooms",
        "bedrooms"
    )

    print("\nBEDROOM F1")
    print("----------------")

    print(
        f"Precision: "
        f"{metrics['precision']:.3f}"
    )

    print(
        f"Recall:    "
        f"{metrics['recall']:.3f}"
    )

    print(
        f"F1:        "
        f"{metrics['f1']:.3f}"
    )

    assert metrics["f1"] >= 0.85


def test_bathroom_f1():

    metrics = evaluate_numeric_entity(
        "bathrooms",
        "bathrooms"
    )

    print("\nBATHROOM F1")
    print("-----------------")

    print(
        f"Precision: "
        f"{metrics['precision']:.3f}"
    )

    print(
        f"Recall:    "
        f"{metrics['recall']:.3f}"
    )

    print(
        f"F1:        "
        f"{metrics['f1']:.3f}"
    )

    assert metrics["f1"] >= 0.85


def test_price_f1():

    metrics = evaluate_numeric_entity(
        "price",
        "price"
    )

    print("\nPRICE F1")
    print("--------")

    print(
        f"Precision: "
        f"{metrics['precision']:.3f}"
    )

    print(
        f"Recall:    "
        f"{metrics['recall']:.3f}"
    )

    print(
        f"F1:        "
        f"{metrics['f1']:.3f}"
    )

    assert metrics["f1"] >= 0.85


def test_sqft_f1():

    metrics = evaluate_numeric_entity(
        "sqft",
        "sqft"
    )

    print("\nSQFT F1")
    print("-------")

    print(
        f"Precision: "
        f"{metrics['precision']:.3f}"
    )

    print(
        f"Recall:    "
        f"{metrics['recall']:.3f}"
    )

    print(
        f"F1:        "
        f"{metrics['f1']:.3f}"
    )

    assert metrics["f1"] >= 0.85

if __name__ == "__main__":

    extractor = EntityExtractor(
        taxonomy_path="data/processed/taxonomy.json"
    )

    df = pd.read_csv(
        "data/processed/listings_entity_gold.csv"
    )

    print("NUMERIC ENTITY EVALUATION")
    print("-------------------------")

    for entity_name, column_name in [
        ("bedrooms", "bed"),
        ("bathrooms", "bath"),
        ("price", "price"),
    ]:

        metrics = evaluate_numeric_entity(
            # extractor,
            # df,
            entity_name,
            column_name
        )

        print(f"\n{entity_name.upper()}")
        print(f"TP:        {metrics['tp']}")
        print(f"FP:        {metrics['fp']}")
        print(f"FN:        {metrics['fn']}")
        print(f"Precision: {metrics['precision']:.3f}")
        print(f"Recall:    {metrics['recall']:.3f}")
        print(f"F1:        {metrics['f1']:.3f}")
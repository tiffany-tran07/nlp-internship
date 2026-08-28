# scripts/analyze_entity_errors.py

import pandas as pd
from collections import Counter


def parse_terms(value):
    if pd.isna(value):
        return set()

    return {
        term.strip().lower()
        for term in str(value).split(";")
        if term.strip()
    }


results = pd.read_csv(
    "data/processed/entity_eval_results.csv"
)


# -------------------------
# NUMERIC FAILURES
# -------------------------

print("BEDROOM FAILURES")
print("----------------")

bed_failures = results[
    ~results["bed_correct"]
]

print(
    bed_failures[
        [
            "listing_id",
            "true_bed",
            "pred_bed"
        ]
    ]
)


print("\nBATHROOM FAILURES")
print("-----------------")

bath_failures = results[
    ~results["bath_correct"]
]

print(
    bath_failures[
        [
            "listing_id",
            "true_bath",
            "pred_bath"
        ]
    ]
)


print("\nPRICE FAILURES")
print("--------------")

price_failures = results[
    ~results["price_correct"]
]

print(
    price_failures[
        [
            "listing_id",
            "true_price",
            "pred_price"
        ]
    ]
)


# -------------------------
# ENTITY FAILURES
# -------------------------

false_negatives = []
false_positives = []


for _, row in results.iterrows():

    gold = parse_terms(
        row["true_amenities"]
    )

    predicted = parse_terms(
        row["pred_entities"]
    )

    false_negatives.extend(
        gold - predicted
    )

    false_positives.extend(
        predicted - gold
    )


print("\nMOST COMMON MISSED ENTITIES")
print("---------------------------")

for term, count in Counter(
    false_negatives
).most_common(15):

    print(
        f"{term}: {count}"
    )


print("\nMOST COMMON FALSE POSITIVES")
print("---------------------------")

for term, count in Counter(
    false_positives
).most_common(15):

    print(
        f"{term}: {count}"
    )
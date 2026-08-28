import pandas as pd

from scripts.entity_extractor import EntityExtractor


def parse_terms(value):
    if pd.isna(value):
        return set()

    return {
        term.strip().lower()
        for term in str(value).split(";")
        if term.strip()
    }


def flatten_entities(entities):
    terms = []

    for category_terms in entities.values():
        terms.extend(category_terms)

    return terms

def price_matches(true_price, pred_price, tolerance=0.01):
    if pd.isna(true_price) or pd.isna(pred_price):
        return False

    difference = abs(true_price - pred_price)

    return difference <= true_price * tolerance


def calculate_metrics(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0

    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0
    )

    return precision, recall, f1


extractor = EntityExtractor()

listings = pd.read_csv(
    "data/processed/listings_entity_gold.csv"
)

results = []


for _, row in listings.iterrows():

    extracted = extractor.extract_all(
        row["remarks"]
    )

    all_taxonomy_entities = flatten_entities(
        extracted["entities"]
    )

    results.append({
        "listing_id": row["listing_id"],

        "true_bed": row["bed"],
        "pred_bed": extracted["bedrooms"],

        "true_bath": row["bath"],
        "pred_bath": extracted["bathrooms"],

        "true_price": row["price"],
        "pred_price": extracted["price"],

        "true_amenities": row["amenities"],

        # Compare against all taxonomy features because
        # your old amenities column is broader than the
        # new taxonomy's "amenities" category.
        "pred_entities": ";".join(
            all_taxonomy_entities
        )
    })


eval_df = pd.DataFrame(results)


# -------------------------
# NUMERIC ENTITY ACCURACY
# -------------------------

eval_df["bed_correct"] = (
    eval_df["true_bed"]
    == eval_df["pred_bed"]
)

eval_df["bath_correct"] = (
    eval_df["true_bath"]
    == eval_df["pred_bath"]
)

eval_df["price_correct"] = eval_df.apply(
    lambda row: price_matches(
        row["true_price"],
        row["pred_price"]
    ),
    axis=1
)


bed_accuracy = eval_df["bed_correct"].mean()
bath_accuracy = eval_df["bath_correct"].mean()
price_accuracy = eval_df["price_correct"].mean()


print("NUMERIC ENTITY ACCURACY")
print("-----------------------")

print(
    f"Bedroom accuracy:  {bed_accuracy:.3f}"
)

print(
    f"Bathroom accuracy: {bath_accuracy:.3f}"
)

print(
    f"Price accuracy:    {price_accuracy:.3f}"
)


# -------------------------
# TAXONOMY ENTITY F1
# -------------------------

tp = 0
fp = 0
fn = 0


for _, row in eval_df.iterrows():

    gold = parse_terms(
        row["true_amenities"]
    )

    predicted = parse_terms(
        row["pred_entities"]
    )

    tp += len(
        gold & predicted
    )

    fp += len(
        predicted - gold
    )

    fn += len(
        gold - predicted
    )


precision, recall, f1 = calculate_metrics(
    tp,
    fp,
    fn
)


print("\nTAXONOMY ENTITY EVALUATION")
print("--------------------------")

print(f"True positives:  {tp}")
print(f"False positives: {fp}")
print(f"False negatives: {fn}")

print(f"Precision: {precision:.3f}")
print(f"Recall:    {recall:.3f}")
print(f"F1:        {f1:.3f}")


if f1 >= 0.85:
    print("\n✓ Target met: F1 >= 0.85")
else:
    print(
        f"\n✗ Target not met: "
        f"F1 = {f1:.3f}"
    )


# -------------------------
# SAVE RESULTS
# -------------------------

eval_df.to_csv(
    "data/processed/entity_eval_results.csv",
    index=False
)

print(
    "\nSaved results to "
    "data/processed/entity_eval_results.csv"
)
import json
import pandas as pd
from collections import Counter

from scripts.entity_extractor import EntityExtractor


def build_alias_lookup(
    taxonomy_path="data/processed/taxonomy.json"
):
    """
    Build a lookup so aliases map back to their
    canonical taxonomy term.

    Example:
        "solar panels" -> "solar"
    """

    with open(taxonomy_path, "r") as f:
        taxonomy = json.load(f)

    lookup = {}

    for category, terms in taxonomy.get(
        "categories",
        {}
    ).items():

        for term_obj in terms:

            canonical = (
                term_obj["term"]
                .strip()
                .lower()
            )

            # Canonical term maps to itself
            lookup[canonical] = canonical

            # Aliases map to canonical term
            for alias in term_obj.get(
                "aliases",
                []
            ):

                normalized_alias = (
                    alias
                    .strip()
                    .lower()
                )

                lookup[
                    normalized_alias
                ] = canonical

    return lookup


def parse_terms(
    value,
    alias_lookup
):
    """
    Parse semicolon-separated gold labels and
    normalize aliases to canonical taxonomy terms.
    """

    if pd.isna(value):
        return set()

    terms = {
        term.strip().lower()
        for term in str(value).split(";")
        if term.strip()
    }

    normalized_terms = {
        alias_lookup.get(
            term,
            term
        )
        for term in terms
    }

    return normalized_terms


def flatten_entities(entities):
    """
    Convert the extractor's categorized output:

        {
            "amenities": ["pool"],
            "exterior": ["garage"]
        }

    into:

        {"pool", "garage"}
    """

    flattened = set()

    for category_terms in entities.values():

        for term in category_terms:

            if term:
                flattened.add(
                    term.strip().lower()
                )

    return flattened


if __name__ == "__main__":

    taxonomy_path = (
        "data/processed/taxonomy.json"
    )

    listings_path = (
        "data/processed/"
        "listings_entity_gold.csv"
    )

    output_path = (
        "data/processed/"
        "taxonomy_eval_results.csv"
    )

    # --------------------------------
    # INITIALIZE
    # --------------------------------

    extractor = EntityExtractor(
        taxonomy_path=taxonomy_path
    )

    df = pd.read_csv(
        listings_path
    )

    alias_lookup = build_alias_lookup(
        taxonomy_path
    )

    # --------------------------------
    # EVALUATION COUNTERS
    # --------------------------------

    matched = 0
    missed = 0

    missed_terms = []

    results = []

    # --------------------------------
    # EVALUATE EVERY LISTING
    # --------------------------------

    for _, row in df.iterrows():

        text = row["remarks"]

        extracted = extractor.extract_all(
            text
        )

        # Flatten all 8 taxonomy categories
        # into one set of predicted concepts.
        predicted = flatten_entities(
            extracted["entities"]
        )

        # Convert manually labeled features
        # into canonical taxonomy terms.
        gold = parse_terms(
            row["gold_features"],
            alias_lookup
        )

        # Correctly found gold features
        found = (
            gold
            & predicted
        )

        # Gold features the extractor missed
        missing = (
            gold
            - predicted
        )

        matched += len(found)
        missed += len(missing)

        missed_terms.extend(
            missing
        )

        results.append({
            "listing_id":
                row["listing_id"],

            "gold_features":
                ";".join(
                    sorted(gold)
                ),

            "predicted_entities":
                ";".join(
                    sorted(predicted)
                ),

            "matched_features":
                ";".join(
                    sorted(found)
                ),

            "missed_features":
                ";".join(
                    sorted(missing)
                ),

            "gold_count":
                len(gold),

            "matched_count":
                len(found),

            "missed_count":
                len(missing)
        })

    # --------------------------------
    # FEATURE RECALL
    # --------------------------------

    total_gold = (
        matched
        + missed
    )

    feature_recall = (
        matched / total_gold
        if total_gold
        else 0
    )

    print()
    print(
        "TAXONOMY FEATURE EVALUATION"
    )
    print(
        "---------------------------"
    )

    print(
        f"Matched features: {matched}"
    )

    print(
        f"Missed features:  {missed}"
    )

    print(
        f"Total gold:       {total_gold}"
    )

    print(
        f"Feature recall:   "
        f"{feature_recall:.3f}"
    )

    # --------------------------------
    # SAVE DETAILED RESULTS
    # --------------------------------

    results_df = pd.DataFrame(
        results
    )

    results_df.to_csv(
        output_path,
        index=False
    )

    print()
    print(
        "Saved results to "
        f"{output_path}"
    )

    # --------------------------------
    # MISSED FEATURE ANALYSIS
    # --------------------------------

    print()
    print(
        "MOST COMMON MISSED FEATURES"
    )

    print(
        "---------------------------"
    )

    missed_counter = Counter(
        missed_terms
    )

    for term, count in (
        missed_counter
        .most_common(20)
    ):

        print(
            f"{term}: {count}"
        )

    # --------------------------------
    # PER-CATEGORY GOLD RECALL
    # --------------------------------

    category_columns = {
        "property_type":
            "gold_property_type",

        "interior":
            "gold_interior",

        "kitchen":
            "gold_kitchen",

        "exterior":
            "gold_exterior",

        "amenities":
            "gold_amenities",

        "location":
            "gold_location",

        "condition":
            "gold_condition",

        "views_environment":
            "gold_views_environment"
    }

    print()
    print(
        "RECALL BY TAXONOMY CATEGORY"
    )

    print(
        "---------------------------"
    )

    for category, column_name in (
        category_columns.items()
    ):

        if column_name not in df.columns:
            continue

        category_matched = 0
        category_missed = 0

        for _, row in df.iterrows():

            gold = parse_terms(
                row[column_name],
                alias_lookup
            )

            if not gold:
                continue

            extracted = (
                extractor.extract_all(
                    row["remarks"]
                )
            )

            predicted = {
                term.strip().lower()
                for term in (
                    extracted[
                        "entities"
                    ].get(
                        category,
                        []
                    )
                )
            }

            found = (
                gold
                & predicted
            )

            missing = (
                gold
                - predicted
            )

            category_matched += len(
                found
            )

            category_missed += len(
                missing
            )

        category_total = (
            category_matched
            + category_missed
        )

        category_recall = (
            category_matched
            / category_total
            if category_total
            else 0
        )

        print(
            f"{category:20} "
            f"{category_recall:.3f} "
            f"({category_matched}/"
            f"{category_total})"
        )
# scripts/generate_extracted_entities.py

import json
from pathlib import Path

import pandas as pd

from scripts.entity_extractor import EntityExtractor


INPUT_PATH = Path(
    "data/processed/cleaned_listing_sample.csv"
)

OUTPUT_PATH = Path(
    "data/processed/listing_sample_with_entities.csv"
)


def generate_entity_csv(
    input_path=INPUT_PATH,
    output_path=OUTPUT_PATH,
):
    """
    Read cleaned_listing_sample.csv, extract entities from each
    listing's remarks, and save the results to a new CSV.

    Original columns are preserved and extracted entity columns
    are added.
    """

    # ---------------------------------------------------------
    # LOAD DATA
    # ---------------------------------------------------------

    df = pd.read_csv(input_path)

    print(f"Loaded {len(df)} listings")

    if "cleaned_remarks" not in df.columns:
        raise ValueError(
            "Input CSV must contain an cleaned_remarks column"
        )

    # ---------------------------------------------------------
    # CREATE ENTITY EXTRACTOR
    # ---------------------------------------------------------

    extractor = EntityExtractor(
        taxonomy_path="data/processed/taxonomy.json"
    )

    # ---------------------------------------------------------
    # STORAGE FOR EXTRACTED VALUES
    # ---------------------------------------------------------

    extracted_bedrooms = []
    extracted_bathrooms = []
    extracted_prices = []
    extracted_sqft = []

    extracted_amenities = []
    extracted_property_type = []
    extracted_interior = []
    extracted_kitchen = []
    extracted_exterior = []
    extracted_location = []
    extracted_condition = []
    extracted_views_environment = []

    extracted_entities_json = []

    # ---------------------------------------------------------
    # PROCESS EACH LISTING
    # ---------------------------------------------------------

    total = len(df)

    for index, row in df.iterrows():

        remarks = row.get(
            "cleaned_remarks",
            "",
        )

        # Handle NaN remarks.
        if pd.isna(remarks):
            remarks = ""

        remarks = str(remarks)

        result = extractor.extract_all(
            remarks
        )

        entities = result.get(
            "entities",
            {},
        )

        # -----------------------------------------------------
        # NUMERIC ENTITIES
        # -----------------------------------------------------

        extracted_bedrooms.append(
            result.get("bedrooms")
        )

        extracted_bathrooms.append(
            result.get("bathrooms")
        )

        extracted_prices.append(
            result.get("price")
        )

        extracted_sqft.append(
            result.get("sqft")
        )

        # -----------------------------------------------------
        # TAXONOMY ENTITIES
        # -----------------------------------------------------

        extracted_amenities.append(
            json.dumps(
                result.get(
                    "amenities",
                    [],
                ),
                ensure_ascii=False,
            )
        )

        extracted_property_type.append(
            json.dumps(
                entities.get(
                    "property_type",
                    [],
                ),
                ensure_ascii=False,
            )
        )

        extracted_interior.append(
            json.dumps(
                entities.get(
                    "interior",
                    [],
                ),
                ensure_ascii=False,
            )
        )

        extracted_kitchen.append(
            json.dumps(
                entities.get(
                    "kitchen",
                    [],
                ),
                ensure_ascii=False,
            )
        )

        extracted_exterior.append(
            json.dumps(
                entities.get(
                    "exterior",
                    [],
                ),
                ensure_ascii=False,
            )
        )

        extracted_location.append(
            json.dumps(
                entities.get(
                    "location",
                    [],
                ),
                ensure_ascii=False,
            )
        )

        extracted_condition.append(
            json.dumps(
                entities.get(
                    "condition",
                    [],
                ),
                ensure_ascii=False,
            )
        )

        extracted_views_environment.append(
            json.dumps(
                entities.get(
                    "views_environment",
                    [],
                ),
                ensure_ascii=False,
            )
        )

        # Keep the complete entity dictionary too.
        extracted_entities_json.append(
            json.dumps(
                entities,
                ensure_ascii=False,
            )
        )

        # -----------------------------------------------------
        # PROGRESS
        # -----------------------------------------------------

        if (
            (index + 1) % 100 == 0
            or index + 1 == total
        ):
            print(
                f"Processed {index + 1}/{total}"
            )

    # ---------------------------------------------------------
    # ADD COLUMNS
    # ---------------------------------------------------------

    df["extracted_bedrooms"] = (
        extracted_bedrooms
    )

    df["extracted_bathrooms"] = (
        extracted_bathrooms
    )

    df["extracted_price"] = (
        extracted_prices
    )

    df["extracted_sqft"] = (
        extracted_sqft
    )

    df["extracted_amenities"] = (
        extracted_amenities
    )

    df["extracted_property_type"] = (
        extracted_property_type
    )

    df["extracted_interior"] = (
        extracted_interior
    )

    df["extracted_kitchen"] = (
        extracted_kitchen
    )

    df["extracted_exterior"] = (
        extracted_exterior
    )

    df["extracted_location"] = (
        extracted_location
    )

    df["extracted_condition"] = (
        extracted_condition
    )

    df["extracted_views_environment"] = (
        extracted_views_environment
    )

    df["extracted_entities"] = (
        extracted_entities_json
    )

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_path,
        index=False,
    )

    print()
    print("=" * 60)
    print("ENTITY EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Listings processed: {len(df)}")
    print(f"Output: {output_path}")
    print("=" * 60)

    return df


if __name__ == "__main__":
    generate_entity_csv()
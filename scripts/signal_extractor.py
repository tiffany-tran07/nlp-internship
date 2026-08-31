# scripts/signal_extractor.py

import json
import re
from pathlib import Path

import pandas as pd

from scripts.entity_extractor import EntityExtractor
from scripts.text_cleaning import TextCleaner


class SignalExtractor:
    """
    Combine structured listing fields with Week 3 entity extraction
    and additional free-text signals.

    Uses:
        - Structured fields from the listing record
        - EntityExtractor for taxonomy/entities
        - TextCleaner for additional SignalExtractor patterns
        - Financing patterns
    """

    FINANCING_TERMS = {
        "seller financing": [
            "seller financing",
            "seller financing available",
            "owner financing",
            "owner will carry",
            "seller will carry",
            "seller carry",
        ],

        "cash only": [
            "cash only",
            "cash buyers only",
            "cash buyer only",
        ],

        "fha": [
            "fha",
            "fha financing",
            "fha eligible",
        ],

        "va": [
            "va loan",
            "va financing",
            "va eligible",
        ],

        "conventional": [
            "conventional financing",
            "conventional loan",
        ],

        "assumable loan": [
            "assumable loan",
            "assumable mortgage",
        ],
    }

    def __init__(
        self,
        entity_extractor=None,
        taxonomy_path="data/processed/taxonomy.json",
    ):
        # Reuse existing Week 3 EntityExtractor.
        self.entity_extractor = (
            entity_extractor
            if entity_extractor is not None
            else EntityExtractor(
                taxonomy_path=taxonomy_path
            )
        )

        # Use the same cleaner implementation for
        # SignalExtractor-owned free-text logic.
        self.cleaner = TextCleaner()

        self._compiled_financing = (
            self._compile_financing()
        )

    # =========================================================
    # GENERAL HELPERS
    # =========================================================

    @staticmethod
    def _clean_value(value):
        """
        Convert pandas NaN/missing structured fields to None.
        """

        if value is None:
            return None

        try:
            if pd.isna(value):
                return None

        except (TypeError, ValueError):
            pass

        # Convert 3.0 -> 3 when appropriate.
        if isinstance(value, float):
            if value.is_integer():
                return int(value)

        return value

    # =========================================================
    # FINANCING
    # =========================================================

    def _compile_financing(self):
        """
        Compile financing phrases after applying TextCleaner.

        This ensures our patterns use the same normalized form
        as listing remarks.
        """

        compiled = []

        for canonical, variants in (
            self.FINANCING_TERMS.items()
        ):

            for variant in variants:

                cleaned_variant = (
                    self.cleaner.clean_text(
                        variant
                    )
                )

                if not cleaned_variant:
                    continue

                pattern = re.compile(
                    r"\b"
                    + re.escape(
                        cleaned_variant
                    )
                    + r"\b",
                    re.IGNORECASE,
                )

                compiled.append(
                    (
                        canonical,
                        pattern,
                    )
                )

        return compiled

    def _extract_financing(
        self,
        cleaned_remarks,
    ):
        """
        Extract financing terms from already-cleaned remarks.
        """

        if not cleaned_remarks:
            return []

        results = []

        for canonical, pattern in (
            self._compiled_financing
        ):

            if pattern.search(
                cleaned_remarks
            ):
                results.append(
                    canonical
                )

        return list(
            dict.fromkeys(results)
        )

    # =========================================================
    # STRUCTURED FIELDS
    # =========================================================

    def _extract_structured(
        self,
        listing_record,
    ):
        """
        Values that already exist in dedicated listing columns.
        """

        return {
            "city": self._clean_value(
                listing_record.get(
                    "L_City"
                )
            ),

            "price": self._clean_value(
                listing_record.get(
                    "L_SystemPrice"
                )
            ),

            "bedrooms": self._clean_value(
                listing_record.get(
                    "L_Keyword2"
                )
            ),

            "bathrooms": self._clean_value(
                listing_record.get(
                    "L_Keyword3"
                )
            ),
        }

    # =========================================================
    # TAXONOMY CATEGORY HELPERS
    # =========================================================

    @staticmethod
    def _get_category(
        entities,
        category,
    ):
        """
        Safely retrieve a taxonomy category.
        """

        if not isinstance(
            entities,
            dict,
        ):
            return []

        values = entities.get(
            category,
            [],
        )

        if not isinstance(
            values,
            list,
        ):
            return []

        return values

    def _build_amenities(
        self,
        entities,
    ):
        """
        Build broad searchable property features.

        Your taxonomy separates these into:
            interior
            kitchen
            exterior
            amenities

        For search/filtering purposes we combine them.
        """

        results = []

        for category in (
            "interior",
            "kitchen",
            "exterior",
            "amenities",
        ):

            results.extend(
                self._get_category(
                    entities,
                    category,
                )
            )

        return sorted(
            set(results)
        )

    def _build_location_features(
        self,
        entities,
    ):
        """
        Combine location and environment/view concepts.
        """

        results = []

        results.extend(
            self._get_category(
                entities,
                "location",
            )
        )

        results.extend(
            self._get_category(
                entities,
                "views_environment",
            )
        )

        return sorted(
            set(results)
        )

    @staticmethod
    def _build_keywords(
        entities,
    ):
        """
        Flatten all taxonomy categories into one unique keyword list.

        Useful for search indexing.
        """

        if not isinstance(
            entities,
            dict,
        ):
            return []

        keywords = []

        for values in entities.values():

            if isinstance(
                values,
                list,
            ):
                keywords.extend(
                    values
                )

        return sorted(
            set(keywords)
        )

    # =========================================================
    # SINGLE LISTING EXTRACTION
    # =========================================================

    def extract_signals(
        self,
        listing_record,
    ):
        """
        Process one complete listing record.
        """

        if not isinstance(
            listing_record,
            dict,
        ):
            raise TypeError(
                "listing_record must be a dictionary"
            )

        raw_remarks = (
            listing_record.get(
                "L_Remarks"
            )
        )

        if (
            raw_remarks is None
            or pd.isna(raw_remarks)
        ):
            raw_remarks = ""

        raw_remarks = str(
            raw_remarks
        )

        # -----------------------------------------------------
        # Clean once for SignalExtractor-specific matching.
        # -----------------------------------------------------

        cleaned_remarks = (
            self.cleaner.clean_text(
                raw_remarks
            )
        )

        # -----------------------------------------------------
        # Existing Week 3 EntityExtractor
        #
        # IMPORTANT:
        # Give it RAW remarks.
        #
        # EntityExtractor.extract_all() already handles its own
        # cleaning and needs raw text for price detection.
        # -----------------------------------------------------

        extracted = (
            self.entity_extractor.extract_all(
                raw_remarks
            )
        )

        taxonomy_entities = (
            extracted.get(
                "entities",
                {},
            )
        )

        # -----------------------------------------------------
        # OUTPUT
        # -----------------------------------------------------

        return {
            "listing_id": (
                self._clean_value(
                    listing_record.get(
                        "L_ListingID"
                    )
                )
            ),

            # ---------------------------------------------
            # Original structured database fields
            # ---------------------------------------------

            "structured": (
                self._extract_structured(
                    listing_record
                )
            ),

            # ---------------------------------------------
            # Week 3 EntityExtractor result
            # ---------------------------------------------

            "entities": extracted,

            # ---------------------------------------------
            # Search/index fields
            # ---------------------------------------------

            "amenities": (
                self._build_amenities(
                    taxonomy_entities
                )
            ),

            "condition": (
                self._get_category(
                    taxonomy_entities,
                    "condition",
                )
            ),

            "financing": (
                self._extract_financing(
                    cleaned_remarks
                )
            ),

            "location_features": (
                self._build_location_features(
                    taxonomy_entities
                )
            ),

            "property_type": (
                self._get_category(
                    taxonomy_entities,
                    "property_type",
                )
            ),

            "keywords": (
                self._build_keywords(
                    taxonomy_entities
                )
            ),
        }

    # =========================================================
    # PROCESS FULL CSV
    # =========================================================

    def process_csv(
        self,
        input_path="data/processed/cleaned_listing_sample.csv",
        output_path="data/processed/listing_signals.csv",
    ):
        """
        Process every listing in a CSV and save extracted signals
        as another CSV.
        """

        input_path = Path(
            input_path
        )

        output_path = Path(
            output_path
        )

        df = pd.read_csv(
            input_path
        )

        results = []

        total = len(df)

        for index, record in enumerate(
            df.to_dict(
                orient="records"
            ),
            start=1,
        ):

            signals = (
                self.extract_signals(
                    record
                )
            )

            # Flatten dictionaries/lists for CSV storage.
            row = {
                "listing_id": (
                    signals[
                        "listing_id"
                    ]
                ),

                "city": (
                    signals[
                        "structured"
                    ]["city"]
                ),

                "price": (
                    signals[
                        "structured"
                    ]["price"]
                ),

                "bedrooms": (
                    signals[
                        "structured"
                    ]["bedrooms"]
                ),

                "bathrooms": (
                    signals[
                        "structured"
                    ]["bathrooms"]
                ),

                # -----------------------------------------
                # EntityExtractor numeric results
                # -----------------------------------------

                "entity_bedrooms": (
                    signals[
                        "entities"
                    ].get(
                        "bedrooms"
                    )
                ),

                "entity_bathrooms": (
                    signals[
                        "entities"
                    ].get(
                        "bathrooms"
                    )
                ),

                "entity_price": (
                    signals[
                        "entities"
                    ].get(
                        "price"
                    )
                ),

                "entity_sqft": (
                    signals[
                        "entities"
                    ].get(
                        "sqft"
                    )
                ),

                # -----------------------------------------
                # Signal lists
                # -----------------------------------------

                "amenities": json.dumps(
                    signals[
                        "amenities"
                    ],
                    ensure_ascii=False,
                ),

                "condition": json.dumps(
                    signals[
                        "condition"
                    ],
                    ensure_ascii=False,
                ),

                "financing": json.dumps(
                    signals[
                        "financing"
                    ],
                    ensure_ascii=False,
                ),

                "location_features": json.dumps(
                    signals[
                        "location_features"
                    ],
                    ensure_ascii=False,
                ),

                "property_type": json.dumps(
                    signals[
                        "property_type"
                    ],
                    ensure_ascii=False,
                ),

                "keywords": json.dumps(
                    signals[
                        "keywords"
                    ],
                    ensure_ascii=False,
                ),

                # Full taxonomy entities are retained too.
                "taxonomy_entities": json.dumps(
                    signals[
                        "entities"
                    ].get(
                        "entities",
                        {},
                    ),
                    ensure_ascii=False,
                ),
            }

            results.append(
                row
            )

            if (
                index % 100 == 0
                or index == total
            ):
                print(
                    f"Processed "
                    f"{index}/{total}"
                )

        output_df = pd.DataFrame(
            results
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_df.to_csv(
            output_path,
            index=False,
        )

        print()
        print("=" * 60)
        print("SIGNAL EXTRACTION COMPLETE")
        print("=" * 60)
        print(
            f"Listings processed: "
            f"{len(output_df)}"
        )
        print(
            f"Saved to: "
            f"{output_path}"
        )
        print("=" * 60)

        return output_df


# =============================================================
# RUN DIRECTLY
# =============================================================

if __name__ == "__main__":

    extractor = SignalExtractor()

    extractor.process_csv(
        input_path=(
            "data/processed/"
            "cleaned_listing_sample.csv"
        ),
        output_path=(
            "data/processed/"
            "listing_signals.csv"
        ),
    )
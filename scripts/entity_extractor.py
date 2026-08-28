import json
import math
import re

from scripts.text_cleaning import TextCleaner


class EntityExtractor:

    def __init__(
        self,
        taxonomy_path="data/processed/taxonomy.json"
    ):
        """
        Load the taxonomy and precompile regex patterns.

        Each canonical taxonomy term may also contain aliases.

        Example:
        {
            "term": "solar",
            "aliases": [
                "solar panel",
                "solar panels"
            ]
        }

        If an alias matches, the extractor returns the
        canonical term ("solar").
        """

        self.cleaner = TextCleaner()

        with open(taxonomy_path, "r") as f:
            taxonomy = json.load(f)

        self.entity_patterns = {}

        # --------------------------------
        # BUILD TAXONOMY REGEX PATTERNS
        # --------------------------------

        for category, terms in taxonomy.get(
            "categories",
            {}
        ).items():

            self.entity_patterns[category] = []

            for term_obj in terms:

                original_term = term_obj["term"]

                # Canonical term + aliases
                variants = [
                    original_term
                ]

                variants.extend(
                    term_obj.get(
                        "aliases",
                        []
                    )
                )

                compiled_patterns = []

                for variant in variants:

                    # Normalize taxonomy term using
                    # the same cleaner used on remarks.
                    normalized_variant = (
                        self.cleaner.clean_text(
                            variant
                        )
                    )

                    if not normalized_variant:
                        continue

                    pattern = re.compile(
                        r"\b"
                        + re.escape(
                            normalized_variant
                        )
                        + r"\b",
                        re.I
                    )

                    compiled_patterns.append(
                        pattern
                    )

                self.entity_patterns[
                    category
                ].append(
                    (
                        original_term,
                        compiled_patterns
                    )
                )

    # ====================================
    # BEDROOM EXTRACTION
    # ====================================

    def extract_bedrooms(self, text):
        """
        Extract number of bedrooms.

        Examples:
            3 bedroom
            3 bedrooms
            3 bd
            3 beds
            3 br
        """

        patterns = [
            r"(\d+(?:\.\d+)?)\s*bedrooms?",
            r"(\d+(?:\.\d+)?)\s*bd\b",
            r"(\d+(?:\.\d+)?)\s*beds?\b",
            r"(\d+(?:\.\d+)?)\s*br\b"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.I
            )

            if match:

                value = float(
                    match.group(1)
                )

                # Round using the same convention
                # as the comparison dataset.
                return int(
                    math.floor(
                        value + 0.5
                    )
                )

        return None

    # ====================================
    # BATHROOM EXTRACTION
    # ====================================

    def extract_bathrooms(self, text):
        """
        Extract number of bathrooms.

        The comparison dataset rounds decimal
        bathroom counts upward using the project's
        existing rounding convention.

        Examples:
            2 bathroom   -> 2
            2.5 bathroom -> 3
            3.5 bath     -> 4
        """

        patterns = [
            r"(\d+(?:\.\d+)?)\s*bathrooms?",
            r"(\d+(?:\.\d+)?)\s*ba\b",
            r"(\d+(?:\.\d+)?)\s*baths?\b"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.I
            )

            if match:

                value = float(
                    match.group(1)
                )

                return int(
                    math.floor(
                        value + 0.5
                    )
                )

        return None

    # ====================================
    # PRICE EXTRACTION
    # ====================================

    def extract_price(self, text):
        """
        Extract listing price.

        Supports both raw and cleaned text.

        Examples:
            $450000
            $450,000
            Price: $450000
            offered at $725,000
            priced at 450000
            asking 1200000

        TextCleaner also converts:
            450k -> 450000
            1.2m -> 1200000
        """

        # --------------------------------
        # RAW DOLLAR PRICE
        # --------------------------------

        raw_match = re.search(
            r"\$\s*([\d,]{5,})",
            text
        )

        if raw_match:

            value = (
                raw_match
                .group(1)
                .replace(",", "")
            )

            return int(value)

        # --------------------------------
        # CLEAN TEXT
        # --------------------------------

        cleaned_text = (
            self.cleaner.clean_text(
                text
            )
        )

        patterns = [
            (
                r"\b(?:price|priced|offered|listed|asking)"
                r"\s*(?:at|for|of)?\s*"
                r"(\d{5,8})\b"
            ),

            r"\b(\d{5,8})\s+dollars?\b"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                cleaned_text,
                re.I
            )

            if match:

                return int(
                    match.group(1)
                )

        return None

    # ====================================
    # SQUARE FOOTAGE EXTRACTION
    # ====================================

    def extract_sqft(self, text):
        """
        Extract square footage.

        TextCleaner normalizes common forms such as:

            1,850 sqft
                ->
            1850 square feet

        Also supports common uncleaned forms.
        """

        patterns = [
            r"(\d{3,7})\s*square\s+feet\b",
            r"(\d{3,7})\s*sqft\b",
            r"(\d{3,7})\s*sq\.?\s*ft\.?\b",
            r"(\d{3,7})\s*sf\b"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.I
            )

            if match:

                value = (
                    match
                    .group(1)
                    .replace(",", "")
                )

                return int(value)

        return None

    # ====================================
    # TAXONOMY ENTITY EXTRACTION
    # ====================================

    def extract_entities(self, text):
        """
        Match taxonomy concepts across all
        eight categories.

        Aliases return their canonical term.

        Example:

            taxonomy:
                term = "solar"
                alias = "solar panels"

            text:
                "Owned solar panels included"

            result:
                "solar"
        """

        results = {}

        for category, term_patterns in (
            self.entity_patterns.items()
        ):

            matches = []

            for term, patterns in term_patterns:

                # Each canonical term can have
                # multiple regex patterns:
                #
                # canonical term
                # + aliases

                for pattern in patterns:

                    if pattern.search(text):

                        matches.append(
                            term
                        )

                        # Once one variant matches,
                        # don't add the same canonical
                        # term again.
                        break

            # Remove duplicates while
            # preserving order.
            results[category] = list(
                dict.fromkeys(
                    matches
                )
            )

        return results

    # ====================================
    # AMENITY-ONLY EXTRACTION
    # ====================================

    def extract_amenities(self, text):
        """
        Return only taxonomy concepts belonging
        to the amenities category.

        This method remains available for backwards
        compatibility with the earlier project code.
        """

        amenities = []

        for term, patterns in (
            self.entity_patterns.get(
                "amenities",
                []
            )
        ):

            for pattern in patterns:

                if pattern.search(text):

                    amenities.append(
                        term
                    )

                    break

        return list(
            dict.fromkeys(
                amenities
            )
        )

    # ====================================
    # MAIN EXTRACTION METHOD
    # ====================================

    def extract_all(self, text):
        """
        Extract all supported entities from raw text.

        The caller does NOT need to run TextCleaner
        manually before calling this method.

        Returns:
            bedrooms
            bathrooms
            price
            sqft
            amenities
            entities (all 8 taxonomy categories)
        """

        # Handle missing values safely
        if text is None:
            text = ""

        text = str(text)

        # --------------------------------
        # PRICE
        #
        # Use raw text so dollar formatting
        # remains available to extract_price().
        # --------------------------------

        price = self.extract_price(
            text
        )

        # --------------------------------
        # CLEAN TEXT FOR EVERYTHING ELSE
        # --------------------------------

        cleaned_text = (
            self.cleaner.clean_text(
                text
            )
        )

        # --------------------------------
        # TAXONOMY ENTITIES
        # --------------------------------

        entities = self.extract_entities(
            cleaned_text
        )

        # --------------------------------
        # RETURN RESULTS
        # --------------------------------

        return {
            "bedrooms":
                self.extract_bedrooms(
                    cleaned_text
                ),

            "bathrooms":
                self.extract_bathrooms(
                    cleaned_text
                ),

            "price":
                price,

            "sqft":
                self.extract_sqft(
                    cleaned_text
                ),

            "amenities":
                entities.get(
                    "amenities",
                    []
                ),

            "entities":
                entities
        }


# ========================================
# MANUAL TEST
# ========================================

if __name__ == "__main__":

    extractor = EntityExtractor()

    text = """
    Beautiful 3BR / 2.5BA single-family home
    offered at $725,000 with 1,850 sq. ft.
    Features solar panels, recessed lighting,
    quartz countertops, a walk-in closet,
    A/C, RV parking and mountain views.
    """

    result = extractor.extract_all(
        text
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )
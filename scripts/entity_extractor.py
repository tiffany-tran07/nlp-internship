# scripts/entity_extractor.py

import json
import math
import re


class EntityExtractor:
    """
    Extract structured entities and taxonomy concepts from text.

    IMPORTANT:
    This class does NOT clean text.

    The caller is responsible for passing cleaned text when needed.

    extract_all() accepts:
        raw_text:
            Original listing remarks.
            Used mainly for price extraction.

        cleaned_text:
            Text already processed by TextCleaner.
            Used for bedrooms, bathrooms, sqft, and taxonomy matching.

    Example:

        cleaner = TextCleaner()
        extractor = EntityExtractor()

        raw = listing["L_Remarks"]
        cleaned = cleaner.clean_text(raw)

        result = extractor.extract_all(
            raw_text=raw,
            cleaned_text=cleaned
        )
    """

    def __init__(
        self,
        taxonomy_path="data/processed/taxonomy.json",
    ):
        with open(
            taxonomy_path,
            "r",
            encoding="utf-8",
        ) as f:
            taxonomy = json.load(f)

        if "categories" not in taxonomy:
            raise ValueError(
                "taxonomy must contain a 'categories' object"
            )

        self.entity_patterns = {}

        self._build_taxonomy_patterns(
            taxonomy
        )

    # =========================================================
    # NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_taxonomy_term(term):
        """
        Minimal normalization for taxonomy patterns.

        This is NOT general text cleaning.

        It only:
            - converts to lowercase
            - normalizes whitespace

        TextCleaner remains responsible for cleaning remarks.
        """
        return " ".join(
            str(term)
            .strip()
            .lower()
            .split()
        )

    # =========================================================
    # TAXONOMY PATTERNS
    # =========================================================

    def _build_taxonomy_patterns(
        self,
        taxonomy,
    ):
        """
        Build regex patterns from canonical taxonomy terms
        and aliases.

        Alias matches return canonical terms.
        """

        for category, terms in (
            taxonomy.get(
                "categories",
                {}
            ).items()
        ):
            self.entity_patterns[
                category
            ] = []

            for term_obj in terms:

                if not isinstance(
                    term_obj,
                    dict,
                ):
                    continue

                original_term = (
                    term_obj.get(
                        "term"
                    )
                )

                if not isinstance(
                    original_term,
                    str,
                ):
                    continue

                canonical = (
                    self._normalize_taxonomy_term(
                        original_term
                    )
                )

                if not canonical:
                    continue

                variants = [
                    original_term
                ]

                aliases = (
                    term_obj.get(
                        "aliases",
                        []
                    )
                )

                if isinstance(
                    aliases,
                    list,
                ):
                    variants.extend(
                        aliases
                    )

                compiled_patterns = []

                for variant in variants:

                    if not isinstance(
                        variant,
                        str,
                    ):
                        continue

                    normalized_variant = (
                        self._normalize_taxonomy_term(
                            variant
                        )
                    )

                    if not normalized_variant:
                        continue

                    # Treat spaces and hyphens similarly.
                    parts = re.split(
                        r"[\s\-]+",
                        normalized_variant,
                    )

                    escaped_parts = [
                        re.escape(part)
                        for part in parts
                        if part
                    ]

                    if not escaped_parts:
                        continue

                    flexible_variant = (
                        r"[\s\-]+".join(
                            escaped_parts
                        )
                    )

                    pattern = re.compile(
                        rf"(?<!\w)"
                        rf"{flexible_variant}"
                        rf"(?!\w)",
                        re.IGNORECASE,
                    )

                    compiled_patterns.append(
                        pattern
                    )

                if compiled_patterns:

                    self.entity_patterns[
                        category
                    ].append(
                        (
                            canonical,
                            compiled_patterns,
                        )
                    )

    # =========================================================
    # BEDROOM EXTRACTION
    # =========================================================

    def extract_bedrooms(
        self,
        text,
    ):
        """
        Extract bedroom count from CLEANED text.

        Examples after TextCleaner:
            3 bedroom
            4 bedroom
        """

        if not text:
            return None

        text = str(text)

        patterns = [
            r"\b(\d+(?:\.\d+)?)\s*bedroom\b",
            r"\b(\d+(?:\.\d+)?)\s*bedrooms\b",

            # Keep these for robustness if caller supplies
            # only partially cleaned text.
            r"\b(\d+(?:\.\d+)?)\s*bd\b",
            r"\b(\d+(?:\.\d+)?)\s*beds?\b",
            r"\b(\d+(?:\.\d+)?)\s*br\b",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
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

    # =========================================================
    # BATHROOM EXTRACTION
    # =========================================================

    def extract_bathrooms(
        self,
        text,
    ):
        """
        Extract bathroom count.

        Uses the project's existing rounding convention:

            2.0 -> 2
            2.5 -> 3
            3.5 -> 4
        """

        if not text:
            return None

        text = str(text)

        patterns = [
            r"\b(\d+(?:\.\d+)?)\s*bathroom\b",
            r"\b(\d+(?:\.\d+)?)\s*bathrooms\b",

            # Robustness for partially cleaned text.
            r"\b(\d+(?:\.\d+)?)\s*ba\b",
            r"\b(\d+(?:\.\d+)?)\s*baths?\b",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
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

    # =========================================================
    # PRICE EXTRACTION
    # =========================================================

    def extract_price(
        self,
        raw_text,
        cleaned_text=None,
    ):
        """
        Extract listing price.

        raw_text is checked first because it preserves:
            $725,000
            $450000

        cleaned_text may contain values normalized by TextCleaner:
            450k -> 450000
            1.2m -> 1200000
        """

        if raw_text is None:
            raw_text = ""

        raw_text = str(
            raw_text
        )

        # -----------------------------------------------------
        # RAW $ PRICE
        # -----------------------------------------------------

        raw_match = re.search(
            r"\$\s*([\d,]{5,})",
            raw_text,
        )

        if raw_match:

            value = (
                raw_match
                .group(1)
                .replace(
                    ",",
                    "",
                )
            )

            return int(
                value
            )

        # -----------------------------------------------------
        # CLEANED / NORMALIZED PRICE
        # -----------------------------------------------------

        if cleaned_text is None:
            cleaned_text = raw_text

        cleaned_text = str(
            cleaned_text
        )

        patterns = [
            (
                r"\b(?:price|priced|offered|listed|asking)"
                r"\s*(?:at|for|of)?\s*"
                r"(\d{5,9})\b"
            ),

            (
                r"\b(\d{5,9})"
                r"\s+dollars?\b"
            ),
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                cleaned_text,
                re.IGNORECASE,
            )

            if match:

                return int(
                    match.group(1)
                )

        return None

    # =========================================================
    # SQUARE FOOTAGE
    # =========================================================

    def extract_sqft(
        self,
        text,
    ):
        """
        Extract square footage.

        TextCleaner normally converts:
            1,850 sqft
        into:
            1850 square feet
        """

        if not text:
            return None

        text = str(
            text
        )

        patterns = [
            r"\b(\d{3,7})\s*square\s+feet\b",

            # Robustness for uncleaned/partially-cleaned text.
            r"\b([\d,]{3,9})\s*sqft\b",
            r"\b([\d,]{3,9})\s*sq\.?\s*ft\.?\b",
            r"\b([\d,]{3,9})\s*sf\b",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if match:

                value = (
                    match.group(1)
                    .replace(
                        ",",
                        "",
                    )
                )

                return int(
                    value
                )

        return None

    # =========================================================
    # TAXONOMY ENTITY EXTRACTION
    # =========================================================

    def extract_entities(
        self,
        text,
    ):
        """
        Match taxonomy concepts across all categories.

        This method expects text that has already been cleaned
        by TextCleaner.

        Aliases return their canonical taxonomy term.
        """

        if not text:
            text = ""

        text = str(
            text
        )

        results = {}

        for category, term_patterns in (
            self.entity_patterns.items()
        ):

            matches = []

            for canonical, patterns in (
                term_patterns
            ):

                for pattern in patterns:

                    if pattern.search(
                        text
                    ):

                        matches.append(
                            canonical
                        )

                        # Don't add same canonical
                        # term twice because of aliases.
                        break

            results[
                category
            ] = list(
                dict.fromkeys(
                    matches
                )
            )

        return results

    # =========================================================
    # AMENITIES
    # =========================================================

    def extract_amenities(
        self,
        text,
    ):
        """
        Return only taxonomy terms from the amenities category.

        Kept for compatibility with previous code.
        """

        if not text:
            return []

        amenities = []

        for canonical, patterns in (
            self.entity_patterns.get(
                "amenities",
                [],
            )
        ):

            for pattern in patterns:

                if pattern.search(
                    text
                ):

                    amenities.append(
                        canonical
                    )

                    break

        return list(
            dict.fromkeys(
                amenities
            )
        )

    # =========================================================
    # MAIN EXTRACTION
    # =========================================================

    def extract_all(
        self,
        raw_text,
        cleaned_text=None,
    ):
        """
        Extract all supported entities.

        EntityExtractor does NOT clean text.

        Preferred usage:

            raw = listing["L_Remarks"]
            cleaned = cleaner.clean_text(raw)

            result = extractor.extract_all(
                raw_text=raw,
                cleaned_text=cleaned
            )

        If cleaned_text is omitted, raw_text is used for both.
        This preserves backwards compatibility, but callers
        should normally provide cleaned_text.
        """

        if raw_text is None:
            raw_text = ""

        raw_text = str(
            raw_text
        )

        if cleaned_text is None:
            cleaned_text = raw_text

        cleaned_text = str(
            cleaned_text
        )

        # -----------------------------------------------------
        # PRICE
        # -----------------------------------------------------

        price = self.extract_price(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
        )

        # -----------------------------------------------------
        # TAXONOMY
        # -----------------------------------------------------

        entities = (
            self.extract_entities(
                cleaned_text
            )
        )

        # -----------------------------------------------------
        # OUTPUT
        # -----------------------------------------------------

        return {
            "bedrooms": (
                self.extract_bedrooms(
                    cleaned_text
                )
            ),

            "bathrooms": (
                self.extract_bathrooms(
                    cleaned_text
                )
            ),

            "price": price,

            "sqft": (
                self.extract_sqft(
                    cleaned_text
                )
            ),

            "amenities": (
                entities.get(
                    "amenities",
                    [],
                )
            ),

            "entities": entities,
        }


# =============================================================
# MANUAL TEST
# =============================================================

if __name__ == "__main__":

    from scripts.text_cleaning import TextCleaner

    cleaner = TextCleaner()

    extractor = EntityExtractor()

    raw_text = """
    Beautiful 3BR / 2.5BA single-family home
    offered at $725,000 with 1,850 sq. ft.
    Features solar panels, recessed lighting,
    quartz countertops, a walk-in closet,
    A/C, RV parking and mountain views.
    """

    cleaned_text = (
        cleaner.clean_text(
            raw_text
        )
    )

    result = extractor.extract_all(
        raw_text=raw_text,
        cleaned_text=cleaned_text,
    )

    print(
        "RAW:"
    )

    print(
        raw_text
    )

    print(
        "\nCLEANED:"
    )

    print(
        cleaned_text
    )

    print(
        "\nENTITIES:"
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )
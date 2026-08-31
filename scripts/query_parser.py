# scripts/query_parser.py

import json
import math
import re
import pandas as pd


class QueryParser:
    """
    Parse natural-language real-estate queries into structured filters
    and convert those filters into parameterized SQL.
    """

    MAX_PRICE = 100_000_000
    MAX_BEDROOMS = 20
    MAX_BATHROOMS = 20

    def __init__(
        self,
        listings_path="data/raw/all_listings.csv",
        taxonomy_path="data/processed/taxonomy.json",
        valid_cities=None,
        valid_amenities=None,
    ):
        # Allow tests to inject values, but load real project data by default.
        if valid_cities is None:
            self.valid_cities = self._load_cities(listings_path)
        else:
            self.valid_cities = {
                self._normalize_text(city): str(city).strip()
                for city in valid_cities
                if str(city).strip()
            }

        if valid_amenities is None:
            (
                self.taxonomy_terms,
                self.term_to_category,
            ) = self._load_taxonomy_terms(taxonomy_path)
        else:
            self.taxonomy_terms = {
                self._normalize_text(term):
                self._normalize_text(term)
                for term in valid_amenities
                if str(term).strip()
            }

            self.term_to_category = {}

    # =================================================
    # LOADING
    # =================================================

    def _load_cities(self, listings_path):
        """
        Load every city from the full raw dataset.

        Dictionary format:
            {
                "san francisco": "San Francisco",
                "irvine": "Irvine",
                ...
            }
        """
        df = pd.read_csv(listings_path)

        if "L_City" not in df.columns:
            raise ValueError(
                f"'L_City' column not found in {listings_path}"
            )

        cities = {}

        for city in df["L_City"].dropna().unique():
            original = str(city).strip()

            if not original:
                continue

            cities[self._normalize_text(original)] = original

        return cities

    def _load_taxonomy_terms(self, taxonomy_path):
        """
        Load taxonomy canonical terms and aliases.

        Alias -> canonical term mapping is used so different natural
        language forms produce consistent filters.

        Example:
            "pets allowed" -> "pet friendly"
            "central air" -> "air conditioning"
            "three car garage" -> "3-car garage"
        """
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            taxonomy = json.load(f)

        if "categories" not in taxonomy:
            raise ValueError(
                "taxonomy.json must contain a 'categories' object"
            )

        term_lookup = {}
        category_lookup = {}

        for category, entries in taxonomy["categories"].items():

            if not isinstance(entries, list):
                continue

            for entry in entries:

                if not isinstance(entry, dict):
                    continue

                term = entry.get("term")

                if not isinstance(term, str):
                    continue

                canonical = self._normalize_text(term)

                if not canonical:
                    continue

                term_lookup[canonical] = canonical
                category_lookup[canonical] = category

                for alias in entry.get("aliases", []):

                    if not isinstance(alias, str):
                        continue

                    normalized_alias = self._normalize_text(alias)

                    if not normalized_alias:
                        continue

                    term_lookup[normalized_alias] = canonical
                    category_lookup[normalized_alias] = category

        return term_lookup, category_lookup

    # =================================================
    # NORMALIZATION
    # =================================================

    @staticmethod
    def _normalize_text(value):
        """
        Lowercase and normalize internal whitespace.
        """
        return " ".join(
            str(value).strip().lower().split()
        )

    @staticmethod
    def _parse_number(digits, letter=""):
        """
        Convert:
            700k -> 700000
            1.2m -> 1200000
            500,000 -> 500000
        """
        value = float(
            digits.replace(",", "")
        )

        letter = letter.lower()

        if letter == "k":
            value *= 1_000

        elif letter == "m":
            value *= 1_000_000

        return (
            int(value)
            if value.is_integer()
            else value
        )

    # =================================================
    # BASIC VALIDATION
    # =================================================

    def _validate_price(self, value):

        if not isinstance(value, (int, float)):
            raise ValueError(
                "Price must be numeric."
            )

        if isinstance(value, bool) or not math.isfinite(value):
            raise ValueError(
                "Price must be a finite number."
            )

        if value < 0:
            raise ValueError(
                "Price cannot be negative."
            )

        if value > self.MAX_PRICE:
            raise ValueError(
                f"Price exceeds allowed maximum "
                f"of {self.MAX_PRICE}."
            )

        return value

    def _validate_bedrooms(self, value):

        if value < 0 or value > self.MAX_BEDROOMS:
            raise ValueError(
                f"Bedrooms must be between 0 "
                f"and {self.MAX_BEDROOMS}."
            )

        return value

    def _validate_bathrooms(self, value):

        if value < 0 or value > self.MAX_BATHROOMS:
            raise ValueError(
                f"Bathrooms must be between 0 "
                f"and {self.MAX_BATHROOMS}."
            )

        return value

    # =================================================
    # PRICE
    # =================================================

    def _extract_prices(self, query, filters):
        """
        Extract prices only when the number has clear price context.

        This avoids false matches such as:

            at least 3 bedrooms
            up to 4 bedrooms
            no more than 2 baths

        A price must normally have $, k, or m.
        """

        # ---------------------------------------------
        # BETWEEN PRICE RANGE
        # ---------------------------------------------

        match = re.search(
            r"\bbetween\s+"
            r"\$?([\d,]+(?:\.\d+)?)\s*([km])?"
            r"\s+(?:and|to)\s+"
            r"\$?([\d,]+(?:\.\d+)?)\s*([km])?"
            r"\b",
            query,
            re.I,
        )

        if match:

            low_digits = match.group(1)
            low_suffix = match.group(2) or ""

            high_digits = match.group(3)
            high_suffix = match.group(4) or ""

            # Require clear price context.
            full_match = match.group(0)

            has_price_context = (
                "$" in full_match
                or low_suffix
                or high_suffix
                or re.search(
                    r"\b(?:price|budget|dollars?)\b",
                    full_match,
                    re.I,
                )
            )

            if has_price_context:

                low = self._validate_price(
                    self._parse_number(
                        low_digits,
                        low_suffix,
                    )
                )

                high = self._validate_price(
                    self._parse_number(
                        high_digits,
                        high_suffix,
                    )
                )

                if low > high:
                    raise ValueError(
                        "Minimum price cannot exceed "
                        "maximum price."
                    )

                filters["price_min"] = low
                filters["price_max"] = high

        # ---------------------------------------------
        # MAXIMUM PRICE
        # ---------------------------------------------

        price_max_patterns = [
            # under $700000
            (
                r"\b(?:under|below|less than|up to|max(?:imum)?)"
                r"\s+\$"
                r"([\d,]+(?:\.\d+)?)\s*([km]?)\b"
            ),

            # under 700k / below 1.2m
            (
                r"\b(?:under|below|less than|up to|max(?:imum)?)"
                r"\s+"
                r"([\d,]+(?:\.\d+)?)\s*([km])\b"
            ),

            # budget under 700000
            (
                r"\b(?:budget|price)"
                r"(?:\s+is)?\s+"
                r"(?:under|below|less than|up to|max(?:imum)?)"
                r"\s+\$?"
                r"([\d,]+(?:\.\d+)?)\s*([km]?)\b"
            ),
        ]

        for pattern in price_max_patterns:

            match = re.search(
                pattern,
                query,
                re.I,
            )

            if not match:
                continue

            value = self._parse_number(
                match.group(1),
                match.group(2) or "",
            )

            filters["price_max"] = (
                self._validate_price(value)
            )

            break

        # ---------------------------------------------
        # MINIMUM PRICE
        # ---------------------------------------------

        price_min_patterns = [
            # over $700000
            (
                r"\b(?:over|above|more than|at least|min(?:imum)?)"
                r"\s+\$"
                r"([\d,]+(?:\.\d+)?)\s*([km]?)\b"
            ),

            # over 700k / above 1m
            (
                r"\b(?:over|above|more than|at least|min(?:imum)?)"
                r"\s+"
                r"([\d,]+(?:\.\d+)?)\s*([km])\b"
            ),

            # price above 700000
            (
                r"\b(?:budget|price)"
                r"(?:\s+is)?\s+"
                r"(?:over|above|more than|at least|min(?:imum)?)"
                r"\s+\$?"
                r"([\d,]+(?:\.\d+)?)\s*([km]?)\b"
            ),
        ]

        for pattern in price_min_patterns:

            match = re.search(
                pattern,
                query,
                re.I,
            )

            if not match:
                continue

            value = self._parse_number(
                match.group(1),
                match.group(2) or "",
            )

            filters["price_min"] = (
                self._validate_price(value)
            )

            break

    # =================================================
    # BEDROOMS
    # =================================================

    def _extract_bedrooms(self, query, filters):

        # 3+ bedrooms
        match = re.search(
            r"\b(\d+)\s*\+\s*"
            r"(?:bed|beds|bedroom|bedrooms|br)\b",
            query,
            re.I,
        )

        if match:

            filters["bedrooms_min"] = (
                self._validate_bedrooms(
                    int(match.group(1))
                )
            )

            return

        # at least 3 bedrooms
        match = re.search(
            r"\b(?:at least|minimum|min)\s+"
            r"(\d+)\s*"
            r"(?:bed|beds|bedroom|bedrooms|br)\b",
            query,
            re.I,
        )

        if match:

            filters["bedrooms_min"] = (
                self._validate_bedrooms(
                    int(match.group(1))
                )
            )

            return

        # up to / max / no more than 4 bedrooms
        match = re.search(
            r"\b(?:up to|max(?:imum)?|no more than)\s+"
            r"(\d+)\s*"
            r"(?:bed|beds|bedroom|bedrooms|br)\b",
            query,
            re.I,
        )

        if match:

            filters["bedrooms_max"] = (
                self._validate_bedrooms(
                    int(match.group(1))
                )
            )

            return

        # exactly 3 bedrooms
        match = re.search(
            r"\b(?:exactly\s+)?"
            r"(\d+)\s*"
            r"(?:bed|beds|bedroom|bedrooms|br)\b",
            query,
            re.I,
        )

        if match:

            filters["bedrooms"] = (
                self._validate_bedrooms(
                    int(match.group(1))
                )
            )

    # =================================================
    # BATHROOMS
    # =================================================

    def _extract_bathrooms(self, query, filters):

        number = r"\d+(?:\.\d+)?"

        # 2+ baths
        match = re.search(
            rf"\b({number})\s*\+\s*"
            r"(?:bath|baths|bathroom|bathrooms|ba)\b",
            query,
            re.I,
        )

        if match:

            filters["bathrooms_min"] = (
                self._validate_bathrooms(
                    float(match.group(1))
                )
            )

            return

        # at least 2 baths
        match = re.search(
            rf"\b(?:at least|minimum|min)\s+"
            rf"({number})\s*"
            r"(?:bath|baths|bathroom|bathrooms|ba)\b",
            query,
            re.I,
        )

        if match:

            filters["bathrooms_min"] = (
                self._validate_bathrooms(
                    float(match.group(1))
                )
            )

            return

        # max / up to / no more than 2 baths
        match = re.search(
            rf"\b(?:up to|max(?:imum)?|no more than)\s+"
            rf"({number})\s*"
            r"(?:bath|baths|bathroom|bathrooms|ba)\b",
            query,
            re.I,
        )

        if match:

            filters["bathrooms_max"] = (
                self._validate_bathrooms(
                    float(match.group(1))
                )
            )

            return

        # exactly 2 baths
        match = re.search(
            rf"\b(?:exactly\s+)?"
            rf"({number})\s*"
            r"(?:bath|baths|bathroom|bathrooms|ba)\b",
            query,
            re.I,
        )

        if match:

            filters["bathrooms"] = (
                self._validate_bathrooms(
                    float(match.group(1))
                )
            )

    # =================================================
    # CITY
    # =================================================

    def _extract_city(self, query, filters):
        """
        Match against actual database cities rather than capturing
        arbitrary text after the word "in".

        Longest city names are checked first.
        """

        if not self.valid_cities:
            return

        cities = sorted(
            self.valid_cities.keys(),
            key=len,
            reverse=True,
        )

        for normalized_city in cities:

            pattern = (
                r"\b(?:in|around|within)\s+"
                + re.escape(normalized_city)
                + r"\b"
            )

            if re.search(
                pattern,
                query,
                re.I,
            ):

                filters["city"] = (
                    self.valid_cities[
                        normalized_city
                    ]
                )

                return

    # =================================================
    # TAXONOMY / AMENITIES
    # =================================================

    def _is_negated(
        self,
        query,
        phrase,
        match_start=None,
    ):
        """
        Recognize common negative expressions.

        Examples:
            no pool
            without pool
            not garage
            don't want a pool
            do not need a gym
            avoid solar panels
        """

        escaped = re.escape(phrase)

        patterns = [
            rf"\bno\s+(?:a\s+|an\s+)?{escaped}\b",
            rf"\bwithout\s+(?:a\s+|an\s+)?{escaped}\b",
            rf"\bexclude\s+(?:a\s+|an\s+)?{escaped}\b",
            rf"\bexcluding\s+(?:a\s+|an\s+)?{escaped}\b",
            rf"\bnot\s+(?:a\s+|an\s+)?{escaped}\b",
            rf"\bdon['’]?t\s+(?:want|need|like)\s+"
            rf"(?:a\s+|an\s+)?{escaped}\b",
            rf"\bdo\s+not\s+(?:want|need|like)\s+"
            rf"(?:a\s+|an\s+)?{escaped}\b",
            rf"\bavoid\s+(?:a\s+|an\s+)?{escaped}\b",
        ]

        return any(
            re.search(
                pattern,
                query,
                re.I,
            )
            for pattern in patterns
        )

    def _extract_amenities(self, query, filters):
        """
        Extract taxonomy terms and aliases.

        Longest phrases are processed first so a phrase like
        "community pool" does not also automatically produce "pool".
        """

        required = []
        excluded = []
        matched_spans = []

        phrases = sorted(
            self.taxonomy_terms.keys(),
            key=len,
            reverse=True,
        )

        for phrase in phrases:

            escaped = re.escape(phrase)

            pattern = (
                r"(?<!\w)"
                + escaped
                + r"(?!\w)"
            )

            matches = list(
                re.finditer(
                    pattern,
                    query,
                    re.I,
                )
            )

            for match in matches:

                span = match.span()

                # Skip if this match overlaps a longer taxonomy
                # phrase already accepted.
                overlaps = any(
                    span[0] < old_end
                    and span[1] > old_start
                    for old_start, old_end in matched_spans
                )

                if overlaps:
                    continue

                canonical = (
                    self.taxonomy_terms[phrase]
                )

                if self._is_negated(
                    query,
                    phrase,
                    match.start(),
                ):
                    excluded.append(
                        canonical
                    )
                else:
                    required.append(
                        canonical
                    )

                matched_spans.append(
                    span
                )

        required = sorted(
            set(required)
            - set(excluded)
        )

        excluded = sorted(
            set(excluded)
        )

        if required:
            filters["amenities"] = required

        if excluded:
            filters["exclude_amenities"] = excluded

    # =================================================
    # CONFLICT VALIDATION
    # =================================================

    def _validate_filter_conflicts(self, filters):

        if (
            "price_min" in filters
            and "price_max" in filters
            and filters["price_min"] > filters["price_max"]
        ):
            raise ValueError(
                "Minimum price cannot exceed maximum price."
            )

        if (
            "bedrooms_min" in filters
            and "bedrooms_max" in filters
            and filters["bedrooms_min"]
            > filters["bedrooms_max"]
        ):
            raise ValueError(
                "Minimum bedrooms cannot exceed "
                "maximum bedrooms."
            )

        if (
            "bathrooms_min" in filters
            and "bathrooms_max" in filters
            and filters["bathrooms_min"]
            > filters["bathrooms_max"]
        ):
            raise ValueError(
                "Minimum bathrooms cannot exceed "
                "maximum bathrooms."
            )

    # =================================================
    # MAIN PARSER
    # =================================================

    def parse(self, query):

        if not isinstance(query, str):
            raise TypeError(
                "Query must be a string."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        filters = {}

        self._extract_prices(
            query,
            filters,
        )

        self._extract_bedrooms(
            query,
            filters,
        )

        self._extract_bathrooms(
            query,
            filters,
        )

        self._extract_city(
            query,
            filters,
        )

        self._extract_amenities(
            query,
            filters,
        )

        self._validate_filter_conflicts(
            filters
        )

        return filters

    # =================================================
    # PARAMETERIZED SQL
    # =================================================

    def to_sql(self, filters):

        if not isinstance(filters, dict):
            raise TypeError(
                "filters must be a dictionary."
            )

        conditions = []
        params = []

        # ---------------------------------------------
        # PRICE
        # ---------------------------------------------

        if "price_max" in filters:

            conditions.append(
                "L_SystemPrice <= %s"
            )

            params.append(
                filters["price_max"]
            )

        if "price_min" in filters:

            conditions.append(
                "L_SystemPrice >= %s"
            )

            params.append(
                filters["price_min"]
            )

        # ---------------------------------------------
        # BEDROOMS
        # ---------------------------------------------

        if "bedrooms" in filters:

            conditions.append(
                "L_Keyword2 = %s"
            )

            params.append(
                filters["bedrooms"]
            )

        if "bedrooms_min" in filters:

            conditions.append(
                "L_Keyword2 >= %s"
            )

            params.append(
                filters["bedrooms_min"]
            )

        if "bedrooms_max" in filters:

            conditions.append(
                "L_Keyword2 <= %s"
            )

            params.append(
                filters["bedrooms_max"]
            )

        # ---------------------------------------------
        # BATHROOMS
        # ---------------------------------------------

        if "bathrooms" in filters:

            conditions.append(
                "L_Keyword3 = %s"
            )

            params.append(
                filters["bathrooms"]
            )

        if "bathrooms_min" in filters:

            conditions.append(
                "L_Keyword3 >= %s"
            )

            params.append(
                filters["bathrooms_min"]
            )

        if "bathrooms_max" in filters:

            conditions.append(
                "L_Keyword3 <= %s"
            )

            params.append(
                filters["bathrooms_max"]
            )

        # ---------------------------------------------
        # CITY
        # ---------------------------------------------

        if "city" in filters:

            conditions.append(
                "L_City = %s"
            )

            params.append(
                filters["city"]
            )

        # ---------------------------------------------
        # REQUIRED TAXONOMY TERMS
        # ---------------------------------------------

        for amenity in filters.get(
            "amenities",
            [],
        ):

            conditions.append(
                "LOWER(L_Remarks) LIKE %s"
            )

            params.append(
                f"%{amenity.lower()}%"
            )

        # ---------------------------------------------
        # EXCLUDED TAXONOMY TERMS
        # ---------------------------------------------

        for amenity in filters.get(
            "exclude_amenities",
            [],
        ):

            conditions.append(
                "LOWER(L_Remarks) NOT LIKE %s"
            )

            params.append(
                f"%{amenity.lower()}%"
            )

        where_clause = (
            " AND ".join(conditions)
            if conditions
            else "1=1"
        )

        sql = (
            "SELECT * "
            "FROM rets_property "
            f"WHERE {where_clause}"
        )

        return sql, params


# =====================================================
# MANUAL TESTING
# =====================================================

if __name__ == "__main__":

    parser = QueryParser()

    test_queries = [
        "3 bed 2 bath under 700k in Irvine with pool and garage",
        "4 bed 3 bath over 600k in Sacramento with solar panels",
        "1 bed in San Francisco near transit",
        "4+ bed under 900k in Fremont",
        "between 500k and 850k in Irvine",
        "at least 3 bed and 2+ bath in San Diego",
        "3 bed with pool but no garage",
        "under 1.2m in Los Angeles without pool",
        "at least 3 bedrooms in Irvine",
        "up to 4 bedrooms in Sacramento",
        "no more than 2 baths in San Diego",
        "3 bed in Irvine pet friendly",
        "3 bed in Irvine pets allowed",
        "2 bed in Los Angeles don't want a pool",
        "4 bed in San Diego not garage",
        "2 bed in Irvine with central air",
        "3 bed in Irvine with three car garage",
        "3 bed in Irvine near the beach",
        "new construction in Irvine with home office",
    ]

    for query in test_queries:

        try:

            filters = parser.parse(
                query
            )

            sql, params = parser.to_sql(
                filters
            )

            print(
                "=" * 80
            )

            print(
                "QUERY:",
                query,
            )

            print(
                "FILTERS:",
                filters,
            )

            print(
                "SQL:",
                sql,
            )

            print(
                "PARAMS:",
                params,
            )

        except (
            ValueError,
            TypeError,
        ) as error:

            print(
                "=" * 80
            )

            print(
                "QUERY:",
                query,
            )

            print(
                "ERROR:",
                error,
            )
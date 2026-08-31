import json
import math
import pandas as pd


class SchemaValidator:
    """
    Validates structured filters produced by QueryParser.
    """

    ALLOWED_FILTERS = {
        "city",
        "price_min",
        "price_max",
        "bedrooms",
        "bedrooms_min",
        "bedrooms_max",
        "bathrooms",
        "bathrooms_min",
        "bathrooms_max",
        "amenities",
        "exclude_amenities",
    }

    MIN_PRICE = 0
    MAX_PRICE = 100_000_000

    MIN_BEDROOMS = 0
    MAX_BEDROOMS = 20

    MIN_BATHROOMS = 0
    MAX_BATHROOMS = 20

    def __init__(
        self,
        listings_path="data/raw/all_listings.csv",
        taxonomy_path="data/processed/taxonomy.json",
    ):
        self.valid_cities = self._load_valid_cities(listings_path)
        self.taxonomy = self._load_taxonomy(taxonomy_path)

        self.valid_taxonomy_terms = self._load_valid_taxonomy_terms()
        self.term_to_category = self._build_term_to_category()

    # -------------------------------------------------
    # DATA LOADING
    # -------------------------------------------------

    def _load_valid_cities(self, listings_path):
        """
        Load cities from the full raw listing dataset.

        Cities are stored lowercase for case-insensitive validation.
        """
        df = pd.read_csv(listings_path)

        if "L_City" not in df.columns:
            raise ValueError(
                f"'L_City' column not found in {listings_path}"
            )

        return {
            self._normalize_text(city)
            for city in df["L_City"].dropna()
            if str(city).strip()
        }

    def _load_taxonomy(self, taxonomy_path):
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            taxonomy = json.load(f)

        if not isinstance(taxonomy, dict):
            raise ValueError(
                "taxonomy.json must contain a JSON object"
            )

        if "categories" not in taxonomy:
            raise ValueError(
                "taxonomy.json must contain a 'categories' object"
            )

        if not isinstance(taxonomy["categories"], dict):
            raise ValueError(
                "'categories' in taxonomy.json must be an object"
            )

        return taxonomy

    # -------------------------------------------------
    # NORMALIZATION
    # -------------------------------------------------

    @staticmethod
    def _normalize_text(value):
        """
        Normalize text for case-insensitive comparisons.
        """
        return " ".join(
            str(value).strip().lower().split()
        )

    # -------------------------------------------------
    # TAXONOMY
    # -------------------------------------------------

    def _load_valid_taxonomy_terms(self):
        """
        Load valid canonical taxonomy terms and aliases.

        Do NOT recursively flatten the JSON because IDs, counts,
        metadata, etc. are not valid search terms.
        """
        valid_terms = set()

        for entries in self.taxonomy["categories"].values():

            if not isinstance(entries, list):
                continue

            for entry in entries:

                if not isinstance(entry, dict):
                    continue

                # Canonical term
                term = entry.get("term")

                if isinstance(term, str) and term.strip():
                    valid_terms.add(
                        self._normalize_text(term)
                    )

                # Aliases
                aliases = entry.get("aliases", [])

                if isinstance(aliases, list):
                    for alias in aliases:

                        if isinstance(alias, str) and alias.strip():
                            valid_terms.add(
                                self._normalize_text(alias)
                            )

        return valid_terms

    def _build_term_to_category(self):
        """
        Map each canonical term and alias to its taxonomy category.

        Examples:
            pool -> amenities
            garage -> exterior
            near beach -> location
            home office -> interior
        """
        lookup = {}

        for category, entries in self.taxonomy["categories"].items():

            if not isinstance(entries, list):
                continue

            for entry in entries:

                if not isinstance(entry, dict):
                    continue

                term = entry.get("term")

                if isinstance(term, str) and term.strip():
                    lookup[
                        self._normalize_text(term)
                    ] = category

                aliases = entry.get("aliases", [])

                if isinstance(aliases, list):
                    for alias in aliases:

                        if isinstance(alias, str) and alias.strip():
                            lookup[
                                self._normalize_text(alias)
                            ] = category

        return lookup

    def get_taxonomy_category(self, term):
        """
        Return the category for a taxonomy term or alias.
        """
        if not isinstance(term, str):
            return None

        return self.term_to_category.get(
            self._normalize_text(term)
        )

    # -------------------------------------------------
    # NUMERIC VALIDATION
    # -------------------------------------------------

    @staticmethod
    def _is_number(value):
        """
        bool is rejected even though bool subclasses int.
        """
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    def _validate_numeric_filter(
        self,
        filters,
        key,
        minimum,
        maximum,
        label,
        errors,
    ):
        if key not in filters:
            return

        value = filters[key]

        if not self._is_number(value):
            errors.append(
                f"{key} must be a number, "
                f"got {type(value).__name__}"
            )
            return

        if value < minimum or value > maximum:
            errors.append(
                f"{label} {value} must be between "
                f"{minimum} and {maximum}"
            )

    def _validate_range(
        self,
        filters,
        min_key,
        max_key,
        label,
        errors,
    ):
        if min_key not in filters or max_key not in filters:
            return

        minimum = filters[min_key]
        maximum = filters[max_key]

        if (
            not self._is_number(minimum)
            or not self._is_number(maximum)
        ):
            return

        if minimum > maximum:
            errors.append(
                f"{label} minimum ({minimum}) cannot be greater "
                f"than {label} maximum ({maximum})"
            )

    # -------------------------------------------------
    # TAXONOMY FILTER VALIDATION
    # -------------------------------------------------

    def _validate_taxonomy_list(
        self,
        filters,
        key,
        errors,
    ):
        if key not in filters:
            return

        values = filters[key]

        if not isinstance(values, (list, tuple, set)):
            errors.append(
                f"{key} must be a list of taxonomy terms"
            )
            return

        for value in values:

            if not isinstance(value, str):
                errors.append(
                    f"Each value in {key} must be a string"
                )
                continue

            normalized = self._normalize_text(value)

            if not normalized:
                errors.append(
                    f"{key} cannot contain an empty value"
                )
                continue

            if normalized not in self.valid_taxonomy_terms:
                errors.append(
                    f"Taxonomy term '{value}' is not recognized"
                )

    # -------------------------------------------------
    # MAIN VALIDATOR
    # -------------------------------------------------

    def validate_query(self, filters):
        errors = []

        if not isinstance(filters, dict):
            return False, [
                "Filters must be provided as a dictionary"
            ]

        # ---------------------------------------------
        # Unknown filter keys
        # ---------------------------------------------

        for key in filters:

            if key not in self.ALLOWED_FILTERS:
                errors.append(
                    f"Filter '{key}' is not recognized"
                )

        # ---------------------------------------------
        # City
        # ---------------------------------------------

        if "city" in filters:

            city = filters["city"]

            if not isinstance(city, str):
                errors.append(
                    "city must be a string"
                )

            elif not city.strip():
                errors.append(
                    "city cannot be empty"
                )

            elif (
                self._normalize_text(city)
                not in self.valid_cities
            ):
                errors.append(
                    f"City '{city}' not found in database"
                )

        # ---------------------------------------------
        # Price
        # ---------------------------------------------

        self._validate_numeric_filter(
            filters,
            "price_min",
            self.MIN_PRICE,
            self.MAX_PRICE,
            "Price",
            errors,
        )

        self._validate_numeric_filter(
            filters,
            "price_max",
            self.MIN_PRICE,
            self.MAX_PRICE,
            "Price",
            errors,
        )

        self._validate_range(
            filters,
            "price_min",
            "price_max",
            "Price",
            errors,
        )

        # ---------------------------------------------
        # Bedrooms
        # ---------------------------------------------

        for key in (
            "bedrooms",
            "bedrooms_min",
            "bedrooms_max",
        ):
            self._validate_numeric_filter(
                filters,
                key,
                self.MIN_BEDROOMS,
                self.MAX_BEDROOMS,
                "Bedroom count",
                errors,
            )

        self._validate_range(
            filters,
            "bedrooms_min",
            "bedrooms_max",
            "Bedroom",
            errors,
        )

        # ---------------------------------------------
        # Bathrooms
        # ---------------------------------------------

        for key in (
            "bathrooms",
            "bathrooms_min",
            "bathrooms_max",
        ):
            self._validate_numeric_filter(
                filters,
                key,
                self.MIN_BATHROOMS,
                self.MAX_BATHROOMS,
                "Bathroom count",
                errors,
            )

        self._validate_range(
            filters,
            "bathrooms_min",
            "bathrooms_max",
            "Bathroom",
            errors,
        )

        # ---------------------------------------------
        # Exact bedroom conflicts
        # ---------------------------------------------

        if (
            "bedrooms" in filters
            and self._is_number(filters["bedrooms"])
        ):
            bedrooms = filters["bedrooms"]

            if (
                "bedrooms_min" in filters
                and self._is_number(
                    filters["bedrooms_min"]
                )
                and bedrooms < filters["bedrooms_min"]
            ):
                errors.append(
                    "Exact bedroom count conflicts "
                    "with bedrooms_min"
                )

            if (
                "bedrooms_max" in filters
                and self._is_number(
                    filters["bedrooms_max"]
                )
                and bedrooms > filters["bedrooms_max"]
            ):
                errors.append(
                    "Exact bedroom count conflicts "
                    "with bedrooms_max"
                )

        # ---------------------------------------------
        # Exact bathroom conflicts
        # ---------------------------------------------

        if (
            "bathrooms" in filters
            and self._is_number(filters["bathrooms"])
        ):
            bathrooms = filters["bathrooms"]

            if (
                "bathrooms_min" in filters
                and self._is_number(
                    filters["bathrooms_min"]
                )
                and bathrooms < filters["bathrooms_min"]
            ):
                errors.append(
                    "Exact bathroom count conflicts "
                    "with bathrooms_min"
                )

            if (
                "bathrooms_max" in filters
                and self._is_number(
                    filters["bathrooms_max"]
                )
                and bathrooms > filters["bathrooms_max"]
            ):
                errors.append(
                    "Exact bathroom count conflicts "
                    "with bathrooms_max"
                )

        # ---------------------------------------------
        # Amenities / taxonomy terms
        # ---------------------------------------------

        self._validate_taxonomy_list(
            filters,
            "amenities",
            errors,
        )

        self._validate_taxonomy_list(
            filters,
            "exclude_amenities",
            errors,
        )

        # ---------------------------------------------
        # Required/excluded amenity conflict
        # ---------------------------------------------

        required = filters.get("amenities")
        excluded = filters.get("exclude_amenities")

        if (
            isinstance(required, (list, tuple, set))
            and isinstance(excluded, (list, tuple, set))
        ):

            required_normalized = {
                self._normalize_text(item)
                for item in required
                if isinstance(item, str)
            }

            excluded_normalized = {
                self._normalize_text(item)
                for item in excluded
                if isinstance(item, str)
            }

            conflicts = (
                required_normalized
                & excluded_normalized
            )

            for term in sorted(conflicts):
                errors.append(
                    f"Taxonomy term '{term}' cannot be "
                    "both required and excluded"
                )

        return len(errors) == 0, errors
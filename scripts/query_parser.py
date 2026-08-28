# scripts/query_parser.py

import re
import pandas as pd

listings = pd.read_csv(
    "data/raw/all_listings.csv"
)

valid_cities = (
    listings["L_City"]
    .dropna()
    .unique()
    .tolist()
)

class QueryParser:

    def __init__(
        self,
        valid_cities=None,
        valid_amenities=None
    ):
        self.valid_cities = {
            city.lower(): city
            for city in (valid_cities or [])
        }

        self.valid_amenities = {
            amenity.lower(): amenity.lower()
            for amenity in (valid_amenities or [])
        }

        self.max_price = 100_000_000
        self.max_bedrooms = 20
        self.max_bathrooms = 20

    # -------------------------------------------------
    # NUMBER NORMALIZATION
    # -------------------------------------------------

    def _parse_number(self, digits, letter=""):
        value = float(
            digits.replace(",", "")
        )

        letter = letter.lower()

        if letter == "k":
            return int(value * 1_000)

        if letter == "m":
            return int(value * 1_000_000)

        return int(value) if value.is_integer() else value

    # -------------------------------------------------
    # VALIDATION
    # -------------------------------------------------

    def _validate_price(self, value):

        if value < 0:
            raise ValueError(
                "Price cannot be negative."
            )

        if value > self.max_price:
            raise ValueError(
                f"Price exceeds allowed maximum "
                f"of {self.max_price}."
            )

        return value

    def _validate_bedrooms(self, value):

        if value < 0 or value > self.max_bedrooms:
            raise ValueError(
                f"Bedrooms must be between 0 "
                f"and {self.max_bedrooms}."
            )

        return value

    def _validate_bathrooms(self, value):

        if value < 0 or value > self.max_bathrooms:
            raise ValueError(
                f"Bathrooms must be between 0 "
                f"and {self.max_bathrooms}."
            )

        return value

    def _validate_city(self, city):

        if not self.valid_cities:
            return city

        normalized = city.strip().lower()

        if normalized not in self.valid_cities:
            raise ValueError(
                f"Invalid city: {city}"
            )

        return self.valid_cities[
            normalized
        ]

    # -------------------------------------------------
    # MAIN PARSER
    # -------------------------------------------------

    def parse(self, query):

        filters = {}

        query = query.strip()

        # =================================================
        # PRICE
        # =================================================

        # under 700k / below $700000 / less than 700k
        match = re.search(
            r"(?:under|below|less than|up to)\s+\$?"
            r"([\d,]+(?:\.\d+)?)\s*([km]?)\b",
            query,
            re.I
        )

        if match:

            value = self._parse_number(
                match.group(1),
                match.group(2)
            )

            filters["price_max"] = (
                self._validate_price(value)
            )

        # over 600k / above / more than / at least
        match = re.search(
            r"(?:over|above|more than|at least)\s+\$?"
            r"([\d,]+(?:\.\d+)?)\s*([km]?)\b",
            query,
            re.I
        )

        if match:

            value = self._parse_number(
                match.group(1),
                match.group(2)
            )

            filters["price_min"] = (
                self._validate_price(value)
            )

        # between 500k and 800k
        match = re.search(
            r"between\s+\$?"
            r"([\d,]+(?:\.\d+)?)\s*([km]?)"
            r"\s+(?:and|to)\s+\$?"
            r"([\d,]+(?:\.\d+)?)\s*([km]?)",
            query,
            re.I
        )

        if match:

            low = self._parse_number(
                match.group(1),
                match.group(2)
            )

            high = self._parse_number(
                match.group(3),
                match.group(4)
            )

            low = self._validate_price(low)
            high = self._validate_price(high)

            if low > high:
                raise ValueError(
                    "Minimum price cannot exceed maximum price."
                )

            filters["price_min"] = low
            filters["price_max"] = high

        # =================================================
        # BEDROOMS
        # =================================================

        # 3+ bed
        match = re.search(
            r"\b(\d+)\s*\+\s*"
            r"(?:bed|beds|bedroom|bedrooms|br)\b",
            query,
            re.I
        )

        if match:

            filters["bedrooms_min"] = (
                self._validate_bedrooms(
                    int(match.group(1))
                )
            )

        # at least 3 bedrooms
        elif match := re.search(
            r"(?:at least|minimum|min)\s+"
            r"(\d+)\s*"
            r"(?:bed|beds|bedroom|bedrooms|br)\b",
            query,
            re.I
        ):

            filters["bedrooms_min"] = (
                self._validate_bedrooms(
                    int(match.group(1))
                )
            )

        # up to 4 bedrooms / max 4 bedrooms
        elif match := re.search(
            r"(?:up to|max(?:imum)?|no more than)\s+"
            r"(\d+)\s*"
            r"(?:bed|beds|bedroom|bedrooms|br)\b",
            query,
            re.I
        ):

            filters["bedrooms_max"] = (
                self._validate_bedrooms(
                    int(match.group(1))
                )
            )

        # exactly 3 bed
        elif match := re.search(
            r"\b(\d+)\s*"
            r"(?:bed|beds|bedroom|bedrooms|br)\b",
            query,
            re.I
        ):

            filters["bedrooms"] = (
                self._validate_bedrooms(
                    int(match.group(1))
                )
            )

        # =================================================
        # BATHROOMS
        # =================================================

        # 2+ bath
        match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*\+\s*"
            r"(?:bath|baths|bathroom|bathrooms|ba)\b",
            query,
            re.I
        )

        if match:

            filters["bathrooms_min"] = (
                self._validate_bathrooms(
                    float(match.group(1))
                )
            )

        # at least 2 baths
        elif match := re.search(
            r"(?:at least|minimum|min)\s+"
            r"(\d+(?:\.\d+)?)\s*"
            r"(?:bath|baths|bathroom|bathrooms|ba)\b",
            query,
            re.I
        ):

            filters["bathrooms_min"] = (
                self._validate_bathrooms(
                    float(match.group(1))
                )
            )

        # max 3 baths
        elif match := re.search(
            r"(?:up to|max(?:imum)?|no more than)\s+"
            r"(\d+(?:\.\d+)?)\s*"
            r"(?:bath|baths|bathroom|bathrooms|ba)\b",
            query,
            re.I
        ):

            filters["bathrooms_max"] = (
                self._validate_bathrooms(
                    float(match.group(1))
                )
            )

        # exactly 2 bath
        elif match := re.search(
            r"\b(\d+(?:\.\d+)?)\s*"
            r"(?:bath|baths|bathroom|bathrooms|ba)\b",
            query,
            re.I
        ):

            filters["bathrooms"] = (
                self._validate_bathrooms(
                    float(match.group(1))
                )
            )

        # =================================================
        # CITY
        # =================================================

        city_match = re.search(
            r"\bin\s+"
            r"([A-Za-z][A-Za-z.\-']*"
            r"(?:\s+[A-Za-z][A-Za-z.\-']*)*?)"
            r"(?=\s+(?:under|over|below|above|with|without|"
            r"near|at least|up to|between|\d+\s*(?:bed|bath))"
            r"|,|$)",
            query,
            re.I
        )

        if city_match:

            city = city_match.group(1).strip()

            city = re.sub(
                r"\s+(?:area|region)$",
                "",
                city,
                flags=re.I
            )

            filters["city"] = (
                self._validate_city(city)
            )

        # =================================================
        # AMENITIES
        # =================================================

        amenities_required = []
        amenities_excluded = []

        for amenity in self.valid_amenities:

            escaped = re.escape(
                amenity
            )

            # no pool / without pool / exclude pool
            neg_pattern = (
                r"(?:no|without|exclude|excluding)"
                r"\s+(?:a\s+)?"
                + escaped
                + r"\b"
            )

            if re.search(
                neg_pattern,
                query,
                re.I
            ):

                amenities_excluded.append(
                    amenity
                )

                continue

            # Otherwise treat explicit mention as desired
            if re.search(
                r"\b" + escaped + r"\b",
                query,
                re.I
            ):

                amenities_required.append(
                    amenity
                )

        if amenities_required:

            filters["amenities"] = (
                sorted(
                    set(amenities_required)
                )
            )

        if amenities_excluded:

            filters["exclude_amenities"] = (
                sorted(
                    set(amenities_excluded)
                )
            )

        return filters

    # -------------------------------------------------
    # PARAMETERIZED SQL
    # -------------------------------------------------

    def to_sql(self, filters):

        conditions = []
        params = []

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

        if "city" in filters:

            conditions.append(
                "L_City = %s"
            )

            params.append(
                filters["city"]
            )

        # Example assumes amenities are searchable
        # in L_Remarks.
        for amenity in filters.get(
            "amenities",
            []
        ):

            conditions.append(
                "LOWER(L_Remarks) LIKE %s"
            )

            params.append(
                f"%{amenity.lower()}%"
            )

        for amenity in filters.get(
            "exclude_amenities",
            []
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


if __name__ == "__main__":

    valid_cities = [
        "Irvine",
        "Sacramento",
        "San Francisco",
        "Fremont",
        "Los Angeles",
        "San Diego"
    ]

    valid_amenities = [
        "pool",
        "garage",
        "solar panels",
        "gym",
        "balcony",
        "pet friendly",
        "home office",
        "ev charger"
    ]

    parser = QueryParser(
        valid_cities=valid_cities,
        valid_amenities=valid_amenities
    )

    tests = [
        "3 bed 2 bath under 700k in Irvine with pool and garage",
        "4 bed 3 bath over 600k in Sacramento with solar panels",
        "1 bed in San Francisco near transit",
        "4+ bed under 900k in Fremont",
        "between 500k and 850k in Irvine",
        "at least 3 bed and 2+ bath in San Diego",
        "3 bed with pool but no garage",
        "under 1.2m in Los Angeles without pool"
    ]

    for query in tests:

        try:

            filters = parser.parse(
                query
            )

            sql, params = parser.to_sql(
                filters
            )

            print(query)
            print(
                " filters:",
                filters
            )
            print(
                " sql:    ",
                sql
            )
            print(
                " params: ",
                params
            )
            print()

        except ValueError as error:

            print(query)
            print(
                " ERROR:",
                error
            )
            print()
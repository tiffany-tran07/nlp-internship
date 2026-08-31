from scripts.query_parser import QueryParser
from scripts.schema_validator import SchemaValidator

# tests/test_week4.py

from pathlib import Path

import pandas as pd
import pytest

from scripts.query_parser import QueryParser
from scripts.schema_validator import SchemaValidator


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VALIDITY_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "housing_query_validity.csv"
)


# ============================================================
# CSV HELPERS
# ============================================================

def load_on_topic_queries():
    """
    Load ONLY queries where on_topic == True.

    Expected CSV columns:
        id
        query
        on_topic
    """
    df = pd.read_csv(VALIDITY_CSV)

    required_columns = {
        "id",
        "query",
        "on_topic",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"housing_query_validity.csv is missing "
            f"columns: {sorted(missing)}"
        )

    # Normalize values because CSV booleans may be represented
    # as True, TRUE, true, 1, etc.
    on_topic_mask = (
        df["on_topic"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )

    on_topic = df.loc[
        on_topic_mask,
        ["id", "query"],
    ].copy()

    # Remove unusable rows.
    on_topic = on_topic.dropna(
        subset=["query"]
    )

    on_topic["query"] = (
        on_topic["query"]
        .astype(str)
        .str.strip()
    )

    on_topic = on_topic[
        on_topic["query"] != ""
    ]

    return on_topic


# Load once during test collection.
ON_TOPIC_DF = load_on_topic_queries()

ON_TOPIC_CASES = [
    pytest.param(
        row.query,
        id=f"query_{row.id}",
    )
    for row in ON_TOPIC_DF.itertuples(
        index=False
    )
]


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="module")
def parser():
    """
    Real parser using:
        data/raw/all_listings.csv
        data/processed/taxonomy.json
    """
    return QueryParser()


@pytest.fixture(scope="module")
def validator():
    return SchemaValidator()


# ============================================================
# BASIC PARSER TESTS
# ============================================================

def test_parser_returns_dictionary(parser):
    result = parser.parse(
        "3 bed in Irvine"
    )

    assert isinstance(
        result,
        dict,
    )


def test_empty_query_rejected(parser):
    with pytest.raises(ValueError):
        parser.parse("")


def test_whitespace_query_rejected(parser):
    with pytest.raises(ValueError):
        parser.parse("     ")


def test_non_string_query_rejected(parser):
    with pytest.raises(TypeError):
        parser.parse(123)


# ============================================================
# PRICE TESTS
# ============================================================

@pytest.mark.parametrize(
    "query, expected",
    [
        ("homes under 700k", 700_000),
        ("homes below 800k", 800_000),
        ("homes less than 900k", 900_000),
        ("homes up to 1m", 1_000_000),
        ("homes under $750000", 750_000),
        ("budget under 600000", 600_000),
        ("price under 500000", 500_000),
        ("condos below $1.2m", 1_200_000),
    ],
)
def test_price_max_patterns(
    parser,
    query,
    expected,
):
    filters = parser.parse(query)

    assert filters["price_max"] == expected


@pytest.mark.parametrize(
    "query, expected",
    [
        ("homes over 600k", 600_000),
        ("homes above 700k", 700_000),
        ("homes more than 800k", 800_000),
        ("homes at least 1m", 1_000_000),
        ("homes over $950000", 950_000),
        ("price above 500000", 500_000),
        ("budget over 1.5m", 1_500_000),
    ],
)
def test_price_min_patterns(
    parser,
    query,
    expected,
):
    filters = parser.parse(query)

    assert filters["price_min"] == expected


@pytest.mark.parametrize(
    "query, expected_min, expected_max",
    [
        (
            "between 500k and 800k",
            500_000,
            800_000,
        ),
        (
            "between $600000 and $900000",
            600_000,
            900_000,
        ),
        (
            "between 1m and 1.5m",
            1_000_000,
            1_500_000,
        ),
    ],
)
def test_price_ranges(
    parser,
    query,
    expected_min,
    expected_max,
):
    filters = parser.parse(query)

    assert filters["price_min"] == expected_min
    assert filters["price_max"] == expected_max


def test_invalid_reverse_price_range(parser):
    with pytest.raises(ValueError):
        parser.parse(
            "between 900k and 500k"
        )


# ============================================================
# IMPORTANT REGRESSION:
# BED/BATH NUMBERS MUST NOT BECOME PRICES
# ============================================================

@pytest.mark.parametrize(
    "query",
    [
        "at least 3 bedrooms",
        "at least 4 bedrooms",
        "up to 4 bedrooms",
        "max 5 bedrooms",
        "no more than 2 bedrooms",
        "at least 2 bathrooms",
        "up to 3 bathrooms",
        "no more than 2 baths",
        "2+ bathrooms",
        "4+ bedrooms",
    ],
)
def test_bed_bath_numbers_do_not_create_prices(
    parser,
    query,
):
    filters = parser.parse(query)

    assert "price_min" not in filters
    assert "price_max" not in filters


# ============================================================
# BEDROOM TESTS
# ============================================================

@pytest.mark.parametrize(
    "query, key, expected",
    [
        (
            "3 bedrooms",
            "bedrooms",
            3,
        ),
        (
            "3 bed",
            "bedrooms",
            3,
        ),
        (
            "3 beds",
            "bedrooms",
            3,
        ),
        (
            "3 br",
            "bedrooms",
            3,
        ),
        (
            "3+ bedrooms",
            "bedrooms_min",
            3,
        ),
        (
            "at least 4 bedrooms",
            "bedrooms_min",
            4,
        ),
        (
            "minimum 2 bed",
            "bedrooms_min",
            2,
        ),
        (
            "up to 5 bedrooms",
            "bedrooms_max",
            5,
        ),
        (
            "max 4 beds",
            "bedrooms_max",
            4,
        ),
        (
            "no more than 3 bedrooms",
            "bedrooms_max",
            3,
        ),
    ],
)
def test_bedroom_patterns(
    parser,
    query,
    key,
    expected,
):
    filters = parser.parse(query)

    assert filters[key] == expected


# ============================================================
# BATHROOM TESTS
# ============================================================

@pytest.mark.parametrize(
    "query, key, expected",
    [
        (
            "2 bathrooms",
            "bathrooms",
            2.0,
        ),
        (
            "2 bath",
            "bathrooms",
            2.0,
        ),
        (
            "2 baths",
            "bathrooms",
            2.0,
        ),
        (
            "2.5 bathrooms",
            "bathrooms",
            2.5,
        ),
        (
            "2+ baths",
            "bathrooms_min",
            2.0,
        ),
        (
            "at least 2 bathrooms",
            "bathrooms_min",
            2.0,
        ),
        (
            "up to 3 bathrooms",
            "bathrooms_max",
            3.0,
        ),
        (
            "max 2.5 baths",
            "bathrooms_max",
            2.5,
        ),
        (
            "no more than 2 baths",
            "bathrooms_max",
            2.0,
        ),
    ],
)
def test_bathroom_patterns(
    parser,
    query,
    key,
    expected,
):
    filters = parser.parse(query)

    assert filters[key] == expected


# ============================================================
# CITY TESTS
# ============================================================

@pytest.mark.parametrize(
    "query, expected",
    [
        (
            "3 bed in Irvine",
            "Irvine",
        ),
        (
            "homes in irvine",
            "Irvine",
        ),
        (
            "condos in Los Angeles",
            "Los Angeles",
        ),
        (
            "homes in San Diego with pool",
            "San Diego",
        ),
        (
            "properties in San Francisco",
            "San Francisco",
        ),
    ],
)
def test_city_parsing(
    parser,
    query,
    expected,
):
    filters = parser.parse(query)

    assert filters["city"].lower() == (
        expected.lower()
    )


def test_city_does_not_absorb_pet_friendly(parser):
    filters = parser.parse(
        "3 bed in Irvine pet friendly"
    )

    assert filters["city"].lower() == "irvine"


def test_city_does_not_absorb_new_construction(
    parser,
):
    filters = parser.parse(
        "new construction in Irvine"
    )

    assert filters["city"].lower() == "irvine"


# ============================================================
# TAXONOMY / AMENITY TESTS
# ============================================================

@pytest.mark.parametrize(
    "query, expected",
    [
        (
            "home with pool",
            "pool",
        ),
        (
            "home with garage",
            "garage",
        ),
        (
            "home with gym",
            "gym",
        ),
        (
            "home with balcony",
            "balcony",
        ),
        (
            "home with home office",
            "home office",
        ),
        (
            "home with ev charger",
            "ev charger",
        ),
        (
            "pet friendly home",
            "pet friendly",
        ),
    ],
)
def test_taxonomy_terms(
    parser,
    query,
    expected,
):
    filters = parser.parse(query)

    assert expected in filters.get(
        "amenities",
        [],
    )


# ============================================================
# TAXONOMY ALIAS TESTS
# ============================================================

@pytest.mark.parametrize(
    "query, canonical",
    [
        (
            "pets allowed",
            "pet friendly",
        ),
        (
            "pet-friendly condo",
            "pet friendly",
        ),
        (
            "central air",
            "air conditioning",
        ),
        (
            "three car garage",
            "3-car garage",
        ),
        (
            "three-car garage",
            "3-car garage",
        ),
        (
            "near the beach",
            "near beach",
        ),
        (
            "close to transit",
            "near transit",
        ),
        (
            "washer/dryer",
            "in-unit laundry",
        ),
    ],
)
def test_taxonomy_aliases(
    parser,
    query,
    canonical,
):
    filters = parser.parse(query)

    assert canonical in filters.get(
        "amenities",
        [],
    )


# ============================================================
# AMENITY NEGATION
# ============================================================

@pytest.mark.parametrize(
    "query, expected",
    [
        (
            "no pool",
            "pool",
        ),
        (
            "without pool",
            "pool",
        ),
        (
            "exclude pool",
            "pool",
        ),
        (
            "not garage",
            "garage",
        ),
        (
            "don't want a pool",
            "pool",
        ),
        (
            "do not want a garage",
            "garage",
        ),
        (
            "avoid solar panels",
            "solar",
        ),
    ],
)
def test_amenity_negation(
    parser,
    query,
    expected,
):
    filters = parser.parse(query)

    assert expected in filters.get(
        "exclude_amenities",
        [],
    )

    assert expected not in filters.get(
        "amenities",
        [],
    )


# ============================================================
# LONGEST TAXONOMY MATCH
# ============================================================

def test_community_pool_not_double_counted(parser):
    filters = parser.parse(
        "home with community pool"
    )

    amenities = filters.get(
        "amenities",
        [],
    )

    assert "community pool" in amenities

    # "pool" should not also be independently added.
    assert "pool" not in amenities


def test_three_car_garage_not_double_counted(
    parser,
):
    filters = parser.parse(
        "home with three car garage"
    )

    amenities = filters.get(
        "amenities",
        [],
    )

    assert "3-car garage" in amenities


# ============================================================
# SCHEMA VALIDATOR TESTS
# ============================================================

def test_schema_accepts_case_insensitive_city(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "city": "irvine",
        }
    )

    assert valid, errors


def test_schema_rejects_bad_price_type(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "price_max": "oops",
        }
    )

    assert not valid

    assert any(
        "must be a number" in error
        for error in errors
    )


def test_schema_rejects_bad_bathrooms(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "bathrooms": 99,
        }
    )

    assert not valid


def test_schema_rejects_reverse_price_range(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "price_min": 900_000,
            "price_max": 500_000,
        }
    )

    assert not valid


def test_schema_rejects_reverse_bedroom_range(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "bedrooms_min": 5,
            "bedrooms_max": 2,
        }
    )

    assert not valid


def test_schema_rejects_reverse_bathroom_range(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "bathrooms_min": 4,
            "bathrooms_max": 2,
        }
    )

    assert not valid


def test_schema_rejects_unknown_filter(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "swimming_with_dolphins": True,
        }
    )

    assert not valid


def test_schema_accepts_taxonomy_alias(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "amenities": [
                "pets allowed",
            ],
        }
    )

    assert valid, errors


def test_schema_rejects_unknown_taxonomy_term(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "amenities": [
                "indoor roller coaster",
            ],
        }
    )

    assert not valid


def test_schema_rejects_required_excluded_conflict(
    validator,
):
    valid, errors = validator.validate_query(
        {
            "amenities": [
                "pool",
            ],
            "exclude_amenities": [
                "pool",
            ],
        }
    )

    assert not valid


# ============================================================
# PARAMETERIZED SQL TESTS
# ============================================================

def test_sql_uses_parameters(parser):
    filters = {
        "city": "Irvine",
        "price_max": 700_000,
    }

    sql, params = parser.to_sql(filters)

    assert "Irvine" not in sql
    assert "700000" not in sql

    assert "Irvine" in params
    assert 700_000 in params


def test_sql_injection_city_is_parameterized(parser):
    malicious = (
        "Irvine'; DROP TABLE rets_property; --"
    )

    filters = {
        "city": malicious,
    }

    sql, params = parser.to_sql(filters)

    # User content must never enter SQL text.
    assert malicious not in sql

    # It remains a bound parameter.
    assert malicious in params

    assert "DROP TABLE" not in sql


def test_sql_injection_amenity_is_parameterized(
    parser,
):
    malicious = (
        "pool%' OR 1=1 --"
    )

    filters = {
        "amenities": [
            malicious,
        ],
    }

    sql, params = parser.to_sql(filters)

    assert malicious not in sql

    assert "OR 1=1" not in sql

    assert (
        f"%{malicious.lower()}%"
        in params
    )


# ============================================================
# COMBINED QUERY TEST
# ============================================================

def test_full_query(parser):
    filters = parser.parse(
        "3 bed 2 bath under 700k "
        "in Irvine with pool and garage"
    )

    assert filters["bedrooms"] == 3
    assert filters["bathrooms"] == 2.0
    assert filters["price_max"] == 700_000
    assert filters["city"].lower() == "irvine"

    assert "pool" in filters["amenities"]
    assert "garage" in filters["amenities"]


# ============================================================
# CSV: ONLY ON-TOPIC QUERIES
# ============================================================

def test_validity_dataset_has_on_topic_queries():
    """
    Sanity check so a broken filter cannot silently cause
    zero parameterized tests.
    """
    assert len(ON_TOPIC_DF) > 0


def test_at_least_50_on_topic_query_examples():
    """
    Requirement: 50+ query tests.

    Because the next test is parameterized, every on_topic row
    becomes its own pytest test case.
    """
    assert len(ON_TOPIC_CASES) >= 50, (
        "Need at least 50 on_topic queries; "
        f"found {len(ON_TOPIC_CASES)}."
    )


@pytest.mark.parametrize(
    "query",
    ON_TOPIC_CASES,
)
def test_each_on_topic_query_can_be_parsed(
    parser,
    query,
):
    """
    Every query labeled on_topic should be accepted by the
    parser without crashing.

    Each CSV row is displayed as a separate pytest case.
    """
    result = parser.parse(query)

    assert isinstance(result, dict)


# ============================================================
# DATASET-LEVEL 90% MEASURE
# ============================================================

def test_on_topic_query_extraction_rate_at_least_90_percent(
    parser,
):
    """
    Measure how many ON-TOPIC queries result in at least one
    structured filter being extracted.

    IMPORTANT:
    This is extraction/coverage accuracy, not semantic field
    accuracy, because housing_query_validity.csv contains no
    expected parsed-filter labels.
    """

    total = len(ON_TOPIC_DF)

    assert total > 0, (
        "No on_topic queries available for evaluation."
    )

    successful = 0
    failures = []

    for row in ON_TOPIC_DF.itertuples(
        index=False
    ):
        query_id = row.id
        query = row.query

        try:
            filters = parser.parse(query)

            # For this metric, success means:
            # parser recognized at least one structured constraint.
            if filters:
                successful += 1
            else:
                failures.append(
                    (
                        query_id,
                        query,
                        "no filters extracted",
                    )
                )

        except (
            ValueError,
            TypeError,
        ) as error:

            failures.append(
                (
                    query_id,
                    query,
                    str(error),
                )
            )

    accuracy = successful / total

    # Helpful failure report if threshold is missed.
    failure_preview = "\n".join(
        f"  id={query_id}: {query!r} -> {reason}"
        for query_id, query, reason
        in failures[:15]
    )

    assert accuracy >= 0.90, (
        f"\nOn-topic extraction rate: "
        f"{accuracy:.1%}\n"
        f"Successful: {successful}/{total}\n"
        f"Failures: {len(failures)}\n\n"
        f"First failures:\n"
        f"{failure_preview}"
    )
def test_on_topic_accuracy(parser):
    total = len(ON_TOPIC_DF)
    successful = 0

    for row in ON_TOPIC_DF.itertuples(index=False):
        query = row.query

        try:
            filters = parser.parse(query)

            if filters:
                successful += 1

        except (ValueError, TypeError):
            pass

    accuracy = successful / total

    print("\n" + "=" * 50)
    print("ACCURACY RESULTS")
    print("=" * 50)
    print(f"Total on-topic queries: {total}")
    print(f"Successfully parsed:    {successful}")
    print(f"Failed:                 {total - successful}")
    print(f"Accuracy:               {accuracy:.2%}")
    print("=" * 50)

    assert accuracy >= 0.90, (
        f"Accuracy {accuracy:.2%} is below 90%"
    )


    
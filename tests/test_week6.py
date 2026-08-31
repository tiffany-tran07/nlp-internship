import json

import pandas as pd
import pytest

from scripts.entity_extractor import EntityExtractor
from scripts.signal_extractor import SignalExtractor


@pytest.fixture(scope="module")
def entity_extractor():
    return EntityExtractor(
        taxonomy_path="data/processed/taxonomy.json"
    )


@pytest.fixture(scope="module")
def extractor(entity_extractor):
    return SignalExtractor(
        entity_extractor=entity_extractor
    )


@pytest.fixture
def sample_listing():
    return {
        "L_ListingID": "TEST-001",
        "L_City": "Irvine",
        "L_SystemPrice": 850_000,
        "L_Keyword2": 3,
        "L_Keyword3": 2.5,
        "L_Remarks": (
            "Beautiful updated 3BR / 2.5BA single-family home "
            "offered at $850,000 with pool, solar panels, "
            "quartz countertops, A/C and mountain views. "
            "Seller financing available."
        ),
    }


# ============================================================
# BASIC OUTPUT
# ============================================================

def test_output_is_dict(
    extractor,
    sample_listing,
):
    result = extractor.extract_signals(
        sample_listing
    )

    assert isinstance(result, dict)


def test_output_schema(
    extractor,
    sample_listing,
):
    result = extractor.extract_signals(
        sample_listing
    )

    expected_keys = {
        "listing_id",
        "structured",
        "entities",
        "amenities",
        "condition",
        "financing",
        "location_features",
        "property_type",
        "keywords",
    }

    assert set(result.keys()) == expected_keys


# ============================================================
# STRUCTURED FIELDS
# ============================================================

def test_structured_fields(
    extractor,
    sample_listing,
):
    result = extractor.extract_signals(
        sample_listing
    )

    structured = result["structured"]

    assert structured["city"] == "Irvine"
    assert structured["price"] == 850_000
    assert structured["bedrooms"] == 3
    assert structured["bathrooms"] == 2.5


def test_listing_id(
    extractor,
    sample_listing,
):
    result = extractor.extract_signals(
        sample_listing
    )

    assert result["listing_id"] == "TEST-001"


# ============================================================
# ENTITY EXTRACTOR INTEGRATION
# ============================================================

def test_entity_extractor_runs(
    extractor,
    sample_listing,
):
    result = extractor.extract_signals(
        sample_listing
    )

    entities = result["entities"]

    assert isinstance(entities, dict)

    assert "bedrooms" in entities
    assert "bathrooms" in entities
    assert "price" in entities
    assert "sqft" in entities
    assert "amenities" in entities
    assert "entities" in entities


def test_cleaned_abbreviations_reach_entity_extractor(
    extractor,
):
    """
    SignalExtractor should clean 3BR and 2BA before
    passing cleaned_text to EntityExtractor.
    """

    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": "Beautiful 3BR / 2BA home.",
        }
    )

    assert result["entities"]["bedrooms"] == 3
    assert result["entities"]["bathrooms"] == 2


def test_raw_text_used_for_price(
    extractor,
):
    """
    Price extraction should still receive raw text so
    formatting like $725,000 remains available.
    """

    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": "Offered at $725,000.",
        }
    )

    assert result["entities"]["price"] == 725_000


def test_cleaner_normalizes_price_suffix(
    extractor,
):
    """
    TextCleaner should normalize 1.2m to 1200000,
    allowing EntityExtractor to detect it from cleaned text.
    """

    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": "Priced at 1.2m.",
        }
    )

    assert result["entities"]["price"] == 1_200_000


# ============================================================
# AMENITIES
# ============================================================

@pytest.mark.parametrize(
    "remarks,expected",
    [
        ("Home with pool.", "pool"),
        ("Living room with fireplace.", "fireplace"),
        ("Property includes garage.", "garage"),
        ("Kitchen has quartz countertop.", "quartz countertop"),
        ("Features recessed lighting.", "recessed lighting"),
        ("Home has solar panels.", "solar"),
        ("Home includes A/C.", "air conditioning"),
    ],
)
def test_amenities(
    extractor,
    remarks,
    expected,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": remarks,
        }
    )

    assert expected in result["amenities"]


# ============================================================
# CONDITION
# ============================================================

@pytest.mark.parametrize(
    "remarks,expected",
    [
        ("Beautiful updated home.", "updated"),
        ("Fully remodeled property.", "remodeled"),
        ("Brand-new residence.", "brand-new"),
        ("Well-maintained property.", "well-maintained"),
        ("Move-in-ready home.", "move-in-ready"),
        ("New construction home.", "new construction"),
    ],
)
def test_condition(
    extractor,
    remarks,
    expected,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": remarks,
        }
    )

    assert expected in result["condition"]


# ============================================================
# LOCATION FEATURES
# ============================================================

@pytest.mark.parametrize(
    "remarks,expected",
    [
        ("Beautiful mountain view.", "mountain view"),
        ("Waterfront property.", "waterfront"),
        ("Home near beach.", "near beach"),
        ("Easy freeway access.", "freeway access"),
        ("Near hiking trail.", "hiking trail"),
    ],
)
def test_location_features(
    extractor,
    remarks,
    expected,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": remarks,
        }
    )

    assert expected in result["location_features"]


# ============================================================
# PROPERTY TYPE
# ============================================================

@pytest.mark.parametrize(
    "remarks,expected",
    [
        ("Beautiful condominium.", "condominium"),
        ("Single-family residence.", "single-family"),
        ("Modern loft.", "loft"),
    ],
)
def test_property_type(
    extractor,
    remarks,
    expected,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": remarks,
        }
    )

    assert expected in result["property_type"]


# ============================================================
# FINANCING
# ============================================================

@pytest.mark.parametrize(
    "remarks,expected",
    [
        ("Seller financing available.", "seller financing"),
        ("Owner financing available.", "seller financing"),
        ("Seller will carry.", "seller financing"),
        ("Cash only sale.", "cash only"),
        ("FHA financing available.", "fha"),
        ("VA financing available.", "va"),
        ("Assumable mortgage available.", "assumable loan"),
    ],
)
def test_financing(
    extractor,
    remarks,
    expected,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": remarks,
        }
    )

    assert expected in result["financing"]


# ============================================================
# KEYWORDS
# ============================================================

def test_keywords_include_all_categories(
    extractor,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": (
                "Updated single-family home "
                "with pool and mountain view."
            ),
        }
    )

    keywords = result["keywords"]

    assert "updated" in keywords
    assert "single-family" in keywords
    assert "pool" in keywords
    assert "mountain view" in keywords


def test_keywords_unique(
    extractor,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": "Pool pool pool pool.",
        }
    )

    assert result["keywords"].count("pool") == 1


# ============================================================
# EMPTY / MISSING VALUES
# ============================================================

def test_empty_remarks(
    extractor,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": "",
        }
    )

    assert result["amenities"] == []
    assert result["condition"] == []
    assert result["financing"] == []
    assert result["location_features"] == []
    assert result["property_type"] == []
    assert result["keywords"] == []


def test_missing_remarks(
    extractor,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
        }
    )

    assert result["amenities"] == []
    assert result["keywords"] == []


def test_nan_remarks(
    extractor,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": float("nan"),
        }
    )

    assert result["amenities"] == []
    assert result["keywords"] == []


def test_missing_structured_values(
    extractor,
):
    result = extractor.extract_signals(
        {
            "L_ListingID": "X",
            "L_Remarks": "Pool.",
        }
    )

    structured = result["structured"]

    assert structured["city"] is None
    assert structured["price"] is None
    assert structured["bedrooms"] is None
    assert structured["bathrooms"] is None


def test_invalid_listing_record(
    extractor,
):
    with pytest.raises(TypeError):
        extractor.extract_signals(
            "not a dictionary"
        )


# ============================================================
# FULL INTEGRATION TEST
# ============================================================

def test_full_listing(
    extractor,
    sample_listing,
):
    result = extractor.extract_signals(
        sample_listing
    )

    assert result["listing_id"] == "TEST-001"

    # Structured
    assert result["structured"]["city"] == "Irvine"
    assert result["structured"]["price"] == 850_000
    assert result["structured"]["bedrooms"] == 3
    assert result["structured"]["bathrooms"] == 2.5

    # EntityExtractor
    assert result["entities"]["bedrooms"] == 3

    # Your EntityExtractor rounds 2.5 using its
    # current project convention.
    assert result["entities"]["bathrooms"] == 3

    assert result["entities"]["price"] == 850_000

    # Signals
    assert "pool" in result["amenities"]
    assert "solar" in result["amenities"]
    assert "quartz countertop" in result["amenities"]
    assert "air conditioning" in result["amenities"]

    assert "updated" in result["condition"]

    assert "single-family" in result["property_type"]

    assert "mountain view" in result["location_features"]

    assert "seller financing" in result["financing"]


# ============================================================
# CSV PROCESSING
# ============================================================

def test_process_csv(
    extractor,
    tmp_path,
):
    input_path = tmp_path / "listings.csv"
    output_path = tmp_path / "signals.csv"

    df = pd.DataFrame(
        [
            {
                "L_ListingID": "1",
                "L_City": "Irvine",
                "L_SystemPrice": 700000,
                "L_Keyword2": 3,
                "L_Keyword3": 2,
                "L_Remarks": (
                    "Updated 3BR / 2BA home "
                    "with pool."
                ),
            },
            {
                "L_ListingID": "2",
                "L_City": "San Diego",
                "L_SystemPrice": 900000,
                "L_Keyword2": 4,
                "L_Keyword3": 3,
                "L_Remarks": (
                    "Single-family home "
                    "with mountain view."
                ),
            },
        ]
    )

    df.to_csv(
        input_path,
        index=False,
    )

    output_df = extractor.process_csv(
        input_path=input_path,
        output_path=output_path,
    )

    assert len(output_df) == 2
    assert output_path.exists()

    saved = pd.read_csv(
        output_path
    )

    assert len(saved) == 2

    amenities = json.loads(
        saved.loc[0, "amenities"]
    )

    assert "pool" in amenities

    locations = json.loads(
        saved.loc[
            1,
            "location_features"
        ]
    )

    assert "mountain view" in locations


# ============================================================
# CSV OUTPUT SCHEMA
# ============================================================

def test_process_csv_output_columns(
    extractor,
    tmp_path,
):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"

    pd.DataFrame(
        [
            {
                "L_ListingID": "1",
                "L_City": "Irvine",
                "L_SystemPrice": 700000,
                "L_Keyword2": 3,
                "L_Keyword3": 2,
                "L_Remarks": "Pool home.",
            }
        ]
    ).to_csv(
        input_path,
        index=False,
    )

    result = extractor.process_csv(
        input_path=input_path,
        output_path=output_path,
    )

    expected_columns = {
        "listing_id",
        "city",
        "price",
        "bedrooms",
        "bathrooms",
        "entity_bedrooms",
        "entity_bathrooms",
        "entity_price",
        "entity_sqft",
        "amenities",
        "condition",
        "financing",
        "location_features",
        "property_type",
        "keywords",
        "taxonomy_entities",
    }

    assert set(result.columns) == expected_columns

# ============================================================
# STRUCTURED FIELD ACCURACY
# ============================================================

def test_structured_field_accuracy(
    extractor,
):
    df = pd.read_csv(
        "data/processed/cleaned_listing_sample.csv"
    )

    field_map = {
        "city": "L_City",
        "price": "L_SystemPrice",
        "bedrooms": "L_Keyword2",
        "bathrooms": "L_Keyword3",
    }

    stats = {
        field: {
            "correct": 0,
            "total": 0,
        }
        for field in field_map
    }

    for record in df.to_dict(
        orient="records"
    ):
        result = extractor.extract_signals(
            record
        )

        structured = result["structured"]

        for output_field, source_column in (
            field_map.items()
        ):
            expected = record.get(
                source_column
            )

            actual = structured.get(
                output_field
            )

            # Normalize missing values.
            if pd.isna(expected):
                expected = None

            if pd.isna(actual):
                actual = None

            stats[
                output_field
            ]["total"] += 1

            if actual == expected:
                stats[
                    output_field
                ]["correct"] += 1

    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    total_correct = 0
    total_checks = 0

    print()
    print("=" * 60)
    print("STRUCTURED FIELD ACCURACY")
    print("=" * 60)

    for field, values in stats.items():

        correct = values["correct"]
        total = values["total"]

        accuracy = (
            correct / total
            if total
            else 0
        )

        total_correct += correct
        total_checks += total

        print(
            f"{field:<12} "
            f"{correct:>4}/{total:<4} "
            f"{accuracy:>8.2%}"
        )

    overall_accuracy = (
        total_correct / total_checks
        if total_checks
        else 0
    )

    print("-" * 60)

    print(
        f"{'OVERALL':<12} "
        f"{total_correct:>4}/{total_checks:<4} "
        f"{overall_accuracy:>8.2%}"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # REQUIREMENT
    # --------------------------------------------------------

    assert overall_accuracy >= 0.90, (
        f"Structured field accuracy "
        f"{overall_accuracy:.2%} "
        f"is below required 90%"
    )
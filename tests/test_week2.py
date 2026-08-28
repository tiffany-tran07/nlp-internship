import pandas as pd
import pytest

from scripts.text_cleaning import TextCleaner


@pytest.fixture
def cleaner():
    return TextCleaner()


@pytest.mark.parametrize(
    "text,expected",
    [
        ("priced at 450k", "450000"),
        ("$1.2m home", "1200000"),
        ("listed for 875K", "875000"),
        ("asking 2.5M", "2500000"),
    ]
)
def test_price_normalization(cleaner, text, expected):
    result = cleaner.normalize_prices(text)

    assert expected in result


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1,500 sqft", "1500 sqft"),
        ("2,750 square feet", "2750 square feet"),
        ("1,250,000", "1250000"),
    ]
)
def test_measurement_normalization(cleaner, text, expected):
    result = cleaner.normalize_measurements(text)

    assert expected in result


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3 BR home", "3 bedroom home"),
        ("2 BA condo", "2 bathroom condominium"),
        ("w/ pool", "with pool"),
        ("w/o HOA", "without homeowners association"),
        ("A/C included", "air conditioning included"),
        ("1500 sqft", "1500 square feet"),
    ]
)
def test_abbreviation_expansion(cleaner, text, expected):
    result = cleaner.clean_text(text)

    assert expected in result


@pytest.mark.parametrize(
    "text,expected",
    [
        ("<p>Beautiful Home</p>", "beautiful home"),
        ("<div>Pool</div>", "pool"),
        ("<strong>Updated</strong> kitchen", "updated kitchen"),
    ]
)
def test_html_removal(cleaner, text, expected):
    result = cleaner.clean_text(text)

    assert expected in result


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Visit https://example.com", "url"),
        ("See www.example.com today", "url"),
    ]
)
def test_url_normalization(cleaner, text, expected):
    result = cleaner.clean_text(text)

    assert expected in result


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Email agent@test.com", "email"),
        ("Contact sales@example.org", "email"),
    ]
)
def test_email_normalization(cleaner, text, expected):
    result = cleaner.clean_text(text)

    assert expected in result


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Beautiful HOME", "beautiful home"),
        ("POOL and SPA", "pool and spa"),
    ]
)
def test_lowercase(cleaner, text, expected):
    result = cleaner.clean_text(text)

    assert result == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("beautiful!!! home", "beautiful home"),
        ("pool, spa, gym", "pool spa gym"),
        ("updated @ home", "updated home"),
    ]
)
def test_punctuation_removal(cleaner, text, expected):
    result = cleaner.clean_text(text)

    assert result == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("beautiful     home", "beautiful home"),
        ("pool\n\nspa", "pool spa"),
        ("garage\t\tparking", "garage parking"),
    ]
)
def test_whitespace_normalization(cleaner, text, expected):
    result = cleaner.clean_text(text)

    assert result == expected


def test_null_input(cleaner):
    result = cleaner.clean_text(None)

    assert result == ""


def test_profiling(cleaner):
    df = pd.read_csv(
        "data/processed/listing_sample.csv"
    )

    profile = cleaner.profile_column(
        df,
        "remarks"
    )

    expected_keys = {
        "row_count",
        "null_count",
        "null_rate",
        "avg_length",
        "common_terms",
        "price_mentions",
        "has_html",
        "url_mentions",
        "email_mentions",
        "common_abbreviations"
    }

    assert expected_keys.issubset(
        profile.keys()
    )


def test_profile_null_rate(cleaner):
    df = pd.DataFrame({
        "remarks": [
            "Nice home",
            None,
            "Pool"
        ]
    })

    profile = cleaner.profile_column(
        df,
        "remarks"
    )

    assert profile["null_rate"] == pytest.approx(
        1 / 3
    )


def test_profile_html_count(cleaner):
    df = pd.DataFrame({
        "remarks": [
            "<p>Home</p>",
            "No HTML",
            "<div>Pool</div>"
        ]
    })

    profile = cleaner.profile_column(
        df,
        "remarks"
    )

    assert profile["has_html"] == 2


def test_profile_price_mentions(cleaner):
    df = pd.DataFrame({
        "remarks": [
            "$450000",
            "Priced at $700000",
            "No price here"
        ]
    })

    profile = cleaner.profile_column(
        df,
        "remarks"
    )

    assert profile["price_mentions"] == 2
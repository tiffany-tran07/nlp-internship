import pandas as pd
from scripts.entity_extractory import EntityExtractor

def test_extract_bedrooms():
    extractor = EntityExtractor()
    assert extractor.extract_bedrooms("3 bed, 2 bath") == 3
    assert extractor.extract_bedrooms("2bd apartment") == 2
    assert extractor.extract_bedrooms("No bedrooms mentioned") is None
    print(f"✓ Bedroom extraction passed")

def test_extract_price():
    extractor = EntityExtractor()
    assert extractor.extract_price("$450,000") == "450000"
    assert extractor.extract_price("Price: 1,200,000") == "1200000"
    assert extractor.extract_price("No price mentioned") is None
    print(f"✓ Price extraction passed")

def test_extract_amenities():
    extractor = EntityExtractor()
    assert extractor.extract_amenities("Apartment with pool and garage") == ['pool', 'garage']
    assert extractor.extract_amenities("No amenities mentioned") == []
    print(f"✓ Amenity extraction passed")

def test_extract_all():
    extractor = EntityExtractor()
    text = "3 bed, 2 bath, $450,000, with pool and garage"
    result = extractor.extract_all(text)
    assert result['bedrooms'] == 3
    assert result['price'] == 450000
    assert 'pool' in result['amenities']
    assert 'garage' in result['amenities']
    print(f"✓ Full extraction passed")

test_extract_bedrooms()
test_extract_price()
test_extract_amenities()
test_extract_all()
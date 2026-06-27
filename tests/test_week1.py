import pytest
import json
import pandas as pd

def test_taxonomy_loaded():
    with open('data/processed/taxonomy.json') as f:
        tax = json.load(f)
    assert len(tax['terms']) >= 200
    # print(f"✓ Taxonomy has {len(tax['terms'])} terms")
    assert all('id' in t and 'term' in t for t in tax['terms'])
    # print(f"✓ All terms have 'id' and 'term' keys")
def test_sample_data_quality():
    df = pd.read_csv('data/processed/listing_sample.csv')
    assert len(df) >= 500
    # print(f"✓ Sample data has {len(df)} rows")
    assert df['remarks'].str.len().min() > 50

test_taxonomy_loaded()
test_sample_data_quality()
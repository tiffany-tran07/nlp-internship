from scripts.text_cleaning import TextCleaner
import pandas as pd

def test_price_normalization():
    cleaner = TextCleaner()
    assert '450000' in cleaner.normalize_prices('priced at 450k')
    print(f"✓ Price normalization for '450k' passed")
    assert '1200000' in cleaner.normalize_prices('$1.2m home')
    print(f"✓ Price normalization for '$1.2m' passed")

def test_profiling():
    cleaner = TextCleaner()
    df = pd.read_csv('data/processed/listing_sample.csv')
    profile = cleaner.profile_column(df, 'remarks')
    assert 'null_rate' in profile
    assert 'avg_length' in profile
    print(f"✓ Profiling for 'remarks' column passed")

test_price_normalization()
test_profiling()
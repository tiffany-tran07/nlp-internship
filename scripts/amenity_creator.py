import pandas as pd
from scripts.entity_extractory import EntityExtractor
from scripts.text_cleaning import TextCleaner

df = pd.read_csv('data/processed/test_suite.csv')

cleaner = TextCleaner()
extractor = EntityExtractor()
df["remarks"] = df["remarks"].apply(cleaner.clean_text)
df.to_csv('data/processed/cleaned_suite.csv', index=False)
df["entities"] = df["remarks"].apply(extractor.extract_all)
df["found_amen"] = df["entities"].str["amenities"]
df["extracted_bedrooms"] = df["entities"].str["bedrooms"]
df["extracted_bathrooms"] = df["entities"].str["bathrooms"]
df["extracted_price"] = df["entities"].str["price"]
df["extracted_sqft"] = df["entities"].str["sqft"]

df.to_csv('data/processed/extracted_test_suite.csv', index=False)

# df = pd.read_csv('data/processed/suite_amenities.csv')
# df.pop('price')
# df.to_csv('data/processed/suite_amenities.csv')

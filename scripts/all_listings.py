from scripts.signal_extractor import SignalExtractor
from scripts.entity_extractor import EntityExtractor
import mysql.connector
import pandas as pd
import json

conn = mysql.connector.connect(
    host='localhost', user='root', password='root', database='idx_exchange')
query = """
SELECT L_ListingID, L_Address, L_City, L_Keyword2 as beds,
    LM_Dec_3 as baths, L_SystemPrice as price, L_Remarks as remarks
FROM rets_property
WHERE L_Remarks IS NOT NULL
"""
df = pd.read_sql(query, conn)
df.to_csv('data/processed/all_listings.csv', index=False)
print(len(df))

conn.close()
ent_extract = EntityExtractor()
sig_extract = SignalExtractor('data/processed/taxonomy.json', ent_extract)

def get_signals(row):
    listing_record = {
        'L_ListingID': row['L_ListingID'],
        'L_Remarks': row['remarks']
    }
    try:
        return sig_extract.extract_signals(listing_record)
    except Exception as e:
        print(f"Error on listing {row['L_ListingID']}: {e}")
        return {
            'listing_id': row['L_ListingID'],
            'entities': None,
            'amenities': [],
            'condition_keywords': [],
            'financing_terms': [],
            'location_features': []
        }

print("Extracting signals...")
signals = df.apply(get_signals, axis=1)

# Expand the dict column into separate columns
df['entities'] = signals.apply(lambda s: json.dumps(s['entities']))
df['amenities'] = signals.apply(lambda s: json.dumps(s['amenities']))
df['condition_keywords'] = signals.apply(lambda s: json.dumps(s['condition_keywords']))
df['financing_terms'] = signals.apply(lambda s: json.dumps(s['financing_terms']))
df['location_features'] = signals.apply(lambda s: json.dumps(s['location_features']))

df.to_csv('data/processed/all_listings_with_signals.csv', index=False)
print(f"Saved {len(df)} listings with signals to data/processed/all_listings_with_signals.csv")


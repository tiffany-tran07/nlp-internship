import pandas as pd
from scripts.query_parser import QueryParser

df = pd.read_csv('data/processed/housing_queries.csv')
parser = QueryParser()


def handle_parse(query):
    try:
        return parser.parse(query)
    except Exception as e:
        return {'error': str(e)}


df['filters'] = df['query'].apply(handle_parse)
parsed_df = pd.json_normalize(df['filters']).add_prefix('parsed_')
df = pd.concat([df, parsed_df], axis=1)


def _normalize(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str) and value.strip() == '':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return value.strip().lower()
    return value


# Ground-truth column -> parser output column
FIELD_MAP = {
    'max_cost': 'parsed_price_max',
    'min_cost': 'parsed_price_min',
    'city': 'parsed_city',
}

results = {}

for truth_col, parsed_col in FIELD_MAP.items():
    if parsed_col not in df.columns:
        df[parsed_col] = None
    matches = df.apply(
        lambda row: _normalize(row[truth_col]) == _normalize(row[parsed_col]),
        axis=1
    )
    results[truth_col] = matches.mean()
    df[f'{truth_col}_correct'] = matches

# bed: parser puts it under 'bedrooms' OR 'bedrooms_min' depending on "3 bed" vs "3+ bed"
for col in ('parsed_bedrooms', 'parsed_bedrooms_min'):
    if col not in df.columns:
        df[col] = None

bed_matches = df.apply(
    lambda row: _normalize(row['bed']) in
                (_normalize(row['parsed_bedrooms']), _normalize(row['parsed_bedrooms_min'])),
    axis=1
)
results['bed'] = bed_matches.mean()
df['bed_correct'] = bed_matches

# Fields the parser doesn't support yet — call this out explicitly rather than
# silently scoring 0% or skipping without comment.
UNSUPPORTED_FIELDS = ['bath', 'amenities']
for field in UNSUPPORTED_FIELDS:
    print(f"NOTE: '{field}' has no extraction logic in QueryParser.parse() — excluded from scoring.")

correct_cols = [c for c in df.columns if c.endswith('_correct')]
df['all_fields_correct'] = df[correct_cols].all(axis=1)
overall_accuracy = df['all_fields_correct'].mean()

print("\n=== Field-level accuracy (supported fields only) ===")
for field, acc in results.items():
    print(f"{field:10s}: {acc:.1%}")

print("\n=== Overall (exact-match on supported fields) ===")
print(f"{overall_accuracy:.1%}  ({df['all_fields_correct'].sum()} / {len(df)} queries fully correct)")

mismatches = df[~df['all_fields_correct']]
if not mismatches.empty:
    print(f"\n=== {len(mismatches)} mismatched queries ===")
    print(mismatches[['query'] + correct_cols].to_string(index=False))

df.to_csv('data/processed/housing_queries_parsed.csv', index=False) 
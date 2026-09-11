# Data Schemas

## API document

The search corpus uses the following normalized document shape:

```json
{
  "id": "L0001",
  "text": "Listing remarks go here",
  "metadata": {
    "address": "123 Main St",
    "city": "Irvine",
    "bedrooms": 3,
    "bathrooms": 2,
    "price": 606190
  }
}
```

`id` and `text` are required strings. `metadata` is an extensible JSON object. The API accepts up to 100,000 characters per text field and up to 50,000 documents in a corpus replacement request.

## Raw listing source

`data/raw/all_listings.csv` contains the MLS-style source columns used by the database loader: `L_ListingID`, `L_Address`, `L_City`, `beds`, `baths`, `price`, and `remarks`/`L_Remarks` depending on the exported file. The loader maps these fields to `listing_id`, `address`, `city`, `bedrooms`, `bathrooms`, `price`, and searchable `remarks`.

## Processed listing sample

`data/processed/listings.csv` is the compact evaluation corpus with `listing_id`, `remarks`, `bed`, `bath`, `city`, `price`, `amenities`, `is_relevant_to`, and `role`. `role` identifies relevant, distractor, or other evaluation examples.

## Taxonomy JSON

The current taxonomy uses:

```json
{
  "metadata": {"version": "..."},
  "categories": {
    "amenities": [
      {"term": "pool", "aliases": ["swimming pool"]}
    ]
  }
}
```

Each category contains entries with a canonical `term` and optional string `aliases`. The parser and extractor return canonical terms. Evaluation files include `gold_features`, `matched_features`, and `missed_features`.

## Evaluation schemas

`eval_results.csv` stores per-query retrieval metrics and IDs. `accuracy_eval.csv` stores structured-field extraction comparisons. `entity_eval_results.csv` stores numeric entity correctness and predicted entity text. `taxonomy_eval_results.csv` stores gold, matched, and missed taxonomy features. These files are evidence artifacts, not production API inputs.

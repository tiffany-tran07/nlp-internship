from scripts.signal_extractor import SignalExtractor
from scripts.entity_extractor import EntityExtractor
import json
import pandas as pd


def check_signals():
    ent_extract = EntityExtractor()
    with open('data/processed/taxonomy.json', 'r') as file:
        taxonomy = json.load(file)
    sig_extract = SignalExtractor(taxonomy, ent_extract)

    df = pd.read_csv('data/processed/extracted_test_suite.csv')
    df = df.dropna(subset=['remarks'])

    print(f"Running signal extraction on {len(df)} listings...\n")

    all_results = []
    errors = []

    for _, row in df.iterrows():
        listing_record = {
            'L_ListingID': row.get('listing_id', row.name),
            'L_Remarks': row['remarks']
        }
        try:
            result = sig_extract.extract_signals(listing_record)
            all_results.append(result)
        except Exception as e:
            errors.append((listing_record['L_ListingID'], str(e)))

    print(f"Succeeded: {len(all_results)} | Errors: {len(errors)}\n")
    if errors:
        print("Errors encountered:")
        for listing_id, err in errors[:10]:
            print(f"  [{listing_id}] {err}")
        print()

    # ---- Show a handful of full examples ----
    print("=" * 70)
    print("SAMPLE RESULTS")
    print("=" * 70)
    for result in all_results[:5]:
        print(f"\nListing: {result['listing_id']}")
        print(f"  amenities:          {result['amenities']}")
        print(f"  condition_keywords: {result['condition_keywords']}")
        print(f"  financing_terms:    {result['financing_terms']}")
        print(f"  location_features:  {result['location_features']}")

    # ---- Coverage: % of listings with at least one match per bucket ----
    print("\n" + "=" * 70)
    print("COVERAGE (% of listings with at least one match per bucket)")
    print("=" * 70)
    n = len(all_results)
    if n > 0:
        for bucket in ['amenities', 'condition_keywords', 'financing_terms', 'location_features']:
            hits = sum(1 for r in all_results if len(r[bucket]) > 0)
            print(f"  {bucket:<20}: {hits}/{n} ({hits/n*100:.1f}%)")

    # ---- Most frequently matched terms per bucket, across the corpus ----
    print("\n" + "=" * 70)
    print("TOP MATCHED TERMS PER BUCKET")
    print("=" * 70)
    for bucket in ['amenities', 'condition_keywords', 'financing_terms', 'location_features']:
        term_counts = {}
        for r in all_results:
            for term in r[bucket]:
                term_counts[term] = term_counts.get(term, 0) + 1
        top_terms = sorted(term_counts.items(), key=lambda x: -x[1])[:10]
        print(f"\n{bucket}:")
        for term, count in top_terms:
            print(f"  {term:<25} {count}")

    # ---- Sanity checks ----
    print("\n" + "=" * 70)
    print("SANITY CHECKS")
    print("=" * 70)
    assert len(errors) == 0, f"{len(errors)} listings raised errors during extraction"
    for r in all_results:
        assert set(r.keys()) == {
            'listing_id', 'entities', 'amenities',
            'condition_keywords', 'financing_terms', 'location_features'
        }, f"Unexpected keys in result for {r['listing_id']}"
    print("All checks passed.")

    return all_results


if __name__ == "__main__":
    check_signals()
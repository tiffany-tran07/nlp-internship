import pandas as pd

listings = pd.read_csv('data/processed/listings.csv')
results = pd.read_csv('data/processed/eval_results.csv')

id_to_role = dict(zip(listings['listing_id'], listings['role']))
results['semantic_top1_role'] = results['semantic_top1_id'].map(id_to_role)
results['keyword_top1_role'] = results['keyword_top1_id'].map(id_to_role)

print("SEMANTIC failures — what it picked instead of the true match:")
print(results[results['semantic_p@1'] == 0]['semantic_top1_role'].value_counts())

print("\nKEYWORD failures — what it picked instead of the true match:")
print(results[results['keyword_p@1'] == 0]['keyword_top1_role'].value_counts())
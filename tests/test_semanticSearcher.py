# import json
# import ast
import pandas as pd
from scripts.semantic_searcher import SemanticSearcher
from scripts.keyword_search import KeywordSearcher  # your BM25 class

# ---------- 1. Load data ----------
listings = pd.read_csv('data/processed/listings.csv')
ground_truth = pd.read_csv('data/processed/ground_truth.csv')

remarks = listings['remarks'].tolist()
ids = listings['listing_id'].tolist()

# ---------- 2. Build both indexes ----------
semantic = SemanticSearcher()
semantic.build_index(remarks, ids=ids)

keyword = KeywordSearcher(remarks, ids=ids)  # adjust to your constructor

# ---------- 3. Metrics ----------
def precision_at_k(retrieved_ids, relevant_ids, k):
    retrieved_k = retrieved_ids[:k]
    hits = len(set(retrieved_k) & set(relevant_ids))
    return hits / k

def recall_at_k(retrieved_ids, relevant_ids, k):
    if not relevant_ids:
        return None
    retrieved_k = retrieved_ids[:k]
    hits = len(set(retrieved_k) & set(relevant_ids))
    return hits / len(relevant_ids)

def reciprocal_rank(retrieved_ids, relevant_ids):
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1 / rank
    return 0.0

# ---------- 4. Run eval ----------
K = 5  # since each query has exactly 1 relevant listing, k=5 or k=10 works; k=1 is the strictest test

rows = []
for _, row in ground_truth.iterrows():
    query = row['query']
    relevant_ids = [row['relevant_listing_ids']]  # single ID per query in your ground truth

    sem_results = semantic.search(query, top_k=K)
    kw_results = keyword.search(query, top_k=K)

    sem_ids = [r[0] for r in sem_results]  # r = (id, text, score)
    kw_ids = [r[0] for r in kw_results]

    rows.append({
        'query_id': row['query_id'],
        'query': query,
        'semantic_p@1': precision_at_k(sem_ids, relevant_ids, 1),
        'keyword_p@1': precision_at_k(kw_ids, relevant_ids, 1),
        f'semantic_p@{K}': precision_at_k(sem_ids, relevant_ids, K),
        f'keyword_p@{K}': precision_at_k(kw_ids, relevant_ids, K),
        'semantic_mrr': reciprocal_rank(sem_ids, relevant_ids),
        'keyword_mrr': reciprocal_rank(kw_ids, relevant_ids),
        'semantic_top1_id': sem_ids[0] if sem_ids else None,
        'keyword_top1_id': kw_ids[0] if kw_ids else None,
        'true_relevant_id': relevant_ids[0],
    })

results_df = pd.DataFrame(rows)

# ---------- 5. Summary ----------
print("=" * 60)
print("SUMMARY (averaged across 50 queries)")
print("=" * 60)
summary_cols = ['semantic_p@1', 'keyword_p@1', f'semantic_p@{K}', f'keyword_p@{K}',
                'semantic_mrr', 'keyword_mrr']
print(results_df[summary_cols].mean().round(3))

results_df.to_csv('data/processed/eval_results.csv', index=False)
print("\nFull per-query results saved to eval_results.csv")

# ---------- 6. Show failure cases (where each method got it wrong) ----------
print("\n" + "=" * 60)
print("QUERIES WHERE SEMANTIC MISSED (top-1 wrong)")
print("=" * 60)
misses = results_df[results_df['semantic_p@1'] == 0]
print(misses[['query', 'semantic_top1_id', 'true_relevant_id']].to_string(index=False))

print("\n" + "=" * 60)
print("QUERIES WHERE KEYWORD MISSED (top-1 wrong)")
print("=" * 60)
misses_kw = results_df[results_df['keyword_p@1'] == 0]
print(misses_kw[['query', 'keyword_top1_id', 'true_relevant_id']].to_string(index=False))
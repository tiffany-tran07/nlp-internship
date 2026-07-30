from scripts.semantic_searcher import SemanticSearcher
from scripts.keyword_search import KeywordSearcher
import pandas as pd
import time
import faiss


searcher = SemanticSearcher()
df = pd.read_csv('data/processed/extracted_test_suite.csv')
remarks = df['remarks'].to_list()

def search_embeddings(searcher, queries):


    searcher.build_index(queries)

    test_query = "a home in Irvine with 3 bedrooms and a pool. Quiet town and no hoa"

    results = searcher.search(test_query, 5)
    
    # for remark in results:
    #     print("\n\nRemark: ", remark[0])
    print(results[0][0])

def benchmark_search(searcher, queries, n_runs=50):
    # warm-up run — first call often includes model/lazy-load overhead
    _ = searcher.search(queries[0])

    latencies = []
    for _ in range(n_runs):
        q = queries[_ % len(queries)]
        start = time.perf_counter()
        searcher.search(q)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        latencies.append(elapsed)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print(f"  mean: {sum(latencies)/len(latencies):.2f}ms")
    print(f"  p50:  {p50:.2f}ms")
    print(f"  p95:  {p95:.2f}ms")
    print(f"  p99:  {p99:.2f}ms")
    return latencies

def compare_search(query, semantic_searcher, keyword_searcher, top_k=5):
    sem_results = semantic_searcher.search(query, top_k=top_k)
    kw_results = keyword_searcher.search(query, top_k=top_k)

    print(f"\nQuery: {query}\n")
    print(f"{'SEMANTIC':<60} | {'KEYWORD'}")
    print("-" * 120)
    for i in range(top_k):
        sem_text = sem_results[i][0][:55] if i < len(sem_results) else ""
        kw_text = kw_results[i][0][:55] if i < len(kw_results) else ""
        print(f"{sem_text:<60} | {kw_text}")

    # overlap: how many of the same listings show up in both top-k sets
    sem_set = {r[0] for r in sem_results}
    kw_set = {r[0] for r in kw_results}
    overlap = len(sem_set & kw_set)
    print(f"\nOverlap: {overlap}/{top_k}")

search_embeddings(searcher, remarks)

kw_searcher = KeywordSearcher(remarks)
test_queries = [
    "a home in Irvine with 3 bedrooms and a pool",  # natural language / paraphrase
    "3BR 2BA pool Irvine",                            # keyword-y phrasing of the same intent
    "quiet cul-de-sac great for kids",                # semantic/conceptual, no exact keyword match likely
    "walking distance to top rated schools",          # semantic
]
for q in remarks:
    compare_search(q, searcher, kw_searcher)

print("Indexing time:")
start = time.perf_counter()
searcher.build_index(remarks)
print(f"  semantic build_index: {time.perf_counter() - start:.2f}s")

start = time.perf_counter()
print(f"  keyword build_index:  {time.perf_counter() - start:.2f}s")

print("\nSemantic search latency:")
benchmark_search(searcher, remarks)

print("\nKeyword search latency:")
benchmark_search(kw_searcher, remarks)

# start = time.perf_counter()
# query_emb = searcher.model.encode(remarks)
# encode_time = time.perf_counter() - start

# start = time.perf_counter()
# faiss.normalize_L2(query_emb)
# searcher.index.search(query_emb, 10)
# faiss_time = time.perf_counter() - start



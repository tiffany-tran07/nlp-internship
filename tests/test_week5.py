from scripts.semantic_searcher import SemanticSearcher
from scripts.keyword_search import KeywordSearcher
import pandas as pd
import time

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



search_embeddings(searcher, remarks)

print("Indexing time:")
start = time.perf_counter()
searcher.build_index(remarks)
print(f"  semantic build_index: {time.perf_counter() - start:.2f}s")

start = time.perf_counter()
kw_searcher = KeywordSearcher(remarks)
print(f"  keyword build_index:  {time.perf_counter() - start:.2f}s")

print("\nSemantic search latency:")
benchmark_search(searcher, remarks)

print("\nKeyword search latency:")
benchmark_search(kw_searcher, remarks)




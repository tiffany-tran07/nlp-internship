from scripts.semantic_searcher import SemanticSearcher
import pandas as pd

def search_embeddings():
    searcher = SemanticSearcher()
    df = pd.read_csv('data/processed/extracted_test_suite.csv')
    remarks = df['remarks'].to_list()

    searcher.build_index(remarks)

    test_query = "a home in Irvine with 3 bedrooms and a pool"

    results = searcher.search(test_query)

    print(results)




from scripts.semantic_searcher import SemanticSearcher
import pandas as pd

def search_embeddings():
    searcher = SemanticSearcher()
    df = pd.read_csv('data/processed/extracted_test_suite.csv')
    remarks = df['remarks'].to_list()

    searcher.build_index(remarks)

    test_query = "a home in Irvine with 3 bedrooms and a pool. Quiet town and no hoa"

    results = searcher.search(test_query, 5)
    
    for remark in results:
        print("\n\nRemark: ", remark[0])

search_embeddings()




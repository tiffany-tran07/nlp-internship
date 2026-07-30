from rank_bm25 import BM25Okapi
import numpy as np

class KeywordSearcher:
    def __init__(self, remarks_list):
        self.listings = remarks_list
        # simple whitespace/lowercase tokenization
        tokenized = [doc.lower().split() for doc in remarks_list]
        self.bm25 = BM25Okapi(tokenized)

    def search(self, query, top_k=10):
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.listings[i], scores[i]) for i in top_indices]
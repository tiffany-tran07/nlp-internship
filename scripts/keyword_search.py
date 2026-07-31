from rank_bm25 import BM25Okapi
import numpy as np

class KeywordSearcher:
    def __init__(self, remarks_list, ids=None):
        self.listings = remarks_list
        self.ids = ids if ids is not None else list(range(len(remarks_list)))
        # simple whitespace/lowercase tokenization
        tokenized = [doc.lower().split() for doc in remarks_list]
        self.bm25 = BM25Okapi(tokenized)

    def search(self, query, top_k=10):
        top_k = min(top_k, len(self.listings))  # same guard as semantic searcher
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = [(self.ids[i], self.listings[i], scores[i]) for i in top_indices]
        return results
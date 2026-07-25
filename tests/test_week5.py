from scripts.semantic_searcher import SemanticSearcher
import pandas as pd

searcher = SemanticSearcher()
df = pd.read_csv('data/processed/extracted_test_suite.csv')
remarks = df['remarks']



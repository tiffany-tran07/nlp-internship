import random
import pandas as pd

df = pd.read_csv('data/processed/listing_sample.csv')
randomInts = random.sample(range(len(df)), 100)
sample_df = df.iloc[randomInts]
print(len(sample_df))
sample_df.to_csv('data/processed/test_suite.csv', index=False)

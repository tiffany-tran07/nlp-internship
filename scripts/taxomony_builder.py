import json

import nltk
from collections import Counter
from nltk.util import ngrams
import pandas as pd

df = pd.read_csv('data/processed/listing_sample.csv')
# Extract bigrams from remarks
all_text = ' '.join(df['remarks'].dropna().str.lower())
tokens = nltk.word_tokenize(all_text)
bigrams = list(ngrams(tokens, 2))
freq = Counter(bigrams)
# make json object for taxonomy
taxomony = {'terms': []}
# Top 200 bigrams become taxonomy seed
for bigram, count in freq.most_common(200):
    taxomony['terms'].append({'id': f"term_{len(taxomony['terms'])}", 'term': ' '.join(bigram), 'count': count})
    print(f"{' '.join(bigram)}: {count}")

# Save taxonomy to JSON file
with open('data/processed/taxonomy.json', 'w') as f:
    json.dump(taxomony, f)
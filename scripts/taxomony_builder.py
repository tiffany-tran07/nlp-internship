import json
import nltk
from collections import Counter
from nltk.util import ngrams
from nltk.corpus import stopwords
import pandas as pd
# nltk.download('stopwords')
df = pd.read_csv('data/processed/listing_sample.csv')
stop_words = set(stopwords.words('english'))
custom_stopwords = {
    "home", "house", "property", "features", "feature",
    "great", "beautiful", "amazing", "stunning", "lovely",
    "close", "recently", "located", "offers", "boasts",
    "perfect", "ideal", "spacious", "nice", "well", ",",
    ".", "!", "?", "(", ")", "[", "]", "{", "}", "'",
    '"', "_", "/", "\\", "|", "@", "#", "$", "%", "^",
    "&", "*", "+", "=", "<", ">", "~", "`", "entertaining", 
    "simply", "elegant", "modern", "classic", "charming", 
    "inviting", "shopping", "rare", "opportunity", "resort", 
    "style", "luxury", "conveniently", "sqft", "sq", "ft", 
    "feet", "move-in", "highlights", "1", "2", "3", 
    "4", "5", "6", "7", "8", "9", "0", "near", "n't miss",
    "whether", "highly", "desirable", "enjoy", "resort-style", 
    "sought-after", "amenitites", "comfort", "convenience", "miss",
    "peaceful", "tranquil", "serene", "breathtaking", "panoramic",
    "spectacular", "unparalleled", "exclusive", "prestigious",
    "coveted", "prime", "exceptional", "unmatched", "unrivaled", 
    "unbeatable", "unforgettable", "unparalleled", "unprecedented"
    "appeal", "quiet", "beautifully", "tastefully", "meticulously", 
    "exquisite", "luxurious", "must-see", "must-have", "must-visit", 
    "must-experience","must-enjoy", "must-explore", "must-discover", 
    "must-appreciate", "must-relax", "must-indulge", "must-immerse",
    "include", "offer", "easy", "thoughtfully", "designed", "crafted", 
    "renovated", "updated", "ft.", "step", "throughout", "cozy", 
    "bonus", "includes", "ample", "foot", "flexible", "freshly", 'fresh',
    "abundant", "nature", "construction", "full", "blend", "privacy", 
    "potential", "blend", "retreat", "seamlessly", "two", "three", 
    "four", "five", "six", "seven", "eight", "nine", "zero", "special", "create",
    "perfectly", "san", "diego", "santa", "monica", "flexibility", "new", "spa"
    , "laguna", "effortlessly", "generous"
}

all_stopwords = stop_words.union(custom_stopwords)

# Extract bigrams from remarks
all_text = ' '.join(df['remarks'].dropna().str.lower())
tokens = nltk.word_tokenize(all_text)
tokens = [token for token in tokens if token not in all_stopwords]
bigrams = list(ngrams(tokens, 2))
freq = Counter(bigrams)
# make json object for taxonomy
taxomony = {'terms': []}
# Top 200 bigrams become taxonomy seed
for bigram, count in freq.most_common(200):
    taxomony['terms'].append({'id': f"term_{len(taxomony['terms'])}", 'term': ' '.join(bigram), 'count': count})
    # print(f"{' '.join(bigram)}: {count}")

# Save taxonomy to JSON file
with open('data/processed/taxonomy.json', 'w') as f:
    json.dump(taxomony, f)
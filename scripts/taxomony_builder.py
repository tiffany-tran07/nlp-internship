import json
import nltk
from collections import Counter
from nltk.util import ngrams
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import pandas as pd
import re
# nltk.download('stopwords')
# nltk.download('punkt')
# nltk.download('punkt_tab')
# nltk.download('wordnet')

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
    "whether", "highly", "desirable", "enjoy", "enjoying", "resort-style", 
    "sought-after", "comfort", "convenience", "miss",
    "peaceful", "tranquil", "serene", "breathtaking", "panoramic",
    "spectacular", "unparalleled", "exclusive", "prestigious",
    "coveted", "prime", "exceptional", "unmatched", "unrivaled", 
    "unbeatable", "unforgettable", "unparalleled", "unprecedented",
    "appeal", "quiet", "beautifully", "tastefully", "meticulously", 
    "exquisite", "luxurious", "must-see", "must-have", "must-visit", 
    "must-experience","must-enjoy", "must-explore", "must-discover", 
    "must-appreciate", "must-relax", "must-indulge", "must-immerse",
    "include", "offer", "easy", "thoughtfully", "designed", "crafted", 
    "renovated", "updated", "ft.", "step", "throughout", "cozy", 
    "includes", "including", "ample", "foot", "flexible", "freshly", 'fresh',
    "abundant", "nature", "construction", "blend", 
    "potential", "blend", "retreat", "seamlessly", "two", "three", 
    "four", "five", "six", "seven", "eight", "nine", "zero", "special", "create",
    "perfectly", "flexibility", "new"
    , "effortlessly", "generous", "expansive", "natural", "ready", ":"
    , "situated", "convenient", "nestled", "entertainment", "seamless", "upgraded",
    "heart", "complete", "completely", "customized", "custom-built", 
    "custom-designed", "custom-crafted", "minutes", "paint", "large", "bright",
    "remodeled", "renovated", "modernized", "refreshed", "revitalized", "\u2019", "find",
    "away", "tucked", "featuring", "flows", "dedicated", "everyday", "areas", 
     "separate", "schedule", "within", "additional", "peace", "generously", "'"
    , "plan", "ownership", "amenities", "minute", "provides","space", "area", "location", "setting", "moment", "point", "line",
    "side", "end", "block", "spot", "detail", "value", "quality", "size",
    "option", "sense", "vision", "character", "atmosphere", "experience",
    "lifestyle", "living", "life", "time", "day", "night", "year", "today",
    "mind", "gem", "beauty", "charm", "art", "market", "cost", "price",
    "sale", "use", "connection", "combination",     "welcome", "boast", "showcase", "creating", "creates",
    "provide", "provides", "providing", "deliver", "delivers", "add",
    "added", "make", "making", "bring", "take", "come", "sit", "sits",
    "want", "need", "used", "lead", "capture", "combine",
    "complement", "complemented", "highlight", "surround", "surrounded",
    "install", "installed", "paint", "painted", "position", "positioned",
    "connect", "connected", "enhance", "enhanced", "escape", "unwind",  "true", "truly", "best", "extra", "double", "multiple", "main",
    "central", "local", "nearby", "adjacent", "directly", "across",
    "around", "along", "behind", "back", "front", "next", "beyond",
    "without", "every", "everything", "much", "many", "plenty", "even",
    "yet", "short", "long", "huge", "dramatic", "grand", "premier",
    "premium", "smart", "strong", "active", "extensive", "usable",
    "versatile", "versatility", "functionality", "effortless",
    "timeless", "elegance", "vibrant", "iconic", "unique", "incredible",
    "wonderful", "fantastic", "excellent", "gorgeous", "impressive",
    "welcoming", "refined", "contemporary", "clean", "sleek", "warm",
    "airy", "lush", "scenic", "dream", "ultimate", "turnkey", "popular",
    "green", "white", "top", "right", "second", "future", "currently",
    "nearly", "approximately", "ideally", "look", "looking","buyer", "seller", "owner", "investor", "resident", "neighbor",
    "north", "south", "east", "west", "downtown", "village", "ha", "wa", "sf", "approx"
}

all_stopwords = stop_words.union(custom_stopwords)
lemmatizer = WordNetLemmatizer()


all_text = ' '.join(df['remarks'].dropna().str.lower())
all_text = all_text.replace('\u2019', "'")   # curly apostrophe, straight
all_text = re.sub(r'[\u2014\u2013\u2022]', ' ', all_text)  # em dash, en dash, bullet


all_text = re.sub(r"[^a-z0-9\s\-]", ' ', all_text)
all_text = re.sub(r'-{2,}', ' ', all_text)
all_text = re.sub(r"\s+", " ", all_text).strip()

tokens = nltk.word_tokenize(all_text)
tokens = [t for t in tokens if not t.isdigit()]

tokens = [t for t in tokens if t not in {"has", "was", "is", "are", "were", "be", "been", "am"}]

tokens = [lemmatizer.lemmatize(t) for t in tokens]
tokens = [t for t in tokens if t not in all_stopwords and len(t) > 1]


valid_ngrams = []
valid_ngrams.extend(tokens)

# adds list of bigrams to valid_ngrams
for gram in ngrams(tokens, 2):
        if gram[0] not in all_stopwords and gram[-1] not in all_stopwords:
            valid_ngrams.append(' '.join(gram))

# counts frequency of valid ngrams
freq = Counter(valid_ngrams)
absorb_ratio = 0.30
final = dict(freq)
bigrams = [t for t in freq if len(t.split()) == 2]
    
for bigram in bigrams:
    w1, w2 = bigram.split()
    bigram_count = freq[bigram]
    for w in (w1, w2):
        if w in final:
            # if most occurrences of this unigram come from this one bigram, drop it
            if bigram_count >= final[w] * absorb_ratio:
                del final[w]
# Build taxonomy from deduped, sorted results
taxonomy = {'terms': []}
sorted_final = sorted(final.items(), key=lambda x: -x[1])
for term, count in sorted_final[:500]:
    taxonomy['terms'].append({
        'id': f"term_{len(taxonomy['terms'])}",
        'term': term,
        'count': count
    })

with open('data/processed/taxonomy.json', 'w') as f:
    print(f"Success — wrote {len(taxonomy['terms'])} terms")

    json.dump(taxonomy, f, indent=2)
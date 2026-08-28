import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.util import ngrams

try:
    from scripts.text_cleaning import TextCleaner
except ImportError:
    class TextCleaner:
        """Fallback cleaner if scripts.text_cleaning is unavailable."""

        def clean_text(self, text: str) -> str:
            text = re.sub(r"https?://\S+|www\.\S+", " ", text)
            text = re.sub(r"[^a-zA-Z0-9\-\s]", " ", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
INPUT_CSV = Path("data/processed/listing_sample.csv")
OUTPUT_JSON = Path("data/processed/taxonomy.json")
CANDIDATES_CSV = Path("data/processed/taxonomy_candidates.csv")

REMARKS_COLUMN = "remarks"
MAX_TERMS = 300
MIN_TERM_COUNT = 2
ABSORB_RATIO = 0.40

CATEGORIES = [
    "property_type",
    "interior",
    "kitchen",
    "exterior",
    "amenities",
    "location",
    "condition",
    "views_environment",
]


# Keep marketing/filler terms out, but preserve useful real-estate concepts
CUSTOM_STOPWORDS = {
    "home", "house", "property", "features", "feature",
    "great", "beautiful", "amazing", "stunning", "lovely",
    "close", "recently", "located", "offers", "boasts",
    "perfect", "ideal", "spacious", "nice", "well",
    "entertaining", "simply", "elegant", "modern", "classic",
    "charming", "inviting", "rare", "opportunity", "resort",
    "style", "conveniently", "sqft", "sq", "ft", "feet",
    "highlights", "whether", "highly", "desirable", "enjoy",
    "comfort", "convenience", "miss", "peaceful", "tranquil",
    "serene", "breathtaking", "panoramic", "spectacular",
    "unparalleled", "exclusive", "prestigious", "coveted", "prime",
    "exceptional", "unmatched", "unrivaled", "unbeatable",
    "appeal", "quiet", "beautifully", "tastefully", "meticulously",
    "exquisite", "luxurious", "must-see", "must-have", "include",
    "offer", "easy", "thoughtfully", "designed", "crafted", "ft.",
    "step", "throughout", "cozy", "includes", "including", "ample",
    "foot", "flexible", "freshly", "fresh", "abundant", "nature",
    "blend", "retreat", "seamlessly", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "zero", "special", "create",
    "perfectly", "flexibility", "effortlessly", "generous", "expansive",
    "natural", "ready", "situated", "convenient", "nestled", "seamless",
    "heart", "complete", "completely", "customized", "custom-built",
    "custom-designed", "custom-crafted", "minutes", "paint", "large",
    "bright", "find", "away", "tucked", "featuring", "flows",
    "dedicated", "everyday", "areas", "separate", "schedule", "within",
    "additional", "peace", "generously", "plan", "ownership", "minute",
    "provides", "space", "area", "location", "setting", "moment",
    "point", "line", "side", "end", "block", "spot", "detail", "value",
    "quality", "size", "option", "sense", "vision", "character",
    "atmosphere", "experience", "lifestyle", "living", "life", "time",
    "day", "night", "year", "today", "mind", "gem", "beauty", "charm",
    "art", "market", "cost", "price", "sale", "use", "connection",
    "combination", "welcome", "boast", "showcase", "creating", "creates",
    "provide", "providing", "deliver", "delivers", "add", "added", "make",
    "making", "bring", "take", "come", "sit", "sits", "want", "need",
    "used", "lead", "capture", "combine", "complement", "complemented",
    "highlight", "surround", "surrounded", "install", "installed", "painted",
    "position", "positioned", "connect", "connected", "enhance", "enhanced",
    "escape", "unwind", "true", "truly", "best", "extra", "double",
    "multiple", "main", "central", "local", "nearby", "adjacent", "directly",
    "across", "around", "along", "behind", "back", "front", "next", "beyond",
    "without", "every", "everything", "much", "many", "plenty", "even", "yet",
    "short", "long", "huge", "dramatic", "grand", "premier", "premium",
    "strong", "active", "extensive", "usable", "versatile", "versatility",
    "functionality", "effortless", "timeless", "elegance", "vibrant", "iconic",
    "unique", "incredible", "wonderful", "fantastic", "excellent", "gorgeous",
    "impressive", "welcoming", "refined", "contemporary", "clean", "sleek",
    "warm", "airy", "lush", "scenic", "dream", "ultimate", "turnkey",
    "popular", "white", "top", "right", "second", "future", "currently",
    "nearly", "approximately", "ideally", "look", "looking", "buyer", "seller",
    "owner", "investor", "resident", "neighbor", "ha", "wa", "sf", "approx",
    "see", "also", "plus",
}

# Keyword hints used to categorize extracted terms.
# Multiword phrases are supported because matching uses token/substring checks.
CATEGORY_HINTS = {
    "property_type": {
        "condo", "condominium", "townhome", "townhouse", "villa", "bungalow",
        "ranch", "duplex", "triplex", "fourplex", "apartment", "loft", "cottage",
        "estate", "farmhouse", "detached", "single family", "multi family",
        "manufactured", "mobile home", "penthouse", "cabin",
    },
    "interior": {
        "bedroom", "bathroom", "bath", "fireplace", "flooring", "hardwood",
        "tile", "carpet", "vaulted ceiling", "ceiling", "walk in closet", "closet",
        "office", "den", "bonus room", "family room", "living room", "dining room",
        "laundry", "basement", "attic", "open concept", "open floor plan",
        "skylight", "built in", "crown molding",
    },
    "kitchen": {
        "kitchen", "countertop", "granite", "quartz", "island", "pantry",
        "cabinet", "cabinetry", "stainless steel", "appliance", "dishwasher",
        "range", "oven", "microwave", "refrigerator", "breakfast bar",
        "breakfast nook", "backsplash", "gas stove", "chef kitchen",
    },
    "exterior": {
        "garage", "carport", "driveway", "patio", "deck", "porch", "balcony",
        "yard", "backyard", "front yard", "fence", "fenced", "roof", "siding",
        "stucco", "brick", "lot", "acre", "acreage", "landscaping", "garden",
        "sprinkler", "terrace", "courtyard", "outdoor kitchen",
    },
    "amenities": {
        "pool", "spa", "hot tub", "gym", "fitness", "clubhouse", "tennis",
        "pickleball", "golf", "playground", "security", "gated", "elevator",
        "doorman", "concierge", "hoa", "community pool", "solar", "ev charger",
        "charging", "smart home", "theater", "media room",
    },
    "location": {
        "downtown", "school", "district", "transit", "metro", "subway", "station",
        "freeway", "highway", "airport", "shopping", "restaurant", "park",
        "trail", "beach", "waterfront", "lakefront", "riverfront", "cul de sac",
        "corner lot", "walkable", "walking distance", "commute", "university",
    },
    "condition": {
        "renovated", "remodeled", "updated", "upgrade", "upgraded", "new construction",
        "newly built", "restored", "refinished", "replacement", "new roof",
        "new hvac", "new windows", "move in ready", "fixer", "fixer upper",
        "well maintained", "original condition",
    },
    "views_environment": {
        "view", "views", "ocean", "mountain", "lake", "river", "water",
        "city view", "ocean view", "mountain view", "lake view", "sunset",
        "sunrise", "trees", "wooded", "forest", "greenbelt", "green space",
        "park view", "golf course view", "water view",
    },
}


# -----------------------------------------------------------------------------
# NLTK helpers
# -----------------------------------------------------------------------------
def ensure_nltk_resource(resource_path: str, download_name: str) -> None:
    try:
        nltk.data.find(resource_path)
    except LookupError:
        nltk.download(download_name, quiet=True)


def initialize_nltk() -> None:
    ensure_nltk_resource("corpora/stopwords", "stopwords")
    ensure_nltk_resource("corpora/wordnet", "wordnet")
    ensure_nltk_resource("tokenizers/punkt", "punkt")
    # Newer NLTK versions can require punkt_tab.
    try:
        ensure_nltk_resource("tokenizers/punkt_tab", "punkt_tab")
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Extraction
# -----------------------------------------------------------------------------
def normalize_term(term: str) -> str:
    term = term.lower().strip()
    term = re.sub(r"\s+", " ", term)
    return term


def process_remark(text: str, cleaner, lemmatizer, all_stopwords) -> list[str]:
    text = cleaner.clean_text(str(text).lower())
    raw_tokens = nltk.word_tokenize(text)

    tokens = []
    for token in raw_tokens:
        token = normalize_term(token)

        if not token or token.isdigit():
            continue
        if token in {"has", "was", "is", "are", "were", "be", "been", "am"}:
            continue
        if token in all_stopwords:
            continue
        if len(token) <= 1:
            continue
        if not re.search(r"[a-z]", token):
            continue

        lemma = lemmatizer.lemmatize(token)
        if lemma not in all_stopwords and len(lemma) > 1:
            tokens.append(lemma)

    terms = list(tokens)

    # Generate bigrams within each remark only.
    for gram in ngrams(tokens, 2):
        if gram[0] not in all_stopwords and gram[-1] not in all_stopwords:
            terms.append(" ".join(gram))

    return terms


def extract_candidate_frequencies(df: pd.DataFrame) -> Counter:
    cleaner = TextCleaner()
    lemmatizer = WordNetLemmatizer()
    all_stopwords = set(stopwords.words("english")).union(CUSTOM_STOPWORDS)

    all_terms = []
    for remark in df[REMARKS_COLUMN].dropna():
        all_terms.extend(process_remark(remark, cleaner, lemmatizer, all_stopwords))

    freq = Counter(all_terms)

    # Remove very rare terms.
    freq = Counter({term: count for term, count in freq.items() if count >= MIN_TERM_COUNT})

    # If a unigram is mostly explained by one dominant bigram, suppress the unigram.
    final = dict(freq)
    bigrams = [term for term in freq if len(term.split()) == 2]

    for bigram in bigrams:
        w1, w2 = bigram.split()
        bigram_count = freq[bigram]

        for word in (w1, w2):
            if word in final and bigram_count >= final[word] * ABSORB_RATIO:
                del final[word]

    return Counter(final)


# -----------------------------------------------------------------------------
# Categorization
# -----------------------------------------------------------------------------
def hint_score(term: str, hints: set[str]) -> int:
    score = 0
    term_tokens = set(term.split())

    for hint in hints:
        hint = normalize_term(hint)
        if term == hint:
            score += 10
        elif " " in hint and hint in term:
            score += 7
        elif hint in term_tokens:
            score += 5
        elif term in hint:
            score += 2

    return score


def categorize_term(term: str) -> str | None:
    scores = {
        category: hint_score(term, hints)
        for category, hints in CATEGORY_HINTS.items()
    }

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        return None

    return best_category


def build_taxonomy(freq: Counter) -> tuple[dict, pd.DataFrame]:
    sorted_terms = sorted(freq.items(), key=lambda item: (-item[1], item[0]))

    categorized = defaultdict(list)
    candidate_rows = []

    for term, count in sorted_terms:
        category = categorize_term(term)
        candidate_rows.append({
            "term": term,
            "count": count,
            "category": category or "unassigned",
        })

        if category and sum(len(v) for v in categorized.values()) < MAX_TERMS:
            categorized[category].append((term, count))

    # If heuristic matching gives too few terms, fill categories from strong
    # domain seeds that actually appear in the corpus.
    for category, hints in CATEGORY_HINTS.items():
        existing = {term for term, _ in categorized[category]}
        for hint in sorted(hints):
            hint = normalize_term(hint)
            if hint in freq and hint not in existing:
                categorized[category].append((hint, freq[hint]))
                existing.add(hint)

    taxonomy = {
        "metadata": {
            "source": str(INPUT_CSV),
            "remarks_column": REMARKS_COLUMN,
            "category_count": len(CATEGORIES),
            "term_count": 0,
        },
        "categories": {},
    }

    total = 0
    for category in CATEGORIES:
        entries = []
        seen = set()

        for term, count in sorted(categorized[category], key=lambda x: (-x[1], x[0])):
            if term in seen:
                continue
            seen.add(term)

            entries.append({
                "id": f"{category}_{len(entries) + 1:03d}",
                "term": term,
                "count": int(count),
                "aliases": [],
            })
            total += 1

        taxonomy["categories"][category] = entries

    taxonomy["metadata"]["term_count"] = total

    candidates_df = pd.DataFrame(candidate_rows)
    return taxonomy, candidates_df


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> None:
    initialize_nltk()

    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_CSV}. Update INPUT_CSV or place your listing sample there."
        )

    df = pd.read_csv(INPUT_CSV)

    if REMARKS_COLUMN not in df.columns:
        raise ValueError(
            f"Expected a '{REMARKS_COLUMN}' column. Found columns: {list(df.columns)}"
        )

    freq = extract_candidate_frequencies(df)
    taxonomy, candidates_df = build_taxonomy(freq)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(taxonomy, f, indent=2, ensure_ascii=False)

    candidates_df.to_csv(CANDIDATES_CSV, index=False)

    print(f"Wrote taxonomy: {OUTPUT_JSON}")
    print(f"Wrote candidates: {CANDIDATES_CSV}")
    print(f"Categories: {taxonomy['metadata']['category_count']}")
    print(f"Taxonomy terms: {taxonomy['metadata']['term_count']}")

    for category in CATEGORIES:
        print(f"  {category}: {len(taxonomy['categories'][category])}")

    if taxonomy["metadata"]["term_count"] < 200:
        print(
            "WARNING: Fewer than 200 categorized terms were found. "
            "Review taxonomy_candidates.csv and expand CATEGORY_HINTS or lower MIN_TERM_COUNT."
        )


if __name__ == "__main__":
    main()

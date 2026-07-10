from email.mime import text
import re
import pandas as pd
import nltk
import unicodedata

class TextCleaner:
    def __init__(self):
        self.abbrev_map = {
            'br': 'bedroom', 'ba': 'bathroom', 'ba': 'bath', 'br': 'bed', 'lr': 'living room', 'sqft': 'square feet', 'sq ft': 'square feet', 'sq. ft.': 'square feet', 'sq. ft': 'square feet',
            'sf': 'square feet','w/o': 'without', 'w/': 'with', 'primary suite': 'master bedroom', 'mbr': 'master bedroom', 'condo': 'condominium', 'ft': 'feet', 'mi': 'mile', 'yd': 'yard', 
            'ac': 'air conditioning', 'a/c': 'air conditioning', 'hoa': 'homeowners association', 'th': 'townhouse', 'co-op': 'cooperative', 'coop': 'cooperative', 
            'bldg': 'building', 'flr': 'floor', 'lvl': 'level', 'apt.': 'apartment', 'apt': 'apartment', 'blvd': 'boulevard', 'ave': 'avenue', 'st': 'street','one:':'1', 
            'two':'2', 'three':'3', 'four':'4', 'five':'5', 'six':'6', 'seven':'7','eight':'8', 'nine':'9', '@': ''
        }

    def clean_text(self, text):
        text = self.normalize_unicode(text)
        text = self.normalize_prices(text)
        text = self.normalize_measurements(text)
        text = self.lowercase_text(text)
        text = self.remove_html_tags(text)
        text = self.normalize_url(text)
        text = self.normalize_email(text)
        text = self.normalize_brackets(text)
        text = self.remove_punctuation(text)
        text = self.expand_abbreviations(text)
        return text.strip()
    def normalize_unicode(self, text):
        # Normalize unicode characters to ASCII
        return  unicodedata.normalize("NFKC", text)
    def normalize_prices(self, text):
        # 450k → 450000
        text = re.sub(r'(\d+)k', lambda m: str(int(m.group(1))*1000), text,
        flags=re.I)
        # 1.2m → 1200000
        text = re.sub(r'(\d+\.?\d*)m', lambda m:
        str(int(float(m.group(1))*1000000)), text, flags=re.I)
        return text
    def normalize_measurements(self, text):
        # 1,500 sqft → 1500 sqft
        text = re.sub(r'(\d+),(\d+)', r'\1\2', text)
        return text
    def lowercase_text(self, text):
        return text.lower()
    def remove_html_tags(self, text):
        # Remove HTML tags
        return re.sub(r'<.*?>', '', text)
    def normalize_url(self, text):
        # Remove URLs
        return re.sub(r'http\S+|www\S+|https\S+', '<URL>', text, flags=re.MULTILINE)
    def normalize_email(self, text):
        # Remove email addresses
        return re.sub(r'\S+@\S+', '<EMAIL>', text)
    def expand_abbreviations(self, text):
        # special cases first
        text = re.sub(r'(?<!\w)w/\s*', 'with ', text, flags=re.I)
        text = re.sub(r'(?<!\w)w/o\s*', 'without ', text, flags=re.I)

        # general abbreviations
        for abbrev, full in sorted(self.abbrev_map.items(), key=lambda x: len(x[0]), reverse=True):
            pattern = r'(?<!\w)' + re.escape(abbrev) + r'(?!\w)'
            text = re.sub(pattern, full, text, flags=re.I)

        return re.sub(r'\s+', ' ', text).strip()
    
    def normalize_brackets(self, text):
        text = text.replace('\u2019', "'")   # curly apostrophe -> straight
        text = re.sub(r'[\u2014\u2013\u2022]', ' ', text)
        return text
    
    def remove_punctuation(self, text):
        text = re.sub(r"[^a-z0-9\s\-]", ' ', text)
        return re.sub(r"\s+", " ", text).strip()


    def profile_column(self, df, column_name):
        # Analyze what's actually in L_Remarks
        return {
            'null_rate': df[column_name].isnull().mean(),
            'avg_length': df[column_name].str.len().mean(),
            'common_terms': self._extract_top_ngrams(df[column_name]),
            'price_mentions': df[column_name].str.contains(r'\$\d').sum(),
            'has_html': df[column_name].str.contains('<').sum(),
            'common_abbreviations': self._detect_abbreviations(df[column_name])
        }
    
    def _extract_top_ngrams(self, series, n=2, top_k=200):
        all_text = ' '.join(series.dropna().str.lower())
        tokens = nltk.word_tokenize(all_text)
        ngrams_list = list(nltk.ngrams(tokens, n))
        freq_dist = nltk.Counter(ngrams_list)
        return freq_dist.most_common(top_k)
    
    def _detect_abbreviations(self, series):
        abbrev_pattern = (
        r'(?<!\w)('
        + '|'.join(
            re.escape(a)
            for a in sorted(self.abbrev_map, key=len, reverse=True)
        )
        + r')(?!\w)'
)
        all_text = ' '.join(series.dropna().str.lower())
        found_abbrevs = re.findall(abbrev_pattern, all_text)
        return list(set(found_abbrevs))
# Use this to guide your cleaning strategy:
cleaner = TextCleaner()
df = pd.read_csv('data/processed/listing_sample.csv')
profile = cleaner.profile_column(df, 'remarks')
print("Original Remarks:")
print(f"Null rate: {profile['null_rate']}")
print(f"Common abbreviations: {profile['common_abbreviations']}")
print(f"Price mentions: {profile['price_mentions']}")
print(f"Has HTML: {profile['has_html']}")

df_cleaned = pd.read_csv('data/processed/cleaned_listing_sample.csv')
cleaned_profile = cleaner.profile_column(df_cleaned, 'cleaned_remarks')
print("\nCleaned Remarks:")
print(f"Null rate: {cleaned_profile['null_rate']}")
print(f"Common abbreviations: {cleaned_profile['common_abbreviations']}")
print(f"Price mentions: {cleaned_profile['price_mentions']}")
print(f"Has HTML: {cleaned_profile['has_html']}")

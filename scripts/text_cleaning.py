from email.mime import text
import re
import pandas as pd
import nltk
import unicodedata

class TextCleaner:
    def __init__(self):
        self.abbrev_map = {
            'br': 'bedroom', 'ba': 'bathroom', 'sqft': 'square feet', 'sq ft': 'square feet', 'sq. ft.': 'square feet', 'sq. ft': 'square feet',
            'w/o': 'without', 'w/': 'with', 'mbr': 'master bedroom'
        }
    def clean_text(self, text):
        text = self.normalize_unicode(text)
        text = self.normalize_prices(text)
        text = self.normalize_measurements(text)
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
    def expand_abbreviations(self, text):
        # special cases first
        text = re.sub(r'(?<!\w)w/\s*', 'with ', text, flags=re.I)
        text = re.sub(r'(?<!\w)w/o\s*', 'without ', text, flags=re.I)

        # general abbreviations
        for abbrev, full in sorted(self.abbrev_map.items(), key=lambda x: len(x[0]), reverse=True):
            pattern = r'(?<!\w)' + re.escape(abbrev) + r'(?!\w)'
            text = re.sub(pattern, full, text, flags=re.I)

        return re.sub(r'\s+', ' ', text).strip()

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
print(f"Null rate: {profile['null_rate']}")
print(f"Common abbreviations: {profile['common_abbreviations']}")
print(f"Price mentions: {profile['price_mentions']}")
print(f"Has HTML: {profile['has_html']}")
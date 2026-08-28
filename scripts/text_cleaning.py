import re
import unicodedata
from collections import Counter

import nltk
import pandas as pd


class TextCleaner:

    def __init__(self):

        self.abbrev_map = {
            # Bedrooms / bathrooms
            "bath": "bathroom",
            "baths": "bathroom",
            "bedrooms": "bedroom",
            "beds": "bedroom",
            "bed": "bedroom",
            "br": "bedroom",
            "bd": "bedroom",
            "ba": "bathroom",
            "mbr": "master bedroom",

            # Rooms
            "lr": "living room",

            # Measurements
            "sqft": "square feet",
            "sq ft": "square feet",
            "sq. ft.": "square feet",
            "sq. ft": "square feet",
            "sf": "square feet",
            "ft": "feet",
            "mi": "mile",
            "yd": "yard",

            # Property types
            "condo": "condominium",
            "th": "townhouse",
            "co-op": "cooperative",
            "coop": "cooperative",
            "apt": "apartment",
            "apt.": "apartment",

            # Amenities / systems
            "ac": "air conditioning",
            "a/c": "air conditioning",
            "hoa": "homeowners association",

            # Building terms
            "bldg": "building",
            "flr": "floor",
            "lvl": "level",

            # Address terms
            "blvd": "boulevard",
            "ave": "avenue",
            "st": "street",

            # Numbers
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8",
            "nine": "9"
        }

    def clean_text(self, text):

        if pd.isna(text):
            return ""

        text = str(text)

        text = self.normalize_unicode(text)
        text = self.normalize_prices(text)
        text = self.normalize_measurements(text)
        text = self.lowercase_text(text)
        text = self.remove_html_tags(text)
        text = self.normalize_url(text)
        text = self.normalize_email(text)
        text = self.normalize_brackets(text)
        text = self.expand_abbreviations(text)
        text = self.remove_punctuation(text)
        text = self.normalize_whitespace(text)

        return text.strip()

    def normalize_unicode(self, text):
        return unicodedata.normalize("NFKC", text)

    def normalize_prices(self, text):
        """
        450k -> 450000
        1.2m -> 1200000
        """

        text = re.sub(
            r"\b(\d+(?:\.\d+)?)k\b",
            lambda m: str(
                int(float(m.group(1)) * 1_000)
            ),
            text,
            flags=re.I
        )

        text = re.sub(
            r"\b(\d+(?:\.\d+)?)m\b",
            lambda m: str(
                int(float(m.group(1)) * 1_000_000)
            ),
            text,
            flags=re.I
        )

        return text

    def normalize_measurements(self, text):
        """
        1,500 -> 1500
        1,250,000 -> 1250000
        """

        return re.sub(
            r"(?<=\d),(?=\d)",
            "",
            text
        )

    def lowercase_text(self, text):
        return text.lower()

    def remove_html_tags(self, text):
        return re.sub(
            r"<[^>]+>",
            " ",
            text
        )

    def normalize_url(self, text):
        return re.sub(
            r"https?://\S+|www\.\S+",
            " url ",
            text,
            flags=re.I
        )

    def normalize_email(self, text):
        return re.sub(
            r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b",
            " email ",
            text
        )

    def normalize_brackets(self, text):

        text = text.replace("\u2019", "'")
        text = text.replace("\u2018", "'")
        text = text.replace("\u201c", '"')
        text = text.replace("\u201d", '"')

        text = re.sub(
            r"[\u2014\u2013\u2022]",
            " ",
            text
        )

        return text

    def expand_abbreviations(self, text):

        # Special cases first
        text = re.sub(
            r"(?<!\w)w/o(?!\w)",
            "without",
            text,
            flags=re.I
        )

        text = re.sub(
            r"(?<!\w)w/(?!\w)",
            "with",
            text,
            flags=re.I
        )

        # General abbreviation mappings
        for abbrev, full in sorted(
            self.abbrev_map.items(),
            key=lambda x: len(x[0]),
            reverse=True
        ):

            pattern = (
                r"(?<!\w)"
                + re.escape(abbrev)
                + r"(?!\w)"
            )

            text = re.sub(
                pattern,
                full,
                text,
                flags=re.I
            )

        return text

    def remove_punctuation(self, text):
        """
        Retain letters, numbers, spaces and hyphens.
        """

        return re.sub(
            r"[^a-z0-9\s\-]",
            " ",
            text
        )

    def normalize_whitespace(self, text):
        return re.sub(
            r"\s+",
            " ",
            text
        ).strip()

    def profile_column(self, df, column_name):

        series = df[column_name]

        return {
            "row_count": len(series),

            "null_count": int(
                series.isnull().sum()
            ),

            "null_rate": float(
                series.isnull().mean()
            ),

            "avg_length": float(
                series.dropna()
                .astype(str)
                .str.len()
                .mean()
            ),

            "common_terms":
                self._extract_top_ngrams(series),

            "price_mentions": int(
                series.fillna("")
                .astype(str)
                .str.contains(
                    r"\$\s*\d",
                    regex=True,
                    na=False
                )
                .sum()
            ),

            "has_html": int(
                series.fillna("")
                .astype(str)
                .str.contains(
                    r"<[^>]+>",
                    regex=True,
                    na=False
                )
                .sum()
            ),

            "url_mentions": int(
                series.fillna("")
                .astype(str)
                .str.contains(
                    r"https?://|www\.",
                    regex=True,
                    case=False,
                    na=False
                )
                .sum()
            ),

            "email_mentions": int(
                series.fillna("")
                .astype(str)
                .str.contains(
                    r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}",
                    regex=True,
                    na=False
                )
                .sum()
            ),

            "common_abbreviations":
                self._detect_abbreviations(series)
        }

    def _extract_top_ngrams(
        self,
        series,
        n=2,
        top_k=200
    ):

        all_text = " ".join(
            series
            .dropna()
            .astype(str)
            .str.lower()
        )

        tokens = nltk.word_tokenize(all_text)

        ngrams_list = nltk.ngrams(
            tokens,
            n
        )

        freq_dist = Counter(
            ngrams_list
        )

        return freq_dist.most_common(
            top_k
        )

    def _detect_abbreviations(self, series):

        abbrev_pattern = (
            r"(?<!\w)("
            + "|".join(
                re.escape(a)
                for a in sorted(
                    self.abbrev_map,
                    key=len,
                    reverse=True
                )
            )
            + r")(?!\w)"
        )

        all_text = " ".join(
            series
            .dropna()
            .astype(str)
            .str.lower()
        )

        found_abbrevs = re.findall(
            abbrev_pattern,
            all_text
        )

        counts = Counter(
            a.lower()
            for a in found_abbrevs
        )

        return counts.most_common()
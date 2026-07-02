import re

class TextCleaner:
    def __init__(self):
        self.abbrev_map = {
            'br': 'bedroom', 'ba': 'bathroom', 'sqft': 'square feet',
            'w/': 'with', 'w/o': 'without', 'mbr': 'master bedroom'
        }
    def clean_text(self, text):
        text = self.normalize_unicode(text)
        text = self.normalize_prices(text)
        text = self.normalize_measurements(text)
        text = self.expand_abbreviations(text)
        return text.strip()
    def normalize_prices(self, text):
        # 450k → 450000
        text = re.sub(r'(\d+)k', lambda m: str(int(m.group(1))*1000), text,
        flags=re.I)
        # 1.2m → 1200000
        text = re.sub(r'(\d+\.?\d*)m', lambda m:
        str(int(float(m.group(1))*1000000)), text, flags=re.I)
        return text
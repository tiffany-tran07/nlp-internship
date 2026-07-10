import re
import json

class EntityExtractor:
    def __init__(self, taxonomy_path='data/processed/taxonomy.json'):
        with open(taxonomy_path, 'r') as f:
            taxonomy = json.load(f)
        # pre-compile a regex for each term once, at init — not per call
        self.amenity_patterns = [
            (term_obj['term'], re.compile(r'\b' + re.escape(term_obj['term']) + r'\b', re.I))
            for term_obj in taxonomy.get('terms', [])
        ]
    def extract_bedrooms(self, text):
        patterns = [
            r'(\d+)\s*(?:bedroom)s?',
            r'(\d+)bd'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return int(match.group(1))
        return None
    
    def extract_bathrooms(self, text):
        patterns = [
            r'(\d+)\s*(?:bathroom)s?',
            r'(\d+)ba'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return int(match.group(1))
        return None
    
    def extract_price(self, text):
    # Assumes cleaned text from Week 2
        match = re.search(r'\$?(\d{5,})', text)
        return int(match.group(1)) if match else None
    
    def extract_sqft(self, text):
        match = re.search(r'(\d{3,5})\s*(?:square feet)', text, re.I)
        return int(match.group(1)) if match else None
    
    def extract_amenities(self, text):
        amenities = []
        for term, pattern in self.amenity_patterns:
            if pattern.search(text):
                amenities.append(term)
        # if re.search(r'pool', text, re.I):
        #     amenities.append('pool')
        # if re.search(r'garage', text, re.I):
        #     amenities.append('garage')
        # if re.search(r'gym', text, re.I):
        #     amenities.append('gym')
        # if re.search(r'fireplace', text, re.I):
        #     amenities.append('fireplace')
        # if re.search(r'balcony', text, re.I):
        #     amenities.append('balcony')
        # if re.search(r'basement', text, re.I):
        #     amenities.append('basement')
        # if re.search(r'air conditioning', text, re.I):
        #     amenities.append('air conditioning')
        # if re.search(r'washer/dryer', text, re.I):
        #     amenities.append('washer/dryer')
        # if re.search(r'patio', text, re.I):
        #     amenities.append('patio')
        return amenities
    
    def extract_all(self, text):
        return {
            'bedrooms': self.extract_bedrooms(text),
            'bathrooms': self.extract_bathrooms(text),
            'price': self.extract_price(text),
            'sqft': self.extract_sqft(text),
            'amenities': self.extract_amenities(text)
        }
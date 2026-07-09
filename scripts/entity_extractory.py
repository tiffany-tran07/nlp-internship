import re
class EntityExtractor:
    def extract_bedrooms(self, text):
        patterns = [
            r'(\d+)\s*(?:bed|br|bedroom)s?',
            r'(\d+)bd'
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
    
    def extract_amenities(self, text):
        amenities = []
        if re.search(r'pool', text, re.I):
            amenities.append('pool')
        if re.search(r'garage', text, re.I):
            amenities.append('garage')
        if re.search(r'gym', text, re.I):
            amenities.append('gym')
        return amenities
    
    def extract_all(self, text):
        return {
            'bedrooms': self.extract_bedrooms(text),
            'bathrooms': self.extract_bathrooms(text),
            'price': self.extract_price(text),
            'sqft': self.extract_sqft(text),
            'amenities': self.extract_amenities(text)
        }
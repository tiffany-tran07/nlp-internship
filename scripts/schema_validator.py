import json

class SchemaValidator:
    def __init__(self, schema_path='data/schema.json'):
        with open(schema_path) as f:
            self.schema = json.load(f)
        self.valid_cities = self._load_valid_cities()
    def validate_query(self, filters):
        errors = []
        # Check city exists in database
        if 'city' in filters:
            if filters['city'] not in self.valid_cities:
                errors.append(f"City '{filters['city']}' not found in database")
                
        # Check price range
        if 'price_max' in filters:
            if filters['price_max'] < 100000 or filters['price_max'] >
            errors.append(f"Price {filters['price_max']} outside typical range")
        # Check bedroom count
        if 'bedrooms' in filters:
            if filters['bedrooms'] < 1 or filters['bedrooms'] > 10:
                errors.append(f"Bedroom count {filters['bedrooms']} seems invalid")
        return len(errors) == 0, errors
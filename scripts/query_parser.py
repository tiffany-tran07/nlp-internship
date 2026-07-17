import re

class QueryParser:
    def parse(self, query):
        filters = {}
        # Price patterns
        if match := re.search(r'under\s+\$?(\d+)([km]?)', query, re.I):
            filters['price_max'] = self._parse_number(match.group(1), match.group(2))
        # Bedroom patterns
        if match := re.search(r'(\d+)\+?\s*(?:bed|br)', query, re.I):
            filters['bedrooms_min' if '+' in match.group(0) else 'bedrooms'] = int(match.group(1))
        return filters
    def to_sql(self, filters):
        conditions = []
        params = []
        if 'price_max' in filters:
            conditions.append('L_SystemPrice <= %s')
        params.append(filters['price_max'])
        if 'bedrooms' in filters:
            conditions.append('L_Keyword2 = %s')
        params.append(filters['bedrooms'])
        where_clause = ' AND '.join(conditions)
        return f"SELECT * FROM rets_property WHERE {where_clause}", params
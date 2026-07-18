import re

class QueryParser:
    def _parse_number(self, digits, letter):
        value = float(digits.replace(',', ''))
        if letter == 'k':
            return int(value)*1000
        elif letter == 'm':
            return int(value)*1000000
        return value

    def parse(self, query):
        filters = {}
        # Price patterns
        if match := re.search(r'under\s+\$?([\d,]+(?:\.\d+)?)([km]?)', query, re.I):
            filters['price_max'] = self._parse_number(match.group(1), match.group(2))

        if match := re.search(r'over\s+\$?([\d,]+(?:\.\d+)?)([km]?)', query, re.I):
            filters['price_min'] = self._parse_number(match.group(1), match.group(2))
        # Bedroom patterns
        if match := re.search(r'(\d+)\+?\s*(?:bed|br)', query, re.I):
            filters['bedrooms_min' if '+' in match.group(0) else 'bedrooms'] = int(match.group(1))
        # city patterns
        city_pattern = re.compile(
            r'(?i:\bin\s+(?:the\s+)?)'                     # "in [the]" matched case-insensitively
            r"([A-Z][a-zA-Z\.\-']*(?:\s+[A-Z][a-zA-Z\.\-']*)*)"  # capitalized word(s) — case-SENSITIVE
            r'(?:\s+area|\s+region)?'                       # optional trailing filler, discarded
            r'(?i:(?=\s+under|\s+with|\s+at|\s+that|\s+which|\s+near|,|$))'
        ).search(query)
        if city_pattern:
            filters['city'] = city_pattern.group(1).strip()
        return filters

    def to_sql(self, filters):
        conditions = []
        params = []

        if 'price_max' in filters:
            conditions.append('L_SystemPrice <= %s')
            params.append(filters['price_max'])

        if 'price_min' in filters:
            conditions.append('L_SystemPrice >= %s')       # was '<=' — bug
            params.append(filters['price_min'])

        if 'bedrooms' in filters:
            conditions.append('L_Keyword2 = %s')
            params.append(filters['bedrooms'])

        if 'bedrooms_min' in filters:
            conditions.append('L_Keyword2 >= %s')
            params.append(filters['bedrooms_min'])

        if 'city' in filters:
            conditions.append('L_City = %s')
            params.append(filters['city'])

        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        return f"SELECT * FROM rets_property WHERE {where_clause}", params


if __name__ == '__main__':
    p = QueryParser()
    tests = [
        "3 bed 2 bath under 700k in Irvine with a pool and garage",
        "4 bed 3 bath over 600k in Sacramento with solar panels",
        "1 bed in San Francisco near transit",
        "4+ bed under 900k in Fremont",
    ]
    for q in tests:
        filters = p.parse(q)
        sql, params = p.to_sql(filters)
        print(q)
        print(' filters:', filters)
        print(' sql:    ', sql)
        print(' params: ', params)
        print()
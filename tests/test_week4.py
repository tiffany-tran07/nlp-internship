from scripts.query_parser import QueryParser
from scripts.schema_validator import SchemaValidator

parser = QueryParser()
validator = SchemaValidator()
filters = parser.parse("3 bed in Portland under 500k")
valid, errors = validator.validate_query(filters)
if not valid:
    print(f"Query validation errors: {errors}")
# Return helpful message to user
else:
    sql, params = parser.to_sql(filters)
    print(params)
    print(sql)
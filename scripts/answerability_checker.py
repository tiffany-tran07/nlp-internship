class AnswerabilityChecker:
    def __init__(self, taxonomy, schema_validator):
        self.taxonomy = taxonomy
        self.validator = schema_validator
        self.real_estate_keywords = ['house', 'home', 'bed', 'bath','property',
        'listing', 'price', 'sqft', 'pool','garage']
    def check_pre_query(self, query):
        """Check BEFORE generating SQL"""
        query_lower = query.lower()
        # Check 1: Is this a real estate question?
        has_re_terms = any(kw in query_lower for kw in
        self.real_estate_keywords)
        if not has_re_terms:
            return False, "This doesn't appear to be a real estate question"
        # Check 2: Does query reference valid data?
        # (Use Week 4's schema validator)
        filters = parser.parse(query)
        valid, errors = self.validator.validate_query(filters)
        if not valid:
            return False, f"Query references invalid data: {'; '.join(errors)}"
        return True, "Query is answerable"
    def check_post_query(self, query, results_df):
        """Check AFTER executing SQL"""
        if len(results_df) == 0:
            return False, "No listings match your criteria"
        # Check for all-null results
        if results_df.isnull().all().all():
            return False, "Query returned no meaningful data"
        return True, "Results found"
# Usage:
checker = AnswerabilityChecker(taxonomy, validator)
can_answer, message = checker.check_pre_query(user_query)
if not can_answer:
    return {"error": message, "answerable": False}
# Execute query...
results = execute_query(sql)
can_answer, message = checker.check_post_query(user_query, results)
if not can_answer:
    return {"message": message, "results": []}
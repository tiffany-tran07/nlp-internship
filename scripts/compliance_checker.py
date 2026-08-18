class ComplianceChecker:
    def __init__(self):
        self.prohibited_patterns = {
            'familial': ['no children', 'adults only', 'perfect for singles'],
            'disability': ['no wheelchairs', 'must be able-bodied'],
            'race': ['white neighborhood', 'ethnic', 'diverse area'],
            'religion': ['christian community', 'jewish neighborhood']
        }
    def check_listing(self, text):
        violations = []
        text_lower = text.lower()
        for category, patterns in self.prohibited_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    violations.append({
                        'category': category,
                        'pattern': pattern,
                        'severity': 'error',
                        'message': f'Prohibited language: {pattern} (Fair
                        Housing violation)'
                    })
    return {'compliant': len(violations) == 0, 'violations': violations}
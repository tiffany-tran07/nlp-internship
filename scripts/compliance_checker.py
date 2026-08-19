class ComplianceChecker:
    def __init__(self):
        self.prohibited_patterns = {
            'familial': ['no children', 'adults only', 'perfect for singles', 'family-friendly', 'child-free', 'no kids allowed', 
                         'ideal for couples', 'not suitable for families', 'family-oriented', 'child-friendly', 'kid-free', 
                         'no minors', 'adults preferred', 'family restrictions apply'],
            'disability': ['no wheelchairs', 'must be able-bodied', 'disabled access not available'],
            'race': ['white neighborhood', 'ethnic', 'diverse area', 
                'no minorities', 'black community', 'asian enclave', 'hispanic', 'latino', 'african american', 'caucasian', 'indigenous', 'native american', 'pacific islander', 'middle eastern', 'arabic', 'european',
                'african', 'afro-american', 'afro-caribbean', 'mixed race', 'multiracial', 'biracial', 'mestizo', 'mulatto', 'creole', 'mestiza', 'mulatta', 'mestizo/a', 'mulatto/a', 'mestizaje', 'mulataje', 'mestizaje/a', 'mulataje/a'],
            'religion': ['christian community', 'jewish neighborhood', 'buddhist temple nearby', 'mosque', 'church', 
                         'synagogue', 'jewish', 'muslim', 'hindu', 'sikh', 'atheist', 'agnostic', 'catholic', 'protestant', 
                         'evangelical', 'orthodox', 'baptist', 'methodist', 'lutheran', 'presbyterian', 'pentecostal', 
                         'secular', 'spiritual', 'agnostic', 'non-religious', 'faith-based', 'interfaith',],
            'sexual orientation': ['gay-friendly', 'lesbian-friendly', 'lgbtq+', 'queer-friendly', 'straight-friendly', 'heterosexual', 'bisexual', 'transgender', 'pansexual', 'asexual', 'non-binary', 'genderqueer', 'genderfluid', 'gender non-conforming']
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
                        'message': f'Prohibited language: {pattern} (Fair Housing violation)'
                    })
        return {'compliant': len(violations) == 0, 'violations': violations}
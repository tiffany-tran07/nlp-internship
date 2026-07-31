import json
import re


class SignalExtractor:
    """
    Taxonomy format expected (matches your file):
    {
      "terms": [
        {"id": "term_0", "term": "room", "count": 1334},
        ...
      ]
    }
    This is a FLAT corpus vocabulary (unigrams/n-grams + document frequency) --
    it is NOT pre-categorized into amenities/condition/financing/location.

    Since the taxonomy itself carries no category labels, this class layers a
    manually curated CATEGORY_MAP on top, assigning a subset of the taxonomy's
    terms to each output bucket. Only terms that actually exist in the loaded
    taxonomy are used (so this stays in sync if the taxonomy file changes).
    Terms not present in CATEGORY_MAP are simply ignored / not returned.

    Review and edit CATEGORY_MAP -- this is domain judgment, not derived from
    the taxonomy file itself.
    """

    CATEGORY_MAP = {
        "amenities": [
            "pool", "pool spa", "garage", "2-car garage", "car garage", "attached 2-car",
            "fireplace", "room fireplace", "solar", "solar panel", "walk-in closet",
            "walk-in shower", "ceiling fan", "air conditioning", "recessed lighting",
            "vaulted ceiling", "soaking tub", "stainless steel", "steel appliance",
            "granite countertop", "quartz countertop", "washer dryer", "adu", "rv",
            "gated", "private balcony", "private patio", "private backyard",
            "covered patio", "en-suite", "ensuite", "bonus room", "custom cabinetry",
            "center island", "island", "french door", "sliding glass", "high ceiling",
            "soaring ceiling", "fitness center", "gym", "tennis court", "bbq",
            "clubhouse", "community pool", "dual vanity", "dual sink", "loft", "den",
            "studio", "formal dining", "family room", "laundry room", "driveway",
            "deck", "patio", "backyard", "yard", "garden", "courtyard", "fenced",
            "landscaped", "landscaping", "fruit tree", "spa-inspired",
        ],
        "condition_keywords": [
            "newer", "brand-new", "well-maintained", "maintained", "fully", "update",
            "upgrade", "custom", "finished", "energy efficiency", "historic",
            "light-filled", "improvement", "designer", "stylish", "thoughtful",
            "functional", "newly",
        ],
        "financing_terms": [
            "homeowner association", "investment", "rental", "long-term",
        ],
        "location_features": [
            "mountain", "mountain view", "beach", "coastal", "canyon", "hill",
            "valley", "lake", "desert", "freeway", "freeway access",
            "walking distance", "school", "neighborhood", "cul-de-sac",
            "golf course", "ocean view", "san diego", "los angeles", "california",
            "county", "city", "trail", "park", "gated community",
        ],
    }

    def __init__(self, taxonomy, entity_extractor):
        if isinstance(taxonomy, str):
            with open(taxonomy, 'r') as f:
                taxonomy = json.load(f)
        self.taxonomy = taxonomy
        self.extractor = entity_extractor

        self.term_counts = {t['term'].lower(): t['count'] for t in taxonomy.get('terms', [])}

        self._compiled = {
            category: self._compile_terms(terms)
            for category, terms in self.CATEGORY_MAP.items()
        }

    def _compile_terms(self, terms):
        compiled = []
        for term in terms:
            if term.lower() not in self.term_counts:
                continue
            escaped = re.escape(term.lower())
            escaped = escaped.replace(r'\ ', r'[\s-]+').replace(r'\-', r'[\s-]+')
            pattern = re.compile(rf'\b{escaped}\b', re.IGNORECASE)
            compiled.append((term, pattern))
        return compiled

    def extract_signals(self, listing_record):
        remarks = listing_record.get('L_Remarks', '')
        entities = self.extractor.extract_all(remarks)
        amenities = self._match_amenities(remarks)
        return {
            'listing_id': listing_record['L_ListingID'],
            'entities': entities,
            'amenities': amenities,
            'condition_keywords': self._extract_condition(remarks),
            'financing_terms': self._extract_financing(remarks),
            'location_features': self._extract_location(remarks)
        }

    def _match_category(self, remarks, category):
        if not remarks:
            return []
        return [term for term, pattern in self._compiled.get(category, [])
                if pattern.search(remarks)]

    def _match_amenities(self, remarks):
        return self._match_category(remarks, 'amenities')

    def _extract_condition(self, remarks):
        return self._match_category(remarks, 'condition_keywords')

    def _extract_financing(self, remarks):
        return self._match_category(remarks, 'financing_terms')

    def _extract_location(self, remarks):
        return self._match_category(remarks, 'location_features')
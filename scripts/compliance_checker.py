import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


EXCLUSION_TERMS = re.compile(
    r"\b(?:"
    r"only|no|without|avoid|exclude[sd]?|"
    r"reject(?:s|ed|ing)?|refuse[sd]?|"
    r"does\s+not\s+rent\s+to|"
    r"do\s+not\s+want|"
    r"will\s+not\s+(?:accept|rent\s+to)|"
    r"not\s+allowed|"
    r"fewest|very\s+few"
    r")\b",
    re.IGNORECASE,
)

PREFERENCE_TERMS = re.compile(
    r"\b(?:"
    r"prefer(?:s|red|ring)?|"
    r"preferred|"
    r"mostly|"
    r"ideal\s+for|"
    r"best\s+suited\s+for|"
    r"around\s+people\s+of\s+my\s+own"
    r")\b",
    re.IGNORECASE,
)

# These phrases discuss preventing discrimination rather than requesting it.
ANTI_DISCRIMINATION_CONTEXT = re.compile(
    r"\b(?:"
    r"without\s+discriminatory\s+screening|"
    r"without\s+discrimination|"
    r"avoid\s+discrimination|"
    r"prevent\s+discrimination|"
    r"stop\s+discrimination|"
    r"does\s+not\s+discriminate|"
    r"do\s+not\s+discriminate|"
    r"fair[\s-]+housing\s+resources?|"
    r"equal\s+housing\s+opportunity"
    r")\b",
    re.IGNORECASE,
)

PROTECTIVE_INTENT = re.compile(
    r"\b(?:"
    r"welcomes?|inclusive|accessible|"
    r"equal\s+opportunity|fair[\s-]+housing|"
    r"without\s+discrimination|"
    r"prevent\s+discrimination|"
    r"report\s+discrimination|"
    r"discrimination\s+complaint|"
    r"reasonable\s+accommodation|"
    r"assistance\s+animal"
    r")\b",
    re.IGNORECASE,
)

CLAUSE_BOUNDARY = re.compile(
    r"(?:[.!?;]+|\b(?:but|however|although|while)\b)",
    re.IGNORECASE,
)

PROTECTED_CLASS_PATTERNS = {
    "race": re.compile(
        r"\b(?:"
        r"white|black|asian|hispanic|latino|"
        r"race|racial|ethnic(?:ity)?|minorities"
        r")\b",
        re.IGNORECASE,
    ),
    "religion": re.compile(
        r"\b(?:"
        r"christian(?:s)?|jewish|jews?|"
        r"muslim(?:s)?|hindu(?:s)?|sikh(?:s)?|"
        r"catholic(?:s)?|religious|religion"
        r")\b",
        re.IGNORECASE,
    ),
    "familial_status": re.compile(
        r"\b(?:"
        r"adults?|"
        r"children|kids?|minors?|"
        r"famil(?:y|ies)|"
        r"single\s+mothers?|"
        r"pregnant\s+(?:women|tenants?|people)|"
        r"married\s+couples?|"
        r"unmarried\s+(?:couples?|tenants?)"
        r")\b",
        re.IGNORECASE,
    ),
    "disability": re.compile(
        r"\b(?:"
        r"disabilit(?:y|ies)|disabled|wheelchairs?|"
        r"wheelchair\s+users?|service[\s-]+animal\s+users?|"
        r"service\s+animals?|mental\s+disabilities"
        r")\b",
        re.IGNORECASE,
    ),
    "sex": re.compile(
        r"\b(?:men|women|male|female|sex)\b",
        re.IGNORECASE,
    ),
    "national_origin": re.compile(
        r"\b(?:"
        r"immigrants?|foreign[\s-]+born|"
        r"born\s+in\s+the\s+united\s+states|"
        r"born\s+abroad|"
        r"people\s+from\s+[a-z]+|"
        r"national\s+origin"
        r")\b",
        re.IGNORECASE,
    ),
    "sexual_orientation": re.compile(
        r"\b(?:"
        r"gay|lesbian|straight|heterosexual|"
        r"same[\s-]+sex\s+couples?|sexual\s+orientation"
        r")\b",
        re.IGNORECASE,
    ),
    "gender_identity": re.compile(
        r"\b(?:"
        r"transgender|trans\s+(?:people|tenants?|residents?)|"
        r"non[\s-]+binary|gender[\s-]+nonconforming|"
        r"gender\s+identity"
        r")\b",
        re.IGNORECASE,
    ),
}


class Severity(str, Enum):
    REVIEW = "review"
    ERROR = "error"


@dataclass(frozen=True)
class Rule:
    category: str
    expression: str
    message: str
    severity: Severity = Severity.REVIEW


class ComplianceChecker:
    def __init__(
        self,
        rules: Iterable[Rule] | None = None,
    ):
        self.rules = tuple(
            self._default_rules()
            if rules is None
            else rules
        )

        self._compiled_rules = tuple(
            (
                rule,
                re.compile(
                    rule.expression,
                    flags=re.IGNORECASE,
                ),
            )
            for rule in self.rules
        )

    @staticmethod
    def _normalize(text: str) -> str:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        text = unicodedata.normalize("NFKC", text)
        text = (
            text.replace("’", "'")
            .replace("–", "-")
            .replace("—", "-")
        )

        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _default_rules() -> list[Rule]:
        return [
            Rule(
                category="familial_status",
                expression=(
                    r"\b(?:"
                    r"no\s+(?:children|kids|minors)|"
                    r"adults?[\s-]+only|"
                    r"no\s+families"
                    r")\b"
                ),
                severity=Severity.ERROR,
                message=(
                    "Language may exclude applicants based on "
                    "familial status."
                ),
            ),
            Rule(
                category="familial_status",
                expression=(
                    r"\b(?:"
                    r"perfect\s+for\s+singles|"
                    r"ideal\s+for\s+couples|"
                    r"adults?\s+preferred|"
                    r"not\s+suitable\s+for\s+families|"
                    r"best\s+suited\s+to\s+mature\s+residents"
                    r")\b"
                ),
                severity=Severity.REVIEW,
                message=(
                    "Language may express a preference about "
                    "household composition."
                ),
            ),
            Rule(
                category="disability",
                expression=(
                    r"\b(?:"
                    r"no\s+wheelchairs?|"
                    r"must\s+be\s+able[\s-]+bodied|"
                    r"able[\s-]+bodied\s+(?:tenants?\s+)?only|"
                    r"wheelchair\s+users?\s+cannot\s+be\s+accommodated"
                    r")\b"
                ),
                severity=Severity.ERROR,
                message=(
                    "Language may exclude people based on disability."
                ),
            ),
            Rule(
                category="disability",
                expression=(
                    r"\bdisabled\s+access\s+"
                    r"(?:is\s+)?not\s+available\b"
                ),
                severity=Severity.REVIEW,
                message=(
                    "Verify that this is an objective accessibility "
                    "description rather than an exclusion."
                ),
            ),
        ]

    @staticmethod
    def _make_violation(
        *,
        category: str,
        match: re.Match,
        severity: Severity,
        message: str,
        finding_type: str,
    ) -> dict:
        return {
            "category": category,
            "matched_text": match.group(0),
            "severity": severity.value,
            "message": message,
            "finding_type": finding_type,
            "start": match.start(),
            "end": match.end(),
        }

    @staticmethod
    def _deduplicate(violations: list[dict]) -> list[dict]:
        seen = set()
        deduplicated = []

        for violation in violations:
            key = (
                violation["category"],
                violation["severity"],
                violation["start"],
                violation["end"],
            )

            if key not in seen:
                seen.add(key)
                deduplicated.append(violation)

        return deduplicated

    @staticmethod
    def _build_result(
        text: str,
        violations: list[dict],
    ) -> dict:
        violations = ComplianceChecker._deduplicate(violations)

        has_error = any(
            violation["severity"] == Severity.ERROR.value
            for violation in violations
        )

        return {
            # Review findings do not automatically make the text
            # definitively noncompliant.
            "compliant": not has_error,
            "requires_review": bool(violations),
            "normalized_text": text,
            "violations": violations,
        }

    def check_listing(self, text: str) -> dict:
        """
        Evaluate property-listing or advertising language.
        """
        normalized = self._normalize(text)
        violations = []

        for rule, regex in self._compiled_rules:
            for match in regex.finditer(normalized):
                violations.append(
                    self._make_violation(
                        category=rule.category,
                        match=match,
                        severity=rule.severity,
                        message=rule.message,
                        finding_type="listing_rule",
                    )
                )

        return self._build_result(
            normalized,
            violations,
        )

    def check_query(self, text: str) -> dict:
        """
        Evaluate a user's housing search or recommendation query.

        A protected-class reference is not sufficient by itself.
        The method requires exclusionary or preferential intent.
        """
        normalized = self._normalize(text)

        # Remove phrases about preventing discrimination so words such
        # as "without" or "avoid" do not create false positives.
        intent_text = ANTI_DISCRIMINATION_CONTEXT.sub(
            " ",
            normalized,
        )

        intent_matches = [
            *EXCLUSION_TERMS.finditer(intent_text),
            *PREFERENCE_TERMS.finditer(intent_text),
        ]

        if not intent_matches:
            return self._build_result(
                normalized,
                [],
            )

        violations = []

        for category, category_regex in (
            PROTECTED_CLASS_PATTERNS.items()
        ):
            for category_match in category_regex.finditer(normalized):
                violations.append(
                    self._make_violation(
                        category=category,
                        match=category_match,
                        severity=Severity.ERROR,
                        message=(
                            "Query may request exclusion, preference, "
                            "or steering based on "
                            f"{category.replace('_', ' ')}."
                        ),
                        finding_type="query_intent",
                    )
                )

        return self._build_result(
            normalized,
            violations,
        )

    def check(self, text: str, text_type: str = "listing") -> dict:
        """
        Common entry point.

        text_type:
            "listing" - listing or advertisement language
            "query"   - user search or recommendation request
        """
        if text_type == "listing":
            return self.check_listing(text)

        if text_type == "query":
            return self.check_query(text)

        raise ValueError(
            "text_type must be either 'listing' or 'query'"
        )
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

# compliance checking comes with severity levels, so we can distinguish between "review" and "error" findings.

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
    def __init__(self, rules: Iterable[Rule] | None = None):
        self.rules = tuple(rules or self._default_rules())

        # Compile once rather than during every check.
        self._compiled_rules = tuple(
            (
                rule,
                re.compile(rule.expression, flags=re.IGNORECASE),
            )
            for rule in self.rules
        )

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("’", "'").replace("–", "-").replace("—", "-")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _default_rules() -> list[Rule]:
        return [
            Rule(
                category="familial_status",
                expression=r"\b(?:no\s+(?:children|kids|minors)|adults[\s-]+only)\b",
                severity=Severity.ERROR,
                message="Language may exclude applicants based on familial status.",
            ),
            Rule(
                category="familial_status",
                expression=(
                    r"\b(?:perfect\s+for\s+singles|ideal\s+for\s+couples|"
                    r"adults?\s+preferred|not\s+suitable\s+for\s+families)\b"
                ),
                severity=Severity.REVIEW,
                message="Language may express a preference about household composition.",
            ),
            Rule(
                category="disability",
                expression=r"\b(?:no\s+wheelchairs?|must\s+be\s+able[\s-]+bodied)\b",
                severity=Severity.ERROR,
                message="Language may exclude people based on disability.",
            ),
            Rule(
                category="disability",
                expression=r"\bdisabled\s+access\s+(?:is\s+)?not\s+available\b",
                severity=Severity.REVIEW,
                message="Verify that this is an objective accessibility description.",
            ),
            Rule(
                category="protected_class_preference",
                expression=(
                    r"\b(?:christian|jewish|muslim|hindu|sikh|catholic|"
                    r"white|black|asian|hispanic|latino|caucasian|"
                    r"gay|lesbian|straight)[\s-]+"
                    r"(?:community|neighbou?rhood|preferred|only|friendly)\b"
                ),
                severity=Severity.REVIEW,
                message="Language may indicate a preference involving a protected class.",
            ),
        ]

    def check_listing(self, text: str) -> dict:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        normalized_text = self._normalize(text)
        violations = []
        seen = set()

        for rule, regex in self._compiled_rules:
            for match in regex.finditer(normalized_text):
                key = (rule.category, match.start(), match.end())
                if key in seen:
                    continue
                seen.add(key)

                violations.append(
                    {
                        "category": rule.category,
                        "matched_text": match.group(0),
                        "severity": rule.severity.value,
                        "message": rule.message,
                        "start": match.start(),
                        "end": match.end(),
                    }
                )

        has_error = any(
            violation["severity"] == Severity.ERROR.value
            for violation in violations
        )

        return {
            # Review findings should not automatically assert illegality.
            "compliant": not has_error,
            "requires_review": bool(violations),
            "violations": violations,
        }
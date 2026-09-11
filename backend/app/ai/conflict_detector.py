"""
Deterministic technical-conflict detector.

Semantic similarity (SBERT/pgvector/XGBoost) can score two descriptions as
"almost the same wording" even when they name incompatible engineering
specifications - e.g. "SS BOLT M10" vs "SS BOLT M12", or "Gate Valve 2 inch"
vs "Gate Valve 3 inch", read as nearly identical text but are not
interchangeable parts. This module extracts real numeric/grade tokens that
are already present in the material's own description + specification text
(reusing the same cleaning normalization.basic_clean already applies
everywhere else, and the same regex vocabulary app.ai.attribute_patterns
uses for extraction) and flags a conflict only when both materials mention
a token in the *same* technical category (material grade, dimension,
thread/bolt size, voltage, pressure) and none of the values on either side
match.

This never fabricates a conflict: if only one side mentions a dimension,
or the same value appears on both sides, nothing is flagged. It is a
second, independent signal alongside the existing similarity score - not a
replacement for it. A confirmed conflict here overrides any similarity
score, however high (spec section 9/10) - see app.services.decision_engine.
"""
from dataclasses import dataclass

from app.ai.attribute_patterns import TECHNICAL_TOKEN_PATTERNS
from app.services.normalization import basic_clean


@dataclass
class ConflictResult:
    has_conflict: bool
    reasons: list[str]


def _extract(text: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for label, pattern, normalize in TECHNICAL_TOKEN_PATTERNS:
        matches = {normalize(m) for m in pattern.finditer(text)}
        if matches:
            found[label] = matches
    return found


def detect_conflict(text_a: str, text_b: str) -> ConflictResult:
    """Compares two materials' combined description+specification text for
    genuine technical incompatibilities - distinct from semantic
    dissimilarity, which the existing scoring pipeline already handles."""
    tokens_a = _extract(basic_clean(text_a))
    tokens_b = _extract(basic_clean(text_b))

    reasons: list[str] = []
    for label in sorted(tokens_a.keys() & tokens_b.keys()):
        if tokens_a[label].isdisjoint(tokens_b[label]):
            reasons.append(
                f"{label} mismatch: {', '.join(sorted(tokens_a[label]))} vs {', '.join(sorted(tokens_b[label]))}"
            )
    return ConflictResult(has_conflict=bool(reasons), reasons=reasons)


# Structured fields where a mismatch is a critical conflict per spec section 9
# ("confidence alone must NEVER override ... incompatible grade,
# incompatible specification") even when the CPSE's source data never
# restates the value in free-text description/specification - e.g. a source
# table carrying grade as its own column, never mentioned in the description
# string at all. This is a second, independent structured-field check
# alongside detect_conflict's text-regex scan above - neither replaces the
# other.
#
# Deliberately EXCLUDES "dimensions": unlike a grade/standard code (already a
# short, standardized token such as "SS304" or "ASTM F593"), a dimension
# string has no canonical format - "M10x50" and "10mm x 50mm" describe the
# identical physical size but are not equal as strings, so a naive exact
# match would flag a false conflict on exactly the kind of differently-worded
# equivalent pair this platform exists to recognize (spec section 42 case 1).
# Real dimension conflicts (e.g. "2 inch" vs "3 inch") are already caught
# by detect_conflict's unit-aware text-regex scan above.
_STRUCTURED_CONFLICT_FIELDS = (("material_grade", "Grade"), ("standard", "Standard"))


def detect_structural_conflict(fields_a: dict[str, str | None], fields_b: dict[str, str | None]) -> ConflictResult:
    """fields_a/fields_b map field name -> value for material_grade/standard.
    Only flags a mismatch when BOTH sides actually specify a value for that
    field and they genuinely differ - never when one side simply didn't
    record it (spec section 11: missing data is never treated as evidence of
    anything)."""
    reasons: list[str] = []
    for field, label in _STRUCTURED_CONFLICT_FIELDS:
        value_a, value_b = fields_a.get(field), fields_b.get(field)
        if not value_a or not value_b:
            continue
        norm_a, norm_b = value_a.strip().upper(), value_b.strip().upper()
        if norm_a != norm_b:
            reasons.append(f"{label} mismatch: {norm_a} vs {norm_b}")
    return ConflictResult(has_conflict=bool(reasons), reasons=reasons)

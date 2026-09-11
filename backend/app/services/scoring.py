"""
Explainable weighted similarity scoring (spec section 6-9).

Every comparison between two CPSE materials produces a set of independently
inspectable 0-100 component scores plus a final weighted score, so the
frontend "why did AI match these materials?" panel can always show a
human-readable breakdown - nothing here is a black box. Material identity
considers more than description text: type, grade, dimensions,
specification, UOM, manufacturer (when technically critical), standard,
function and criticality all contribute (spec section 6). Packaging/pack
size is deliberately never a component here - it must never make two
otherwise-identical materials look different (spec section 6 example).
"""
import difflib
from dataclasses import dataclass, fields

import numpy as np

from app.services.settings_service import get_effective_weights

# UOMs that denote a *count/packaging* unit rather than a physical measure
# (weight/length/volume). A mismatch purely within this group (e.g. EACH vs
# BOX) reflects a packaging difference, not a different underlying material,
# so it is scored as a mild, non-disqualifying mismatch rather than 0.
DISCRETE_UOM_GROUP = {"EACH", "NUMBERS", "BOX", "SET", "PAIR", "ROLL"}

# Classifications where the manufacturer's identity is technically
# meaningful (interchangeability is not guaranteed across manufacturers) -
# spec section 6 point 7 ("manufacturer when technically critical"). Outside
# this set, manufacturer is dropped from the weighted score entirely rather
# than penalizing/rewarding a coincidental match.
MANUFACTURER_CRITICAL_CRITICALITY = {"CRITICAL"}


@dataclass
class ScoreBreakdown:
    final_score: float
    description_score: float
    specification_score: float
    classification_score: float
    uom_score: float
    attribute_score: float
    grade_score: float
    dimension_score: float
    standard_score: float
    manufacturer_score: float
    function_score: float
    criticality_score: float

    def as_dict(self) -> dict:
        return {f.name: round(getattr(self, f.name), 2) for f in fields(self)}


def cosine_similarity(a: list[float] | None, b: list[float] | None) -> float | None:
    # `a`/`b` may be numpy arrays (pgvector columns deserialize that way) - never
    # use bare truthiness on them, "bool(array)" raises for multi-element arrays.
    if a is None or b is None or len(a) == 0 or len(b) == 0:
        return None
    va, vb = np.array(a, dtype=float), np.array(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return None
    sim = float(np.dot(va, vb) / denom)
    # Map cosine similarity from [-1, 1] onto [0, 1]: 1.0 = identical, 0.5 = orthogonal, 0.0 = opposite.
    return max(0.0, min(1.0, (sim + 1) / 2))


def text_ratio(a: str, b: str) -> float:
    if not a and not b:
        return 100.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio() * 100.0


def field_text_score(norm_a: str, norm_b: str, embedding_cosine: float | None) -> float:
    """Blend embedding cosine similarity (semantic) with raw token overlap (lexical)."""
    ratio = text_ratio(norm_a or "", norm_b or "")
    if embedding_cosine is None:
        return round(ratio, 2)
    return round((embedding_cosine * 100.0) * 0.7 + ratio * 0.3, 2)


def classification_score(norm_a: str, norm_b: str) -> float:
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 100.0
    return round(text_ratio(norm_a, norm_b), 2)


def uom_score(norm_a: str, norm_b: str) -> float:
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 100.0
    if norm_a in DISCRETE_UOM_GROUP and norm_b in DISCRETE_UOM_GROUP:
        # Both sides use a count/packaging unit, just a different one (e.g.
        # PC vs BOX) - a packaging difference, not a material-identity
        # conflict (spec section 6), so this is not scored as low as a
        # genuine cross-measure mismatch (e.g. METER vs KILOGRAM).
        return 70.0
    ratio = text_ratio(norm_a, norm_b)
    return round(ratio, 2) if ratio > 60 else 0.0


def attribute_score(attrs_a: dict[str, str], attrs_b: dict[str, str]) -> float:
    if not attrs_a and not attrs_b:
        return 100.0
    if not attrs_a or not attrs_b:
        return 50.0  # neutral - one side simply didn't capture extra attributes
    keys = set(attrs_a) | set(attrs_b)
    if not keys:
        return 100.0
    total = 0.0
    for key in keys:
        va, vb = attrs_a.get(key), attrs_b.get(key)
        if va is None or vb is None:
            total += 40.0  # attribute only present on one side
        elif va.strip().upper() == vb.strip().upper():
            total += 100.0
        else:
            total += text_ratio(va.upper(), vb.upper())
    return round(total / len(keys), 2)


def _direct_field_score(value_a: str | None, value_b: str | None) -> float:
    """Shared shape for grade/dimension/standard/function: neither side
    specified it -> neutral 100 (nothing to disagree about, same philosophy
    as attribute_score above); only one side specified it -> neutral 50;
    both specified -> exact match or lexical ratio."""
    a, b = (value_a or "").strip().upper(), (value_b or "").strip().upper()
    if not a and not b:
        return 100.0
    if not a or not b:
        return 50.0
    if a == b:
        return 100.0
    return round(text_ratio(a, b), 2)


def grade_score(a: str | None, b: str | None) -> float:
    return _direct_field_score(a, b)


def dimension_score(a: str | None, b: str | None) -> float:
    return _direct_field_score(a, b)


def standard_score(a: str | None, b: str | None) -> float:
    return _direct_field_score(a, b)


def function_score(a: str | None, b: str | None) -> float:
    return _direct_field_score(a, b)


def manufacturer_score(a: str | None, b: str | None) -> float:
    return _direct_field_score(a, b)


def criticality_score(a: str | None, b: str | None) -> float:
    a, b = a or "UNSPECIFIED", b or "UNSPECIFIED"
    if a == "UNSPECIFIED" or b == "UNSPECIFIED":
        return 70.0
    return 100.0 if a == b else 40.0


def manufacturer_is_applicable(criticality_a: str | None, criticality_b: str | None) -> bool:
    return (criticality_a in MANUFACTURER_CRITICAL_CRITICALITY) or (criticality_b in MANUFACTURER_CRITICAL_CRITICALITY)


# Optional structured fields (spec section 6) that a CPSE's source data may
# genuinely never populate. When BOTH sides lack one of these, the component
# is excluded entirely and its weight is redistributed - never scored as a
# neutral 100, which would otherwise inflate the confidence of two
# completely unrelated materials that simply both happen to omit the same
# optional field (verified: "Electrical Cable" vs "Industrial Pump", both
# missing grade/dimension/standard, landed in the review band instead of
# NOT_EQUIVALENT before this fix - see spec section 42 case 4). This is the
# same redistribution mechanism already used for `manufacturer` above,
# applied consistently to every optional field rather than only one.
_OPTIONAL_FIELDS = ("grade", "dimension", "standard", "function", "manufacturer")


def field_is_applicable(value_a: str | None, value_b: str | None) -> bool:
    return bool(value_a) and bool(value_b)


def compute_final_score(
    *,
    description_score: float,
    specification_score: float,
    classification_score: float,
    uom_score: float,
    attribute_score: float,
    grade_score: float,
    dimension_score: float,
    standard_score: float,
    manufacturer_score: float,
    function_score: float,
    criticality_score: float,
    grade_applicable: bool = True,
    dimension_applicable: bool = True,
    standard_applicable: bool = True,
    function_applicable: bool = True,
    manufacturer_applicable: bool = False,
    weights: dict | None = None,
) -> ScoreBreakdown:
    weights = weights or get_effective_weights()
    w = dict(weights)

    component_values = {
        "description": description_score,
        "specification": specification_score,
        "classification": classification_score,
        "uom": uom_score,
        "attributes": attribute_score,
        "grade": grade_score,
        "dimension": dimension_score,
        "standard": standard_score,
        "manufacturer": manufacturer_score,
        "function": function_score,
        "criticality": criticality_score,
    }
    applicability = {
        "grade": grade_applicable,
        "dimension": dimension_applicable,
        "standard": standard_applicable,
        "function": function_applicable,
        "manufacturer": manufacturer_applicable,
    }

    inapplicable_weight = 0.0
    for field in _OPTIONAL_FIELDS:
        if not applicability[field]:
            inapplicable_weight += w.pop(field, 0.0)
            component_values[field] = 0.0

    remaining = sum(w.values())
    if inapplicable_weight and remaining:
        scale = (remaining + inapplicable_weight) / remaining
        w = {k: v * scale for k, v in w.items()}

    final = sum(component_values[key] * w.get(key, 0.0) for key in component_values)

    return ScoreBreakdown(
        final_score=round(final, 2),
        description_score=description_score,
        specification_score=specification_score,
        classification_score=classification_score,
        uom_score=uom_score,
        attribute_score=attribute_score,
        grade_score=grade_score,
        dimension_score=dimension_score,
        standard_score=standard_score,
        manufacturer_score=manufacturer_score,
        function_score=function_score,
        criticality_score=criticality_score,
    )

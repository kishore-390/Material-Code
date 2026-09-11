"""
Critical decision rules (spec section 8-9).

This is the single source of truth for turning a final confidence score
plus the technical-conflict signal into one of the required match
categories - IDENTICAL, DUPLICATE, NEAR_DUPLICATE, FUNCTIONALLY_EQUIVALENT,
NOT_EQUIVALENT, TECHNICAL_CONFLICT, MANUAL_REVIEW. A confirmed technical
conflict always overrides similarity, however high (spec section 9/10) -
confidence alone must never paper over an incompatible grade, dimension or
specification. Thresholds are read from app.services.settings_service so
an ADMIN can tune them at runtime without a redeploy.
"""
from dataclasses import dataclass

from app.ai.conflict_detector import ConflictResult
from app.models.enums import MatchDecision
from app.services.scoring import ScoreBreakdown
from app.services.settings_service import get_effective_thresholds

# A pair only qualifies as IDENTICAL (not just DUPLICATE) when every
# key structured attribute that either side actually specified agrees
# exactly - never inferred purely from an overall score being high enough.
_IDENTICAL_FLOOR = 99.0
_FUNCTIONAL_EQUIVALENCE_CLASSIFICATION_FLOOR = 90.0
_FUNCTIONAL_EQUIVALENCE_FUNCTION_FLOOR = 70.0


@dataclass
class DecisionResult:
    decision: str
    message: str
    reason_text: str


def _human_reason(material_desc: str, candidate_desc: str, scores: ScoreBreakdown) -> str:
    return (
        f"Both materials represent '{material_desc.strip().lower()}' "
        f"and were found to be {scores.final_score:.0f}% similar overall - "
        f"{scores.description_score:.0f}% description, {scores.specification_score:.0f}% specification, "
        f"{scores.classification_score:.0f}% classification, {scores.grade_score:.0f}% grade, "
        f"{scores.dimension_score:.0f}% dimension and {scores.uom_score:.0f}% unit-of-measure match."
    )


def evaluate(
    scores: ScoreBreakdown,
    material_description: str = "",
    candidate_description: str = "",
    conflict: ConflictResult | None = None,
    thresholds: dict | None = None,
) -> DecisionResult:
    thresholds = thresholds or get_effective_thresholds()
    score = scores.final_score
    reason = _human_reason(material_description, candidate_description, scores)

    # A genuine technical incompatibility always wins, regardless of how
    # similar the wording reads (spec section 9 - "HIGH SIMILARITY +
    # TECHNICAL CONFLICT = TECHNICAL_CONFLICT, not an equivalence decision").
    if conflict is not None and conflict.has_conflict:
        return DecisionResult(
            decision=MatchDecision.TECHNICAL_CONFLICT.value,
            message="A technical conflict was detected between these materials' key specifications.",
            reason_text=f"{reason} However, a technical conflict was detected: {'; '.join(conflict.reasons)}.",
        )

    if score >= thresholds["auto"]:
        key_attributes_agree = (
            scores.grade_score >= _IDENTICAL_FLOOR
            and scores.dimension_score >= _IDENTICAL_FLOOR
            and scores.standard_score >= _IDENTICAL_FLOOR
            and scores.classification_score >= _IDENTICAL_FLOOR
        )
        if key_attributes_agree:
            return DecisionResult(
                decision=MatchDecision.IDENTICAL.value,
                message="Every key technical attribute matches exactly - these are the same material.",
                reason_text=reason,
            )
        return DecisionResult(
            decision=MatchDecision.DUPLICATE.value,
            message="AI confidence meets the automatic harmonization threshold.",
            reason_text=reason,
        )

    if score >= thresholds["review"]:
        functionally_equivalent = (
            scores.classification_score >= _FUNCTIONAL_EQUIVALENCE_CLASSIFICATION_FLOOR
            and scores.function_score >= _FUNCTIONAL_EQUIVALENCE_FUNCTION_FLOOR
        )
        if functionally_equivalent:
            return DecisionResult(
                decision=MatchDecision.FUNCTIONALLY_EQUIVALENT.value,
                message="These materials serve the same function and classification despite differing wording.",
                reason_text=reason,
            )
        return DecisionResult(
            decision=MatchDecision.NEAR_DUPLICATE.value,
            message="AI found a strong candidate match, but human confirmation is required before harmonization.",
            reason_text=reason,
        )

    if score >= thresholds["low"]:
        return DecisionResult(
            decision=MatchDecision.MANUAL_REVIEW.value,
            message="AI confidence is insufficient for automatic classification - manual review is required.",
            reason_text=reason,
        )

    return DecisionResult(
        decision=MatchDecision.NOT_EQUIVALENT.value,
        message="No sufficiently similar material found - these are not considered equivalent.",
        reason_text="The similarity score is below the minimum equivalence threshold.",
    )

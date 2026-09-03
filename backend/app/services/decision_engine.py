"""
Critical decision rules (spec section 9).

This is the single source of truth for turning a final confidence score
into a decision. Thresholds are read from app.services.settings_service
so an ADMIN can tune them at runtime without a redeploy.
"""
from dataclasses import dataclass

from app.models.enums import Decision
from app.services.scoring import ScoreBreakdown
from app.services.settings_service import get_effective_thresholds


@dataclass
class DecisionResult:
    decision: str
    message: str
    reason_text: str


def _human_reason(material_desc: str, candidate_desc: str, scores: ScoreBreakdown) -> str:
    return (
        f"Both materials represent '{material_desc.strip().lower()}' "
        f"and were found to be equivalent with {scores.description_score:.0f}% description similarity, "
        f"{scores.specification_score:.0f}% specification similarity, "
        f"{scores.category_score:.0f}% category match and {scores.uom_score:.0f}% unit-of-measure match."
    )


def evaluate(
    scores: ScoreBreakdown,
    material_description: str = "",
    candidate_description: str = "",
    thresholds: dict | None = None,
) -> DecisionResult:
    thresholds = thresholds or get_effective_thresholds()
    score = scores.final_score
    reason = _human_reason(material_description, candidate_description, scores)

    if score >= thresholds["auto"]:
        return DecisionResult(
            decision=Decision.AUTO_HARMONIZATION.value,
            message="AI confidence meets the automatic harmonization threshold.",
            reason_text=reason,
        )
    if score >= thresholds["review"]:
        return DecisionResult(
            decision=Decision.HUMAN_REVIEW_REQUIRED.value,
            message="AI found a strong candidate match, but human confirmation is required before harmonization.",
            reason_text=reason,
        )
    if score >= thresholds["low"]:
        return DecisionResult(
            decision=Decision.LOW_CONFIDENCE.value,
            message="AI confidence is insufficient for automatic harmonization.",
            reason_text=reason,
        )
    return DecisionResult(
        decision=Decision.NO_COMMON_CODE.value,
        message="No sufficiently similar material found. Common material code cannot be recommended.",
        reason_text="The similarity score is below the minimum harmonization threshold.",
    )

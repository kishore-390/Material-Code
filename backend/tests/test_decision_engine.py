from app.ai.conflict_detector import ConflictResult
from app.models.enums import MatchDecision
from app.services.decision_engine import evaluate
from app.services.scoring import ScoreBreakdown

THRESHOLDS = {"auto": 95, "review": 85, "low": 60}
_NO_CONFLICT = ConflictResult(has_conflict=False, reasons=[])


def _breakdown(final_score: float, **overrides) -> ScoreBreakdown:
    base = dict(
        final_score=final_score, description_score=final_score, specification_score=final_score,
        classification_score=final_score, uom_score=final_score, attribute_score=final_score,
        grade_score=final_score, dimension_score=final_score, standard_score=final_score,
        manufacturer_score=final_score, function_score=final_score, criticality_score=final_score,
    )
    base.update(overrides)
    return ScoreBreakdown(**base)


def test_score_96_with_exact_attributes_is_identical():
    # IDENTICAL requires every key structured attribute to match exactly
    # (>=99), not just an overall score above the auto threshold - grade/
    # dimension/standard/classification are set to 100 here while the
    # overall score (96) still comes from the lower-scoring free-text fields.
    breakdown = _breakdown(96, grade_score=100, dimension_score=100, standard_score=100, classification_score=100)
    result = evaluate(breakdown, "SS Hex Bolt", "SS Hex Bolt", conflict=_NO_CONFLICT, thresholds=THRESHOLDS)
    assert result.decision == MatchDecision.IDENTICAL.value


def test_score_96_without_exact_grade_is_duplicate():
    result = evaluate(_breakdown(96, grade_score=50), conflict=_NO_CONFLICT, thresholds=THRESHOLDS)
    assert result.decision == MatchDecision.DUPLICATE.value


def test_score_90_with_functional_match_is_functionally_equivalent():
    result = evaluate(
        _breakdown(90, classification_score=95, function_score=80), conflict=_NO_CONFLICT, thresholds=THRESHOLDS
    )
    assert result.decision == MatchDecision.FUNCTIONALLY_EQUIVALENT.value


def test_score_90_without_functional_match_is_near_duplicate():
    result = evaluate(
        _breakdown(90, classification_score=50, function_score=20), conflict=_NO_CONFLICT, thresholds=THRESHOLDS
    )
    assert result.decision == MatchDecision.NEAR_DUPLICATE.value


def test_score_75_is_manual_review():
    result = evaluate(_breakdown(75), conflict=_NO_CONFLICT, thresholds=THRESHOLDS)
    assert result.decision == MatchDecision.MANUAL_REVIEW.value


def test_score_55_is_not_equivalent():
    result = evaluate(_breakdown(55), conflict=_NO_CONFLICT, thresholds=THRESHOLDS)
    assert result.decision == MatchDecision.NOT_EQUIVALENT.value
    assert "below the minimum equivalence threshold" in result.reason_text


def test_technical_conflict_overrides_high_similarity():
    """Spec section 9: HIGH SIMILARITY + TECHNICAL CONFLICT = TECHNICAL_CONFLICT, never an equivalence decision."""
    conflict = ConflictResult(has_conflict=True, reasons=["Material grade mismatch: SS304 vs SS316"])
    result = evaluate(_breakdown(99), conflict=conflict, thresholds=THRESHOLDS)
    assert result.decision == MatchDecision.TECHNICAL_CONFLICT.value

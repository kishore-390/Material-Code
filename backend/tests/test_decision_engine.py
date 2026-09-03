from app.models.enums import Decision
from app.services.decision_engine import evaluate
from app.services.scoring import ScoreBreakdown

THRESHOLDS = {"auto": 95, "review": 85, "low": 60}


def _breakdown(final_score: float) -> ScoreBreakdown:
    return ScoreBreakdown(
        final_score=final_score,
        description_score=final_score,
        specification_score=final_score,
        category_score=final_score,
        uom_score=final_score,
        image_score=final_score,
        attribute_score=final_score,
    )


def test_score_96_is_auto_harmonization():
    result = evaluate(_breakdown(96), "Carbon Steel Pipe", "Carbon Steel Pipe", thresholds=THRESHOLDS)
    assert result.decision == Decision.AUTO_HARMONIZATION.value


def test_score_95_boundary_is_auto_harmonization():
    result = evaluate(_breakdown(95), thresholds=THRESHOLDS)
    assert result.decision == Decision.AUTO_HARMONIZATION.value


def test_score_90_is_human_review_required():
    result = evaluate(_breakdown(90), "Gate Valve", "Gate Valve", thresholds=THRESHOLDS)
    assert result.decision == Decision.HUMAN_REVIEW_REQUIRED.value


def test_score_85_boundary_is_human_review_required():
    result = evaluate(_breakdown(85), thresholds=THRESHOLDS)
    assert result.decision == Decision.HUMAN_REVIEW_REQUIRED.value


def test_score_75_is_low_confidence():
    result = evaluate(_breakdown(75), thresholds=THRESHOLDS)
    assert result.decision == Decision.LOW_CONFIDENCE.value


def test_score_60_boundary_is_low_confidence():
    result = evaluate(_breakdown(60), thresholds=THRESHOLDS)
    assert result.decision == Decision.LOW_CONFIDENCE.value


def test_score_55_is_no_common_code():
    result = evaluate(_breakdown(55), thresholds=THRESHOLDS)
    assert result.decision == Decision.NO_COMMON_CODE.value


def test_score_zero_is_no_common_code():
    result = evaluate(_breakdown(0), thresholds=THRESHOLDS)
    assert result.decision == Decision.NO_COMMON_CODE.value
    assert "below the minimum harmonization threshold" in result.reason_text

"""
XGBoost ranker tests (spec section 49 - "if a trained model does not yet
exist, implement a clean model interface and a deterministic development
fallback rather than pretending a fake trained model exists"). No trained
model is committed to the repo (see app/ml/train_xgb_ranker.py for how one
would be produced from real synced+approved data), so these tests exercise
the FALLBACK path plus the blend-gating logic using a stubbed-in fake model
- never a real trained artifact pretending to be one.
"""
import app.ai.ml_ranker as ml_ranker
from app.core.config import settings
from app.services.scoring import ScoreBreakdown


def _breakdown(**overrides) -> ScoreBreakdown:
    base = dict(
        final_score=80, description_score=80, specification_score=80, classification_score=80,
        uom_score=80, attribute_score=80, grade_score=80, dimension_score=80, standard_score=80,
        manufacturer_score=80, function_score=80, criticality_score=80,
    )
    base.update(overrides)
    return ScoreBreakdown(**base)


def test_no_committed_model_falls_back_safely():
    ml_ranker.reset_model_cache()
    result = ml_ranker.score_with_ml(ml_ranker.extract_features(_breakdown()))
    assert result.status == "FALLBACK"
    assert result.available is False
    assert result.score is None


def test_missing_model_path_falls_back_safely(monkeypatch):
    monkeypatch.setattr(settings, "XGB_MODEL_PATH", "/tmp/does-not-exist-xgb-model.json")
    ml_ranker.reset_model_cache()
    result = ml_ranker.score_with_ml(ml_ranker.extract_features(_breakdown()))
    assert result.status == "FALLBACK"
    ml_ranker.reset_model_cache()


def test_blend_scores_returns_untouched_breakdown_without_a_model():
    ml_ranker.reset_model_cache()
    breakdown = _breakdown(final_score=80)
    blended, ml_result = ml_ranker.blend_scores(breakdown)
    assert blended.final_score == 80
    assert ml_result.status == "FALLBACK"


def test_blend_scores_gated_below_classification_safety_floor(monkeypatch):
    """Even a stubbed-in confident model must be ignored entirely when the
    rule-based classification score signals different material families."""

    class _FakeModel:
        def predict_proba(self, rows):
            return [[0.05, 0.95]]  # very confident "match"

    monkeypatch.setattr(ml_ranker, "_load_model", lambda: _FakeModel())
    ml_ranker._load_attempted = True
    ml_ranker._model = _FakeModel()

    breakdown = _breakdown(final_score=40, classification_score=10)  # below XGB_SAFETY_CLASSIFICATION_FLOOR
    blended, ml_result = ml_ranker.blend_scores(breakdown)
    assert ml_result.available is True
    assert blended.final_score == 40  # unchanged - the model's opinion was discarded
    ml_ranker.reset_model_cache()


def test_blend_scores_applies_above_classification_safety_floor(monkeypatch):
    class _FakeModel:
        def predict_proba(self, rows):
            return [[0.0, 1.0]]  # probability 100

    ml_ranker._load_attempted = True
    ml_ranker._model = _FakeModel()

    breakdown = _breakdown(final_score=60, classification_score=90)  # above the floor
    blended, ml_result = ml_ranker.blend_scores(breakdown)
    assert ml_result.available is True
    assert blended.final_score == 80  # 0.5*60 + 0.5*100
    ml_ranker.reset_model_cache()


def test_feature_order_never_includes_material_codes():
    assert "material_code" not in ml_ranker.FEATURE_ORDER
    assert "original_material_code" not in ml_ranker.FEATURE_ORDER
    for name in ml_ranker.FEATURE_ORDER:
        assert "code" not in name.lower()

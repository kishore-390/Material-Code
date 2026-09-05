"""
XGBoost material-match ranker, genuinely integrated into the decision path
(spec §24-25 + the follow-up "actually train it" request).

Design:
- Features are exactly the six existing 0-100 component scores the rule-based
  scorer already computes (`ScoreBreakdown`) - no new feature-extraction path
  to keep in sync, and CPSE material codes are never a feature (the model
  only ever sees material characteristics).
- `blend_scores()` is the ONLY place XGBoost's prediction can influence a
  decision. It is a hard-gated blend: XGBoost's opinion is used only when a
  trained model is available AND the rule-based category component already
  clears a safety floor (XGB_SAFETY_CATEGORY_FLOOR). Below that floor - e.g.
  a pipe vs a drill bit - XGBoost's prediction is discarded entirely and the
  untouched rule-based score decides, so a stray high probability can never
  push a category-incompatible pair into AUTO_HARMONIZATION.
- If no trained model exists (`settings.XGB_MODEL_PATH` missing), every call
  reports `status="FALLBACK"` and behaves exactly as the pre-trained system
  did: pure rule-based score, no crash, no fabricated number.

See app/ml/train_xgb_ranker.py for how the model here is actually produced.
"""
import dataclasses
import logging
import os
from dataclasses import dataclass

from app.core.config import settings
from app.services.scoring import ScoreBreakdown

logger = logging.getLogger(__name__)

FEATURE_ORDER = [
    "description_score",
    "specification_score",
    "category_score",
    "uom_score",
    "attribute_score",
    "image_score",
]

# Below this rule-based category-similarity score, the two materials are
# treated as different material families and XGBoost's opinion is ignored
# outright - it cannot single-handedly harmonize a pipe with a drill bit.
XGB_SAFETY_CATEGORY_FLOOR = 50.0

_model = None
_load_attempted = False


@dataclass
class MLScoreResult:
    available: bool
    score: float | None
    status: str  # "FALLBACK" | "TRAINED" | "ERROR"


def extract_features(breakdown: ScoreBreakdown) -> dict:
    return {
        "description_score": breakdown.description_score,
        "specification_score": breakdown.specification_score,
        "category_score": breakdown.category_score,
        "uom_score": breakdown.uom_score,
        "attribute_score": breakdown.attribute_score,
        "image_score": breakdown.image_score,
    }


def reset_model_cache() -> None:
    """Forces the next score_with_ml() call to re-check XGB_MODEL_PATH. Used
    by tests that need to exercise both the trained and fallback paths in
    the same process, and safe to call after (re)training a model."""
    global _model, _load_attempted
    _model = None
    _load_attempted = False


def _load_model():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    _load_attempted = True
    if not os.path.exists(settings.XGB_MODEL_PATH):
        logger.info("No trained XGBoost model at %s - falling back to rule-based scoring only", settings.XGB_MODEL_PATH)
        return None
    try:
        import xgboost as xgb

        booster = xgb.XGBClassifier()
        booster.load_model(settings.XGB_MODEL_PATH)
        _model = booster
        logger.info("Loaded trained XGBoost model from %s", settings.XGB_MODEL_PATH)
    except Exception:  # noqa: BLE001
        logger.exception("Found a model file at %s but failed to load it", settings.XGB_MODEL_PATH)
        _model = None
    return _model


def score_with_ml(features: dict) -> MLScoreResult:
    model = _load_model()
    if model is None:
        return MLScoreResult(available=False, score=None, status="FALLBACK")
    try:
        row = [[features[name] for name in FEATURE_ORDER]]
        probability = float(model.predict_proba(row)[0][1])
        return MLScoreResult(available=True, score=round(probability * 100, 2), status="TRAINED")
    except Exception:  # noqa: BLE001
        logger.exception("XGBoost inference failed")
        return MLScoreResult(available=False, score=None, status="ERROR")


def blend_scores(breakdown: ScoreBreakdown) -> tuple[ScoreBreakdown, MLScoreResult]:
    """
    Returns (decision_breakdown, ml_result). decision_breakdown is identical
    to `breakdown` except final_score may be blended 50/50 with the XGBoost
    probability - and only when the safety gate above is satisfied. Every
    other component score (description/specification/category/uom/
    attribute/image) is untouched, so the reported "why it matched"
    breakdown always reflects the real rule-based components.
    """
    ml_result = score_with_ml(extract_features(breakdown))
    if ml_result.available and breakdown.category_score >= XGB_SAFETY_CATEGORY_FLOOR:
        blended = round(0.5 * breakdown.final_score + 0.5 * ml_result.score, 2)
        return dataclasses.replace(breakdown, final_score=blended), ml_result
    return breakdown, ml_result

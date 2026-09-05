"""
End-to-end, reproducible XGBoost training run for the material-equivalence
ranker described in app.ai.ml_ranker.

Run inside the backend container (needs DB + connector access):

    docker compose exec backend python -m app.ml.train_xgb_ranker

What it does, in order: load IOCL/ONGC materials already present in the
app's own materials table -> build labeled pairs by rule
(app.ml.build_training_dataset) -> compute the same six features the live
pipeline uses -> split by MATERIAL (not by pair) into train/validation/test
so no material's pairs leak across splits -> train XGBClassifier ->
evaluate on the held-out test set -> save the model to
settings.XGB_MODEL_PATH -> print a full, honest report.

*** Prototype labeled material-pair dataset derived from representative
*** IOCL/ONGC records - with a dataset this small, the reported metrics
*** are prototype-level validation only, not a statistically meaningful
*** accuracy claim.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from app.db.base import Base  # noqa: F401 - registers every model so relationship() string refs resolve

from app.ai.ml_ranker import FEATURE_ORDER, reset_model_cache
from app.core.config import settings
from app.db.session import SessionLocal
from app.ml.build_training_dataset import build_dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RANDOM_SEED = 42
TRAIN_FRACTION = 0.7
VAL_FRACTION = 0.15
# TEST_FRACTION is whatever remains (~0.15)


def _split_by_material(df, seed: int = RANDOM_SEED):
    """Splits at the MATERIAL level, not the pair level, so no material's
    pairs can appear in more than one split (spec's data-leakage requirement).
    A pair is kept only if both its materials landed in the same split."""
    materials = sorted(set(df["material_a"]) | set(df["material_b"]))
    train_mats, rest_mats = train_test_split(materials, train_size=TRAIN_FRACTION, random_state=seed)
    val_size = VAL_FRACTION / (1 - TRAIN_FRACTION)
    val_mats, test_mats = train_test_split(rest_mats, train_size=val_size, random_state=seed)

    train_set, val_set, test_set = set(train_mats), set(val_mats), set(test_mats)

    def _assign(row):
        a, b = row["material_a"], row["material_b"]
        for name, s in (("train", train_set), ("val", val_set), ("test", test_set)):
            if a in s and b in s:
                return name
        return None  # pair straddles two splits - dropped to avoid leakage

    df = df.copy()
    df["split"] = df.apply(_assign, axis=1)
    dropped = int(df["split"].isna().sum())
    if dropped:
        logger.info("Dropped %d pair(s) straddling two splits (avoids leakage)", dropped)
    return df.dropna(subset=["split"])


def _evaluate(model, X, y) -> dict:
    if len(y) == 0:
        return {"note": "empty split - no metrics computed"}
    preds = model.predict(X)
    metrics = {
        "n": len(y),
        "positives": int(sum(y)),
        "negatives": int(len(y) - sum(y)),
        "accuracy": round(accuracy_score(y, preds), 4),
        "precision": round(precision_score(y, preds, zero_division=0), 4),
        "recall": round(recall_score(y, preds, zero_division=0), 4),
        "f1": round(f1_score(y, preds, zero_division=0), 4),
    }
    if len(set(y)) == 2:
        proba = model.predict_proba(X)[:, 1]
        metrics["roc_auc"] = round(roc_auc_score(y, proba), 4)
    else:
        metrics["roc_auc"] = None
        metrics["roc_auc_note"] = "only one class present in this split - ROC-AUC undefined"
    return metrics


def train() -> dict:
    import xgboost as xgb

    db = SessionLocal()
    try:
        logger.info("Building labeled dataset from IOCL/ONGC materials in the central materials table ...")
        df = build_dataset(db)
    finally:
        db.close()

    if df.empty:
        raise RuntimeError("No labeled pairs could be built - check source database connectivity/seed data.")

    df = _split_by_material(df)
    train_df = df[df["split"] == "train"]
    val_df = df[df["split"] == "val"]
    test_df = df[df["split"] == "test"]

    X_train, y_train = train_df[FEATURE_ORDER], train_df["label"]
    X_val, y_val = val_df[FEATURE_ORDER], val_df["label"]
    X_test, y_test = test_df[FEATURE_ORDER], test_df["label"]

    n_pos = int((df["label"] == 1).sum())
    n_neg = int((df["label"] == 0).sum())
    train_pos = int(y_train.sum())
    train_neg = int(len(y_train) - train_pos)
    scale_pos_weight = (train_neg / train_pos) if train_pos else 1.0

    params = dict(
        n_estimators=150,
        max_depth=3,
        learning_rate=0.1,
        min_child_weight=2,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
        random_state=RANDOM_SEED,
    )
    logger.info("Training XGBClassifier with params: %s", params)
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train)

    val_metrics = _evaluate(model, X_val, y_val) if len(X_val) else {"note": "empty validation split"}
    test_metrics = _evaluate(model, X_test, y_test) if len(X_test) else {"note": "empty test split"}

    os.makedirs(os.path.dirname(settings.XGB_MODEL_PATH), exist_ok=True)
    model.save_model(settings.XGB_MODEL_PATH)
    reset_model_cache()  # so the running API process (or this one) picks up the new model immediately

    report = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_label": "Prototype labeled material-pair dataset derived from representative IOCL/ONGC demo records",
        "dataset_size": len(df),
        "positive_pairs": n_pos,
        "negative_pairs": n_neg,
        "split_sizes": {"train": len(train_df), "val": len(val_df), "test": len(test_df)},
        "split_material_counts": {
            "train": len(set(train_df["material_a"]) | set(train_df["material_b"])),
            "val": len(set(val_df["material_a"]) | set(val_df["material_b"])),
            "test": len(set(test_df["material_a"]) | set(test_df["material_b"])),
        },
        "features": FEATURE_ORDER,
        "params": params,
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "model_path": settings.XGB_MODEL_PATH,
        "note": (
            "Dataset is small (prototype scale); metrics are prototype-level validation only, "
            "not a statistically meaningful accuracy claim."
        ),
    }

    metrics_path = settings.XGB_MODEL_PATH.rsplit(".", 1)[0] + ".metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    report["metrics_path"] = metrics_path

    return report


if __name__ == "__main__":
    result = train()
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0)

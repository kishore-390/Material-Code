"""
Builds a labeled material-pair training dataset from the IOCL/ONGC
material records already present in the application's own `materials`
table (the source of truth since the demo per-CPSE source databases and
their connectors were retired - no live external fetch is needed or
possible anymore).

*** Prototype labeled material-pair dataset derived from representative
*** IOCL/ONGC demo records - not real production CPSE data.

Labeling is a reproducible rule, not hand-picked pairs:

  POSITIVE      cross-CPSE pair whose NORMALIZED category AND NORMALIZED
                specification are identical - the exact same oracle
                app.services.normalization already uses at inference
                time, applied here as a strict equality gate.
  HARD NEGATIVE same normalized category, different normalized
                specification (e.g. two pipes of different grade/standard)
                - stops the model from learning the trivial shortcut
                "same category => match".
  EASY NEGATIVE different normalized category entirely
                (e.g. pipe vs drilling equipment) - the spec's own
                "pipe vs drill bit" example.

Every pair's features are the exact six ScoreBreakdown components the
live pipeline already computes via analyzer._score_pair - not a separate
feature path - so the model trains on precisely what it sees at
inference time. Material codes are never a feature.
"""
import logging
import random

import pandas as pd
from sqlalchemy.orm import Session

from app.ai.analyzer import _attributes_dict, _score_pair, ensure_embeddings
from app.ai.ml_ranker import extract_features
from app.models.cpse import CPSEOrganization
from app.models.material import Material

logger = logging.getLogger(__name__)

RANDOM_SEED = 42
MIN_EASY_NEGATIVES = 20
TRAINING_CPSES = ("IOCL", "ONGC")


def sync_all_sources(db: Session) -> dict[str, Material]:
    """Loads every IOCL/ONGC material already present in the application's
    own `materials` table. Returns {"CPSE:CODE": Material}."""
    materials: dict[str, Material] = {}
    rows = (
        db.query(Material)
        .join(CPSEOrganization, Material.cpse_id == CPSEOrganization.id)
        .filter(CPSEOrganization.code.in_(TRAINING_CPSES))
        .all()
    )
    for m in rows:
        materials[f"{m.cpse.code}:{m.material_code}"] = m
    return materials


def build_labeled_pairs(materials: dict[str, Material], seed: int = RANDOM_SEED) -> list[tuple[str, str, int, str]]:
    """Returns [(key_a, key_b, label, reason), ...] over IOCL x ONGC cross-source pairs only."""
    iocl_keys = sorted(k for k in materials if k.startswith("IOCL:"))
    ongc_keys = sorted(k for k in materials if k.startswith("ONGC:"))

    positives: list[tuple[str, str, int, str]] = []
    hard_negatives: list[tuple[str, str, int, str]] = []
    easy_negatives: list[tuple[str, str, int, str]] = []

    for ka in iocl_keys:
        a = materials[ka]
        for kb in ongc_keys:
            b = materials[kb]
            same_category = bool(a.normalized_category) and a.normalized_category == b.normalized_category
            if same_category:
                same_spec = bool(a.normalized_specification) and a.normalized_specification == b.normalized_specification
                if same_spec:
                    positives.append((ka, kb, 1, "same normalized category + specification"))
                else:
                    hard_negatives.append((ka, kb, 0, "same category, different specification"))
            else:
                easy_negatives.append((ka, kb, 0, "different category"))

    rng = random.Random(seed)
    target_easy = min(len(easy_negatives), max(len(positives) + len(hard_negatives), MIN_EASY_NEGATIVES))
    sampled_easy = rng.sample(easy_negatives, target_easy) if easy_negatives else []

    logger.info(
        "Pair candidates: %d positive, %d hard-negative, %d easy-negative (sampled %d of %d available)",
        len(positives), len(hard_negatives), len(sampled_easy), len(sampled_easy), len(easy_negatives),
    )
    return positives + hard_negatives + sampled_easy


def compute_feature_rows(
    db: Session, materials: dict[str, Material], pairs: list[tuple[str, str, int, str]]
) -> pd.DataFrame:
    unique_keys = {k for pair in pairs for k in (pair[0], pair[1])}
    embeddings = {}
    attrs_cache = {}
    for key in unique_keys:
        m = materials[key]
        embeddings[key] = ensure_embeddings(db, m)
        attrs_cache[key] = _attributes_dict(db, m.id)

    rows = []
    for key_a, key_b, label, reason in pairs:
        a, b = materials[key_a], materials[key_b]
        breakdown, _ = _score_pair(db, a, embeddings[key_a], attrs_cache[key_a], b)
        row = extract_features(breakdown)
        row.update(
            {
                "label": label,
                "material_a": key_a,
                "material_b": key_b,
                "reason": reason,
                "description_a": a.description,
                "description_b": b.description,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_dataset(db: Session) -> pd.DataFrame:
    materials = sync_all_sources(db)
    pairs = build_labeled_pairs(materials)
    return compute_feature_rows(db, materials, pairs)

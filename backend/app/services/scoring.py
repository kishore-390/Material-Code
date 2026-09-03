"""
Explainable weighted similarity scoring (spec section 8).

Every comparison between two materials produces six component scores
(0-100) plus a final weighted score. Nothing here is a black box: each
component is a small, inspectable function so the frontend "Why did AI
match these materials?" panel can show a human-readable breakdown.
"""
import difflib
from dataclasses import dataclass

import numpy as np

from app.services.settings_service import get_effective_weights


@dataclass
class ScoreBreakdown:
    final_score: float
    description_score: float
    specification_score: float
    category_score: float
    uom_score: float
    image_score: float
    attribute_score: float

    def as_dict(self) -> dict:
        return {
            "final_score": round(self.final_score, 2),
            "description_score": round(self.description_score, 2),
            "specification_score": round(self.specification_score, 2),
            "category_score": round(self.category_score, 2),
            "uom_score": round(self.uom_score, 2),
            "image_score": round(self.image_score, 2),
            "attribute_score": round(self.attribute_score, 2),
        }


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


def category_score(norm_a: str, norm_b: str) -> float:
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


def image_score(embedding_a: list[float] | None, embedding_b: list[float] | None) -> float:
    cos = cosine_similarity(embedding_a, embedding_b)
    if cos is None:
        return 0.0
    return round(cos * 100.0, 2)


def compute_final_score(
    description_score: float,
    specification_score: float,
    category_score_: float,
    uom_score_: float,
    image_score_: float,
    attribute_score_: float,
    has_image_both_sides: bool,
    weights: dict | None = None,
) -> ScoreBreakdown:
    weights = weights or get_effective_weights()
    w_desc = weights["description"]
    w_spec = weights["specification"]
    w_cat = weights["category"]
    w_uom = weights["uom"]
    w_img = weights["image"]
    w_attr = weights["attributes"]

    if not has_image_both_sides:
        # Redistribute the image weight proportionally across the remaining components
        # rather than penalizing a material simply for lacking a photo.
        remaining = w_desc + w_spec + w_cat + w_uom + w_attr
        scale = (remaining + w_img) / remaining if remaining else 1.0
        w_desc, w_spec, w_cat, w_uom, w_attr = (w * scale for w in (w_desc, w_spec, w_cat, w_uom, w_attr))
        w_img = 0.0
        image_score_ = 0.0

    final = (
        description_score * w_desc
        + specification_score * w_spec
        + category_score_ * w_cat
        + uom_score_ * w_uom
        + image_score_ * w_img
        + attribute_score_ * w_attr
    )
    return ScoreBreakdown(
        final_score=round(final, 2),
        description_score=description_score,
        specification_score=specification_score,
        category_score=category_score_,
        uom_score=uom_score_,
        image_score=image_score_,
        attribute_score=attribute_score_,
    )

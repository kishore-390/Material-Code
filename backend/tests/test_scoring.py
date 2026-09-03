from app.services.scoring import (
    attribute_score,
    category_score,
    compute_final_score,
    cosine_similarity,
    text_ratio,
    uom_score,
)

WEIGHTS = {
    "description": 0.30, "specification": 0.25, "category": 0.15,
    "uom": 0.10, "image": 0.15, "attributes": 0.05,
}


def test_text_ratio_identical_strings_is_100():
    assert text_ratio("CARBON STEEL PIPE", "CARBON STEEL PIPE") == 100.0


def test_text_ratio_empty_vs_value_is_zero():
    assert text_ratio("", "SOMETHING") == 0.0


def test_category_score_exact_match():
    assert category_score("PIPE", "PIPE") == 100.0


def test_category_score_mismatch_is_low():
    assert category_score("PIPE", "VALVE") < 50.0


def test_uom_score_exact_match():
    assert uom_score("METER", "METER") == 100.0


def test_uom_score_mismatch_is_zero():
    assert uom_score("METER", "KILOGRAM") == 0.0


def test_attribute_score_identical_dicts():
    assert attribute_score({"Schedule": "SCH 40"}, {"Schedule": "SCH 40"}) == 100.0


def test_attribute_score_both_empty():
    assert attribute_score({}, {}) == 100.0


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0]) - 0.5) < 1e-6


def test_compute_final_score_weights_applied_with_image():
    breakdown = compute_final_score(
        description_score=100, specification_score=100, category_score_=100,
        uom_score_=100, image_score_=100, attribute_score_=100,
        has_image_both_sides=True, weights=WEIGHTS,
    )
    assert breakdown.final_score == 100.0


def test_compute_final_score_redistributes_weight_without_image():
    breakdown = compute_final_score(
        description_score=100, specification_score=100, category_score_=100,
        uom_score_=100, image_score_=0, attribute_score_=100,
        has_image_both_sides=False, weights=WEIGHTS,
    )
    # No image on either side should not penalize the pair - still a perfect match.
    assert breakdown.final_score == 100.0
    assert breakdown.image_score == 0.0


def test_compute_final_score_partial_match_example():
    breakdown = compute_final_score(
        description_score=98, specification_score=97, category_score_=100,
        uom_score_=100, image_score_=94, attribute_score_=95,
        has_image_both_sides=True, weights=WEIGHTS,
    )
    expected = 98 * 0.30 + 97 * 0.25 + 100 * 0.15 + 100 * 0.10 + 94 * 0.15 + 95 * 0.05
    assert abs(breakdown.final_score - expected) < 0.01

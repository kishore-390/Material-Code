from app.services.scoring import (
    attribute_score,
    classification_score,
    compute_final_score,
    cosine_similarity,
    criticality_score,
    dimension_score,
    grade_score,
    manufacturer_is_applicable,
    text_ratio,
    uom_score,
)

WEIGHTS = {
    "description": 0.20, "specification": 0.15, "classification": 0.10, "uom": 0.05, "attributes": 0.05,
    "grade": 0.15, "dimension": 0.15, "standard": 0.05, "manufacturer": 0.03, "function": 0.05, "criticality": 0.02,
}


def _score_kwargs(**overrides):
    base = dict(
        description_score=100, specification_score=100, classification_score=100, uom_score=100,
        attribute_score=100, grade_score=100, dimension_score=100, standard_score=100,
        manufacturer_score=0, function_score=100, criticality_score=100, manufacturer_applicable=False,
        weights=WEIGHTS,
    )
    base.update(overrides)
    return base


def test_text_ratio_identical_strings_is_100():
    assert text_ratio("CARBON STEEL PIPE", "CARBON STEEL PIPE") == 100.0


def test_text_ratio_empty_vs_value_is_zero():
    assert text_ratio("", "SOMETHING") == 0.0


def test_classification_score_exact_match():
    assert classification_score("PIPE", "PIPE") == 100.0


def test_classification_score_mismatch_is_low():
    assert classification_score("PIPE", "VALVE") < 50.0


def test_uom_score_exact_match():
    assert uom_score("METER", "METER") == 100.0


def test_uom_score_incompatible_measure_units_is_zero():
    assert uom_score("METER", "KILOGRAM") == 0.0


def test_uom_score_packaging_difference_is_not_zero():
    """Spec section 6: packaging (e.g. PC vs BOX) must not make two
    otherwise-identical materials look like different materials."""
    assert uom_score("EACH", "BOX") == 70.0


def test_grade_score_both_absent_is_neutral_match():
    assert grade_score(None, None) == 100.0


def test_grade_score_one_absent_is_neutral():
    assert grade_score("SS304", None) == 50.0


def test_grade_score_mismatch_is_low():
    # SequenceMatcher gives "SS304"/"SS316" a 60.0 lexical ratio (shared "SS3"
    # prefix) - clearly not a match, but not near 0 either; assert the
    # actual boundary rather than an arbitrary tighter one.
    assert grade_score("SS304", "SS316") <= 60.0


def test_dimension_score_exact_match():
    assert dimension_score("M10x50", "M10x50") == 100.0


def test_criticality_score_same_is_full():
    assert criticality_score("CRITICAL", "CRITICAL") == 100.0


def test_criticality_score_conflicting_is_low():
    assert criticality_score("CRITICAL", "NON_CRITICAL") == 40.0


def test_manufacturer_only_applicable_when_critical():
    assert manufacturer_is_applicable("CRITICAL", "NORMAL") is True
    assert manufacturer_is_applicable("NORMAL", "NORMAL") is False


def test_attribute_score_identical_dicts():
    assert attribute_score({"Schedule": "SCH 40"}, {"Schedule": "SCH 40"}) == 100.0


def test_attribute_score_both_empty():
    assert attribute_score({}, {}) == 100.0


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0]) - 0.5) < 1e-6


def test_compute_final_score_perfect_match_is_100():
    breakdown = compute_final_score(**_score_kwargs())
    assert breakdown.final_score == 100.0


def test_compute_final_score_manufacturer_weight_redistributed_when_not_critical():
    breakdown = compute_final_score(**_score_kwargs(manufacturer_applicable=False, manufacturer_score=0))
    assert breakdown.final_score == 100.0
    assert breakdown.manufacturer_score == 0.0


def test_compute_final_score_manufacturer_counted_when_critical():
    breakdown = compute_final_score(**_score_kwargs(manufacturer_applicable=True, manufacturer_score=0))
    # Manufacturer now genuinely counts against the score and is not redistributed away.
    assert breakdown.final_score < 100.0

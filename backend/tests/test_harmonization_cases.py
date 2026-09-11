"""
The six required fixture cases from spec section 42, exercised through the
REAL end-to-end pipeline (app.ai.analyzer.analyze_material) - normalization,
embeddings, pgvector candidate retrieval, weighted scoring, technical
conflict detection, XGBoost blend (falls back cleanly with no trained
model) and the decision engine - never a mocked/shortcut decision.

Assertions on decision CATEGORY are intentionally scoped to "equivalent vs
not" where the spec's own wording is a range ("IDENTICAL / EQUIVALENT",
"Equivalent if technical specifications are consistent") rather than a
single exact label, since exact scores can shift slightly between the real
SBERT model and the deterministic mock fallback (see app.ai.text_embeddings)
depending on what's available in a given environment - the four cases with
an unambiguous required outcome (technical conflict / not equivalent) are
asserted exactly.
"""
import uuid

from app.ai.analyzer import analyze_material
from tests.conftest import create_cpse_material, create_cpse

_EQUIVALENT_DECISIONS = {"IDENTICAL", "DUPLICATE", "NEAR_DUPLICATE", "FUNCTIONALLY_EQUIVALENT"}


def _analyze_pair(db_session, a, b):
    """Candidate must be analyzed (embedded) first so it is findable when
    the primary material's own analysis runs its pgvector candidate search."""
    analyze_material(db_session, b.id)
    return analyze_material(db_session, a.id)


def test_case1_identical_bolts_different_wording_are_equivalent(db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    a = create_cpse_material(
        db_session, iocl, code="IOCL001", description="SS Hex Bolt M10x50",
        classification="Fastener", uom="PC", specification="SS304 ASTM F593 PC",
        material_grade="SS304", dimensions="M10x50", standard="ASTM F593",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC001", description="Stainless Steel Bolt 10mm x 50mm",
        classification="Fastener", uom="PC", specification="SS304 ASTM F593 PC",
        material_grade="SS304", dimensions="M10x50", standard="ASTM F593",
    )

    analysis = _analyze_pair(db_session, a, b)
    assert analysis.decision in _EQUIVALENT_DECISIONS
    assert analysis.technical_conflict is False


def test_case2_ball_bearings_are_equivalent(db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    a = create_cpse_material(
        db_session, iocl, code="IOCL002", description="Ball Bearing 6205",
        classification="Bearing", uom="EACH", dimensions="6205", function="Rotational Support",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC002", description="Deep Groove Ball Bearing 6205",
        classification="Bearing", uom="EACH", dimensions="6205", function="Rotational Support",
    )

    analysis = _analyze_pair(db_session, a, b)
    assert analysis.decision in _EQUIVALENT_DECISIONS


def test_case3_different_valve_sizes_is_technical_conflict(db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    a = create_cpse_material(
        db_session, iocl, code="IOCL003", description="Gate Valve 2 inch",
        classification="Valve", uom="EACH", dimensions="2 inch",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC003", description="Gate Valve 3 inch",
        classification="Valve", uom="EACH", dimensions="3 inch",
    )

    analysis = _analyze_pair(db_session, a, b)
    assert analysis.decision == "TECHNICAL_CONFLICT"
    assert analysis.technical_conflict is True


def test_case4_unrelated_materials_are_not_equivalent(db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    a = create_cpse_material(
        db_session, iocl, code="IOCL004", description="Electrical Cable",
        classification="Cable", uom="METER", function="Power Transmission",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC004", description="Industrial Pump",
        classification="Pump", uom="EACH", function="Fluid Transfer",
    )

    analysis = _analyze_pair(db_session, a, b)
    assert analysis.decision == "NOT_EQUIVALENT"


def test_case5_different_grade_bolts_is_technical_conflict(db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    a = create_cpse_material(
        db_session, iocl, code="IOCL005", description="SS Bolt M10x50 SS304",
        classification="Fastener", uom="PC", material_grade="SS304",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC005", description="SS Bolt M10x50 SS316",
        classification="Fastener", uom="PC", material_grade="SS316",
    )

    analysis = _analyze_pair(db_session, a, b)
    assert analysis.decision == "TECHNICAL_CONFLICT"
    assert analysis.technical_conflict is True


def test_case6_packaging_difference_is_not_a_conflict(db_session, seed_roles_and_cpse):
    """Spec section 6/42: packaging/pack size must never make two otherwise
    identical materials look like different materials, and must never be
    treated as a technical conflict."""
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    a = create_cpse_material(
        db_session, iocl, code="IOCL006", description="Bolt M10x50",
        classification="Fastener", uom="PC", dimensions="M10x50", packaging="Loose, Pack of 1",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC006", description="Bolt M10x50",
        classification="Fastener", uom="BOX", dimensions="M10x50", packaging="Box of 100",
    )

    analysis = _analyze_pair(db_session, a, b)
    assert analysis.technical_conflict is False
    assert analysis.decision in _EQUIVALENT_DECISIONS

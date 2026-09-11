"""
Tests for app.services.duplicate_code_service - duplicate SOURCE MATERIAL
CODE detection (the same literal original_material_code string supplied by
two or more different CPSEs). A deliberately separate concept from
app.services.duplicate_service (AI-detected material equivalence) - see
test_duplicate_materials.py for that feature's tests.
"""
from app.ai.analyzer import analyze_material
from tests.conftest import create_cpse, create_cpse_material, register_and_login


def test_empty_database_has_no_duplicate_codes(client, seed_roles_and_cpse):
    headers = register_and_login(client, "dupcode_empty_admin", "ADMIN")
    resp = client.get("/api/legacy-codes", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["total_duplicate_codes"] == 0
    assert body["cpses_affected"] == 0
    assert body["materials_affected"] == 0


def test_two_cpses_sharing_one_code_is_detected(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dupcode_two_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    create_cpse_material(db_session, iocl, code="100245", description="SS Hex Bolt M10x50", classification="Fastener", uom="Nos")
    create_cpse_material(db_session, ongc, code="100245", description="Something Entirely Different", classification="Electronics", uom="Nos")

    resp = client.get("/api/legacy-codes", headers=headers)
    body = resp.json()
    assert body["total_duplicate_codes"] == 1
    assert body["cpses_affected"] == 2
    assert body["materials_affected"] == 2
    assert set(body["items"][0]["cpses"]) == {"IOCL", "ONGC"}


def test_code_unique_to_one_cpse_is_not_flagged(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dupcode_unique_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    create_cpse_material(db_session, iocl, code="ONLY-IOCL-001", description="Solo material", classification="Fastener", uom="Nos")

    resp = client.get("/api/legacy-codes", headers=headers)
    assert resp.json()["total_duplicate_codes"] == 0

    detail = client.get("/api/legacy-codes/ONLY-IOCL-001", headers=headers)
    assert detail.status_code == 404


def test_classify_pair_ai_technical_equivalence_when_common_material_shared(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dupcode_equiv_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    a = create_cpse_material(
        db_session, iocl, code="SAME-CODE-EQ", description="Carbon Steel Gate Valve",
        specification="API 600 Class 150", classification="Valve", uom="Nos",
    )
    b = create_cpse_material(
        db_session, ongc, code="SAME-CODE-EQ", description="CS Gate Valve",
        specification="API 600 Class 150", classification="Valve", uom="Nos",
    )
    # b is analyzed first, before a has an embedding to be found as a
    # candidate, so b's own first pass finds nothing and gets no mapping;
    # a (analyzed second) finds b and gets one. Re-analyzing b settles it
    # onto the same common material now that a is embedded - exactly the
    # eventual-consistency behavior app.api.endpoints.harmonization's
    # rescan exists for (see analyze_material/_handle_decision).
    analyze_material(db_session, b.id)
    analyze_material(db_session, a.id)
    analyze_material(db_session, b.id)

    detail = client.get("/api/legacy-codes/SAME-CODE-EQ", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["pairs"]) == 1
    assert body["pairs"][0]["classification"] == "AI_TECHNICAL_EQUIVALENCE"


def test_classify_pair_technical_conflict_on_real_mismatch(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dupcode_conflict_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    create_cpse_material(db_session, iocl, code="SAME-CODE-CONFLICT", description="SS Bolt M10x50 SS304", classification="Fastener", uom="Nos", material_grade="SS304")
    create_cpse_material(db_session, ongc, code="SAME-CODE-CONFLICT", description="SS Bolt M10x50 SS316", classification="Fastener", uom="Nos", material_grade="SS316")

    detail = client.get("/api/legacy-codes/SAME-CODE-CONFLICT", headers=headers)
    assert detail.json()["pairs"][0]["classification"] == "TECHNICAL_CONFLICT"


def test_classify_pair_same_source_code_when_no_ai_relationship_established(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dupcode_neutral_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    create_cpse_material(db_session, iocl, code="SAME-CODE-NEUTRAL", description="Widget Type A", classification="Misc", uom="Nos")
    create_cpse_material(db_session, ongc, code="SAME-CODE-NEUTRAL", description="Completely Unrelated Gadget", classification="Misc", uom="Nos")

    detail = client.get("/api/legacy-codes/SAME-CODE-NEUTRAL", headers=headers)
    assert detail.json()["pairs"][0]["classification"] == "SAME_SOURCE_CODE"


def test_unknown_duplicate_code_returns_404(client, seed_roles_and_cpse):
    headers = register_and_login(client, "dupcode_404_admin", "ADMIN")
    resp = client.get("/api/legacy-codes/DOES-NOT-EXIST", headers=headers)
    assert resp.status_code == 404

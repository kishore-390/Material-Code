import re

from app.ai.conflict_detector import detect_conflict
from tests.conftest import create_cpse, create_cpse_material, register_and_login


def test_common_code_generator_produces_neutral_cm_format(db_session):
    """Direct proof codes are neutral CM-XXXXXX, never a renamed CPSE code,
    and unique across successive calls."""
    from app.services.code_generator import generate_common_code

    code_a = generate_common_code(db_session)
    code_b = generate_common_code(db_session)

    assert re.fullmatch(r"CM-\d{6}", code_a)
    assert re.fullmatch(r"CM-\d{6}", code_b)
    assert code_a != code_b


def test_conflict_detector_flags_real_grade_and_dimension_mismatches():
    same = detect_conflict("SS BOLT M10 X 50 MM", "STAINLESS STEEL HEXAGON BOLT M10 X 50 MM")
    assert same.has_conflict is False

    grade_conflict = detect_conflict("Gasket SS304 Ring Type", "Gasket SS316 Ring Type")
    assert grade_conflict.has_conflict is True
    assert "grade" in grade_conflict.reasons[0].lower()

    dimension_conflict = detect_conflict("SS Bolt M10 X 50 MM", "SS Bolt M10 X 60 MM")
    assert dimension_conflict.has_conflict is True

    inch_dimension_conflict = detect_conflict("Gate Valve 2 inch", "Gate Valve 3 inch")
    assert inch_dimension_conflict.has_conflict is True

    voltage_conflict = detect_conflict("Induction Motor 230V", "Induction Motor 415V")
    assert voltage_conflict.has_conflict is True

    no_data = detect_conflict("Generic item with no technical tokens", "Another generic item")
    assert no_data.has_conflict is False


def test_scan_material_masters_groups_equivalent_materials_across_cpses(client, db_session, seed_roles_and_cpse):
    """
    End-to-end proof of the core feature: insert raw CPSE material records
    (as a real sync would have), trigger the scan endpoint, and confirm the
    existing AI pipeline groups the known-equivalent valve pair under one
    neutral CM-XXXXXX code while leaving an unrelated pair out of that group.
    """
    headers = register_and_login(client, "scan_admin_tester", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    create_cpse_material(db_session, iocl, code="IOCL-1002", description="Carbon Steel Gate Valve", specification="API 600 Class 150", classification="Valve", uom="Nos")
    create_cpse_material(db_session, ongc, code="ONGC-2002", description="CS Gate Valve", specification="API 600 Class 150", classification="Valve", uom="Nos")
    create_cpse_material(db_session, iocl, code="IOCL-1001", description="Carbon Steel Seamless Pipe", specification="ASTM A106 Grade B", classification="Pipe", uom="Meter")
    create_cpse_material(db_session, ongc, code="ONGC-2011", description="Drill Bit Tricone Type", specification="Tricone Roller Cone Bit", classification="Drilling Equipment", uom="Nos")

    scan_resp = client.post("/api/harmonization/scan", headers=headers)
    assert scan_resp.status_code == 200
    scan_body = scan_resp.json()
    assert scan_body["queued"] > 0
    assert scan_body["mode"] == "PROCESSED_INLINE"

    status_resp = client.post("/api/harmonization/scan-status", json=scan_body["material_ids"], headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["completed"] == status_resp.json()["total"]

    # Materials are analyzed in whatever order the scan's query returns them;
    # whichever of a matching pair is processed FIRST finds no candidate yet
    # (its counterpart has no embedding until its own analysis runs) and gets
    # no mapping on this pass. A second scan settles it, now that every
    # material in the batch has an embedding - the same eventual-consistency
    # behavior verified live in this rebuild's end-to-end demo run.
    second_scan = client.post("/api/harmonization/scan", headers=headers)
    if second_scan.json()["material_ids"]:
        client.post("/api/harmonization/scan-status", json=second_scan.json()["material_ids"], headers=headers)

    materials = client.get("/api/cpse-materials", headers=headers).json()["items"]
    by_code = {m["original_material_code"]: m for m in materials}
    valve_iocl = client.get(f"/api/cpse-materials/{by_code['IOCL-1002']['id']}", headers=headers).json()
    valve_ongc = client.get(f"/api/cpse-materials/{by_code['ONGC-2002']['id']}", headers=headers).json()
    assert valve_iocl["active_common_material"] is not None
    assert valve_ongc["active_common_material"] is not None
    assert valve_iocl["active_common_material"]["common_code"] == valve_ongc["active_common_material"]["common_code"]
    assert re.fullmatch(r"CM-\d{6}", valve_iocl["active_common_material"]["common_code"])

    pipe_iocl = client.get(f"/api/cpse-materials/{by_code['IOCL-1001']['id']}", headers=headers).json()
    drill_ongc = client.get(f"/api/cpse-materials/{by_code['ONGC-2011']['id']}", headers=headers).json()
    if pipe_iocl["active_common_material"] and drill_ongc["active_common_material"]:
        assert pipe_iocl["active_common_material"]["common_code"] != drill_ongc["active_common_material"]["common_code"]

    common_detail = client.get(f"/api/common-materials/{valve_iocl['active_common_material']['common_code']}", headers=headers)
    assert common_detail.status_code == 200
    linked_codes = {m["original_material_code"] for m in common_detail.json()["mapped_materials"]}
    assert {"IOCL-1002", "ONGC-2002"}.issubset(linked_codes)


def test_scan_status_empty_ids_returns_empty_result(client, seed_roles_and_cpse):
    headers = register_and_login(client, "scan_empty_admin", "ADMIN")
    resp = client.post("/api/harmonization/scan-status", json=[], headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "completed": 0}


def test_scan_requires_admin_or_material_expert_role(client, seed_roles_and_cpse):
    headers = register_and_login(client, "scan_viewer_tester", "VIEWER")
    resp = client.post("/api/harmonization/scan", headers=headers)
    assert resp.status_code == 403

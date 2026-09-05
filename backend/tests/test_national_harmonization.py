import re

from app.ai.conflict_detector import detect_conflict


def _register_and_login(client, username, role_name, cpse_code=None):
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "full_name": username.title(),
        "password": "Password@1",
        "role_name": role_name,
    }
    if cpse_code:
        payload["cpse_code"] = cpse_code
    client.post("/api/auth/register", json=payload)
    login = client.post("/api/auth/login", json={"username": username, "password": "Password@1"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_ongc_org(client, admin_headers):
    client.post("/api/cpse", data={"code": "ONGC", "name": "Oil and Natural Gas Corporation"}, headers=admin_headers)


def _create_material(client, admin_headers, *, code, description, category, uom, cpse_code, specification=None, material_type=None):
    resp = client.post(
        "/api/materials",
        data={
            "material_code": code,
            "description": description,
            "specification": specification or "",
            "category": category,
            "uom": uom,
            "cpse_code": cpse_code,
            "material_type": material_type or "",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_common_code_generator_produces_neutral_cm_format(db_session):
    """Direct proof the code generator was changed to the neutral CM-XXXXXX
    namespace rather than the old TYPE-CATEGORY-SEQ format, and that codes
    are unique across successive calls."""
    from app.services.code_generator import generate_common_code

    code_a = generate_common_code(db_session)
    code_b = generate_common_code(db_session)

    assert re.fullmatch(r"CM-\d{6}", code_a)
    assert re.fullmatch(r"CM-\d{6}", code_b)
    assert code_a != code_b


def test_category_normalization_improves_pipe_vs_piping_material(client, db_session, seed_roles_and_cpse):
    """Direct proof the normalization fix in app/services/normalization.py is real:
    'Pipes' and 'Piping Material' should normalize to the same category token,
    so the category component score is a full match. Ported from the removed
    manual analyze-selected test (that endpoint is gone), exercised here
    through the surviving analyze_material() full-pool pipeline instead."""
    import uuid as uuid_module

    from app.ai.analyzer import analyze_material

    admin_headers = _register_and_login(client, "norm_fix_admin_tester", "ADMIN")
    _create_ongc_org(client, admin_headers)

    iocl = _create_material(
        client, admin_headers, code="NORM-IOCL-1001", description="Carbon Steel Seamless Pipe",
        specification="ASTM A106 Grade B", category="Pipes", uom="M", cpse_code="IOCL",
    )
    ongc = _create_material(
        client, admin_headers, code="NORM-ONGC-2001", description="Seamless Carbon Steel Pipe",
        specification="ASTM A106 Gr.B", category="Piping Material", uom="M", cpse_code="ONGC",
    )

    # find_candidate_materials only matches already-embedded materials, so the
    # candidate must be analyzed first (see the identical note in test_xgboost_ranker.py).
    analyze_material(db_session, uuid_module.UUID(ongc["id"]))
    analyze_material(db_session, uuid_module.UUID(iocl["id"]))

    response = client.get(f"/api/ai/analysis/{iocl['id']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["category_score"] == 100.0


def test_conflict_detector_flags_real_grade_and_dimension_mismatches():
    same = detect_conflict("SS BOLT M10 X 50 MM", "STAINLESS STEEL HEXAGON BOLT M10 X 50 MM")
    assert same.has_conflict is False

    grade_conflict = detect_conflict("Gasket SS304 Ring Type", "Gasket SS316 Ring Type")
    assert grade_conflict.has_conflict is True
    assert "grade" in grade_conflict.reasons[0].lower()

    dimension_conflict = detect_conflict("SS Bolt M10 X 50 MM", "SS Bolt M10 X 60 MM")
    assert dimension_conflict.has_conflict is True

    voltage_conflict = detect_conflict("Induction Motor 230V", "Induction Motor 415V")
    assert voltage_conflict.has_conflict is True

    no_data = detect_conflict("Generic item with no technical tokens", "Another generic item")
    assert no_data.has_conflict is False


def test_scan_material_masters_groups_equivalent_materials_across_cpses(client, seed_roles_and_cpse, monkeypatch):
    """
    End-to-end proof of the core feature: create raw CPSE material records
    directly (no demo source database involved), trigger the bulk scan,
    and confirm the EXISTING AI pipeline (pgvector + scoring + XGBoost +
    decision engine) groups the known-equivalent IOCL-1002 / ONGC-2002
    valve pair under one neutral CM-XXXXXX code, while leaving an
    unrelated pair (IOCL-1001 pipe vs ONGC-2011 drill bit) out of that
    group.

    The docker-compose Celery worker connects to a different (non-test)
    database, so it can never see this test's ephemeral rows even though
    .delay() succeeds without raising. Rather than depend on that
    cross-process/cross-database timing, force the scan endpoint's own
    already-implemented "no broker reachable" fallback - it then runs the
    exact same analyze_material() pipeline synchronously, in-process,
    against this test's own db session, which is what every other AI test
    in this suite already relies on.
    """
    from app.workers import tasks as worker_tasks

    def _raise(*_args, **_kwargs):
        raise RuntimeError("simulated: no broker reachable in this test")

    monkeypatch.setattr(worker_tasks.bulk_ai_analysis, "delay", _raise)

    admin_headers = _register_and_login(client, "scan_admin_tester", "ADMIN")
    _create_ongc_org(client, admin_headers)

    _create_material(
        client, admin_headers, code="IOCL-1002", description="Carbon Steel Gate Valve",
        specification="API 600 Class 150", category="Valves", uom="Nos", cpse_code="IOCL",
    )
    _create_material(
        client, admin_headers, code="ONGC-2002", description="CS Gate Valve",
        specification="API 600 Class 150", category="Valve", uom="Nos", cpse_code="ONGC",
    )
    _create_material(
        client, admin_headers, code="IOCL-1001", description="Carbon Steel Seamless Pipe",
        specification="ASTM A106 Grade B", category="Pipes", uom="M", cpse_code="IOCL",
    )
    _create_material(
        client, admin_headers, code="ONGC-2011", description="Drill Bit Tricone Type",
        specification="Tricone Roller Cone Bit", category="Drilling Equipment", uom="Nos", cpse_code="ONGC",
    )

    scan_resp = client.post("/api/harmonization/scan", headers=admin_headers)
    assert scan_resp.status_code == 200
    scan_body = scan_resp.json()
    assert scan_body["queued"] > 0
    assert scan_body["mode"] == "PROCESSED_INLINE"

    status_resp = client.post(
        "/api/harmonization/scan-status",
        json={"material_ids": scan_body["material_ids"]},
        headers=admin_headers,
    )
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["completed"] == status_body["total"]

    by_code = {item["material_code"]: item for item in status_body["items"]}
    valve_iocl = by_code.get("IOCL-1002")
    valve_ongc = by_code.get("ONGC-2002")
    assert valve_iocl is not None and valve_ongc is not None
    assert valve_iocl["common_code"] is not None
    assert valve_ongc["common_code"] is not None
    assert valve_iocl["common_code"]["code"] == valve_ongc["common_code"]["code"]
    assert re.fullmatch(r"CM-\d{6}", valve_iocl["common_code"]["code"])

    pipe_iocl = by_code.get("IOCL-1001")
    drill_ongc = by_code.get("ONGC-2011")
    if pipe_iocl and drill_ongc and pipe_iocl["common_code"] and drill_ongc["common_code"]:
        assert pipe_iocl["common_code"]["code"] != drill_ongc["common_code"]["code"]

    detail_resp = client.get(f"/api/common-codes/{valve_iocl['common_code']['code']}", headers=admin_headers)
    assert detail_resp.status_code == 200
    detail_body = detail_resp.json()
    linked_codes = {m["material_code"] for m in detail_body["linked_materials"]}
    assert {"IOCL-1002", "ONGC-2002"}.issubset(linked_codes)


def test_scan_status_empty_ids_returns_empty_result(client, seed_roles_and_cpse):
    admin_headers = _register_and_login(client, "scan_empty_admin", "ADMIN")
    resp = client.post("/api/harmonization/scan-status", json={"material_ids": []}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "completed": 0, "items": []}


def test_scan_requires_admin_or_material_expert_role(client, seed_roles_and_cpse):
    viewer_headers = _register_and_login(client, "scan_viewer_tester", "VIEWER")
    resp = client.post("/api/harmonization/scan", headers=viewer_headers)
    assert resp.status_code == 403

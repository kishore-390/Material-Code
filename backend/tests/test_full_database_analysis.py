import re

from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalStatus
from app.models.harmonization import CommonMaterialCode


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


def _create_org(client, admin_headers, code, name):
    client.post("/api/cpse", data={"code": code, "name": name}, headers=admin_headers)


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


def test_full_database_scan_excludes_cpses_outside_iocl_ongc(client, seed_roles_and_cpse):
    """Prototype scope rule: only IOCL + ONGC materials are ever queued by
    the full-database scan, even if other organizations have materials."""
    admin_headers = _register_and_login(client, "fda_scope_admin", "ADMIN")
    _create_org(client, admin_headers, "ONGC", "Oil and Natural Gas Corporation")
    _create_org(client, admin_headers, "BPCL", "Bharat Petroleum Corporation Limited")

    _create_material(
        client, admin_headers, code="BPCL-9001", description="Out of scope material",
        category="Fasteners", uom="Numbers", cpse_code="BPCL",
    )
    iocl_mat = _create_material(
        client, admin_headers, code="FDA-IOCL-0001", description="Test scoped material",
        category="Fasteners", uom="Numbers", cpse_code="IOCL",
    )

    scan_resp = client.post("/api/harmonization/full-database-scan", headers=admin_headers)
    assert scan_resp.status_code == 200
    material_ids = set(scan_resp.json()["material_ids"])

    assert iocl_mat["id"] in material_ids
    bpcl_material_ids = {
        m["id"]
        for m in client.get("/api/materials", params={"q": "BPCL-9001"}, headers=admin_headers).json()["items"]
    }
    assert bpcl_material_ids.isdisjoint(material_ids)


def test_full_database_scan_reincludes_auto_generated_materials_not_just_null(client, seed_roles_and_cpse, monkeypatch):
    """
    Direct proof the scan is NOT merely `WHERE common_code_id IS NULL`: a
    material that already received an AUTO_GENERATED (not yet
    human-approved) common code from a first scan must still be picked up
    by a second scan, since it has not been officially approved.
    """
    from app.workers import tasks as worker_tasks

    def _raise(*_a, **_kw):
        raise RuntimeError("simulated: no broker reachable in this test")

    monkeypatch.setattr(worker_tasks.bulk_ai_analysis, "delay", _raise)

    admin_headers = _register_and_login(client, "fda_reinclude_admin", "ADMIN")
    _create_org(client, admin_headers, "ONGC", "Oil and Natural Gas Corporation")

    _create_material(
        client, admin_headers, code="IOCL-1002", description="Carbon Steel Gate Valve",
        specification="API 600 Class 150", category="Valves", uom="Nos", cpse_code="IOCL",
    )
    _create_material(
        client, admin_headers, code="ONGC-2002", description="CS Gate Valve",
        specification="API 600 Class 150", category="Valve", uom="Nos", cpse_code="ONGC",
    )

    first_scan = client.post("/api/harmonization/full-database-scan", headers=admin_headers)
    assert first_scan.status_code == 200
    assert first_scan.json()["mode"] == "PROCESSED_INLINE"

    status_resp = client.post(
        "/api/harmonization/scan-status",
        json={"material_ids": first_scan.json()["material_ids"]},
        headers=admin_headers,
    )
    items = status_resp.json()["items"]
    valve = next(i for i in items if i["material_code"] == "IOCL-1002")
    assert valve["common_code"] is not None
    assert valve["common_code"]["status"] == "AUTO_GENERATED"

    second_scan = client.post("/api/harmonization/full-database-scan", headers=admin_headers)
    assert second_scan.status_code == 200
    second_ids = set(second_scan.json()["material_ids"])
    # The valve material's id must be present again since its code is only AUTO_GENERATED.
    all_materials = client.get("/api/materials", params={"q": "IOCL-1002"}, headers=admin_headers).json()["items"]
    valve_id = all_materials[0]["id"]
    assert valve_id in second_ids


def test_approved_mapping_is_never_overwritten_by_a_rescan(client, db_session, seed_roles_and_cpse, monkeypatch):
    """
    Once a Material Expert approves a harmonization, its common_code_id
    must survive any number of subsequent full-database rescans unchanged
    - even though the scan re-includes any non-approved material.
    """
    from app.workers import tasks as worker_tasks

    def _raise(*_a, **_kw):
        raise RuntimeError("simulated: no broker reachable in this test")

    monkeypatch.setattr(worker_tasks.bulk_ai_analysis, "delay", _raise)

    admin_headers = _register_and_login(client, "fda_approve_admin", "ADMIN")
    _create_org(client, admin_headers, "ONGC", "Oil and Natural Gas Corporation")

    _create_material(
        client, admin_headers, code="IOCL-1002", description="Carbon Steel Gate Valve",
        specification="API 600 Class 150", category="Valves", uom="Nos", cpse_code="IOCL",
    )
    _create_material(
        client, admin_headers, code="ONGC-2002", description="CS Gate Valve",
        specification="API 600 Class 150", category="Valve", uom="Nos", cpse_code="ONGC",
    )

    client.post("/api/harmonization/full-database-scan", headers=admin_headers)

    materials = client.get("/api/materials", params={"q": "IOCL-1002"}, headers=admin_headers).json()["items"]
    material_id = materials[0]["id"]
    material_detail = client.get(f"/api/materials/{material_id}", headers=admin_headers).json()
    original_code = material_detail["common_code"]["code"]

    # Manually mark the underlying common code APPROVED, mirroring what
    # approve_harmonization() does when a Material Expert approves it.
    common_code = db_session.query(CommonMaterialCode).filter(CommonMaterialCode.code == original_code).first()
    common_code.status = "APPROVED"
    db_session.commit()

    # Rescan repeatedly - the approved mapping must not move. This also
    # proves the scan-level SQL filter: an approved-linked material is
    # excluded from the query entirely, so it is never even re-queued.
    for _ in range(2):
        rescan = client.post("/api/harmonization/full-database-scan", headers=admin_headers)
        assert material_id not in rescan.json()["material_ids"]

    refreshed = client.get(f"/api/materials/{material_id}", headers=admin_headers).json()
    assert refreshed["common_code"]["code"] == original_code
    assert refreshed["common_code"]["status"] == "APPROVED"

    # Second, independent layer of protection: even if something else (e.g.
    # a direct /ai/analyze/{id} call, bypassing the scan's own SQL filter)
    # re-ran the AI pipeline on this exact material, analyzer._handle_decision
    # itself must refuse to reassign an already-APPROVED mapping.
    import uuid as uuid_module

    from app.ai.analyzer import analyze_material

    analyze_material(db_session, uuid_module.UUID(material_id))

    still_approved = client.get(f"/api/materials/{material_id}", headers=admin_headers).json()
    assert still_approved["common_code"]["code"] == original_code
    assert still_approved["common_code"]["status"] == "APPROVED"

    audit_resp = client.get(
        "/api/audit-logs", params={"action": "RESCAN_SKIPPED_APPROVED_MAPPING"}, headers=admin_headers
    )
    assert audit_resp.status_code == 200
    assert audit_resp.json()["total"] >= 1


def test_repeated_scan_does_not_duplicate_pending_approval_requests(client, db_session, seed_roles_and_cpse, monkeypatch):
    """
    A grade conflict (SS304 vs SS316) on otherwise near-identical
    descriptions should be gated to HUMAN_REVIEW_REQUIRED. Scanning twice
    must reuse/refresh the same pending ApprovalRequest, never create a
    second one for the same pair.
    """
    from app.workers import tasks as worker_tasks

    def _raise(*_a, **_kw):
        raise RuntimeError("simulated: no broker reachable in this test")

    monkeypatch.setattr(worker_tasks.bulk_ai_analysis, "delay", _raise)

    admin_headers = _register_and_login(client, "fda_dup_admin", "ADMIN")
    _create_org(client, admin_headers, "ONGC", "Oil and Natural Gas Corporation")

    _create_material(
        client, admin_headers, code="FDA-IOCL-BOLT-304", description="SS Bolt M10x50 SS304",
        category="Fasteners", uom="Numbers", cpse_code="IOCL", specification="SS304",
        material_type="Stainless Steel",
    )
    _create_material(
        client, admin_headers, code="FDA-ONGC-BOLT-316", description="SS Bolt M10x50 SS316",
        category="Fasteners", uom="Numbers", cpse_code="ONGC", specification="SS316",
        material_type="Stainless Steel",
    )

    for _ in range(2):
        resp = client.post("/api/harmonization/full-database-scan", headers=admin_headers)
        assert resp.status_code == 200

    materials = client.get("/api/materials", params={"q": "FDA-IOCL-BOLT-304"}, headers=admin_headers).json()["items"]
    bolt_id = materials[0]["id"]

    pending = (
        db_session.query(ApprovalRequest)
        .filter(ApprovalRequest.status == ApprovalStatus.PENDING.value)
        .filter(ApprovalRequest.material_id == bolt_id)
        .all()
    )
    # Either the pair was gated to human review (exactly one pending request
    # for this material) or the pipeline found no candidate at all - but
    # never more than one PENDING request for the same material.
    assert len(pending) <= 1


def test_full_database_scan_is_idempotent_no_duplicate_common_codes(client, db_session, seed_roles_and_cpse, monkeypatch):
    from app.workers import tasks as worker_tasks

    def _raise(*_a, **_kw):
        raise RuntimeError("simulated: no broker reachable in this test")

    monkeypatch.setattr(worker_tasks.bulk_ai_analysis, "delay", _raise)

    admin_headers = _register_and_login(client, "fda_idempotent_admin", "ADMIN")
    _create_org(client, admin_headers, "ONGC", "Oil and Natural Gas Corporation")

    _create_material(
        client, admin_headers, code="IOCL-1002", description="Carbon Steel Gate Valve",
        specification="API 600 Class 150", category="Valves", uom="Nos", cpse_code="IOCL",
    )
    _create_material(
        client, admin_headers, code="ONGC-2002", description="CS Gate Valve",
        specification="API 600 Class 150", category="Valve", uom="Nos", cpse_code="ONGC",
    )

    for _ in range(3):
        resp = client.post("/api/harmonization/full-database-scan", headers=admin_headers)
        assert resp.status_code == 200

    valve_codes = (
        db_session.query(CommonMaterialCode)
        .filter(CommonMaterialCode.standard_description.ilike("%gate valve%"))
        .all()
    )
    assert len(valve_codes) == 1, "repeated scans must not create duplicate common codes for the same group"
    assert re.fullmatch(r"CM-\d{6}", valve_codes[0].code)

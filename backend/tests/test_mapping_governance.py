"""
Approval workflow + governance (spec section 14/29/37): approve/reject/
edit-and-approve/manual-review transitions, and the invariant that an
APPROVED mapping can never be silently reassigned by a later rescan.
"""
from app.ai.analyzer import analyze_material
from app.models.enums import MappingDecisionStatus
from app.models.harmonization import CommonMaterialMapping
from tests.conftest import create_cpse, create_cpse_material, register_and_login


def _make_valve_pair(db_session, iocl, ongc):
    a = create_cpse_material(
        db_session, iocl, code="IOCL-1002", description="Carbon Steel Gate Valve",
        specification="API 600 Class 150", classification="Valve", uom="Nos",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC-2002", description="CS Gate Valve",
        specification="API 600 Class 150", classification="Valve", uom="Nos",
    )
    analyze_material(db_session, b.id)
    analyze_material(db_session, a.id)
    return a, b


def test_pending_mappings_appear_in_approval_queue(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "gov_pending_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    _make_valve_pair(db_session, iocl, ongc)

    pending = client.get("/api/approvals/pending", headers=headers).json()
    assert len(pending) >= 1


def test_approve_moves_mapping_to_approved_and_logs_audit(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "gov_approve_admin", "MATERIAL_EXPERT")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    _make_valve_pair(db_session, iocl, ongc)

    mapping = db_session.query(CommonMaterialMapping).first()
    resp = client.post(f"/api/approvals/{mapping.id}/approve", json={"remarks": "Confirmed equivalent"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["decision_status"] in (
        MappingDecisionStatus.APPROVED.value, MappingDecisionStatus.EDITED_AND_APPROVED.value,
    )

    audit = client.get("/api/audit-logs", params={"action": "MAPPING_APPROVED"}, headers=headers).json()
    assert audit["total"] >= 1


def test_reject_moves_mapping_to_rejected(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "gov_reject_admin", "MATERIAL_EXPERT")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    _make_valve_pair(db_session, iocl, ongc)

    mapping = db_session.query(CommonMaterialMapping).first()
    resp = client.post(f"/api/approvals/{mapping.id}/reject", json={"remarks": "Not the same part"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["decision_status"] == MappingDecisionStatus.REJECTED.value


def test_edit_and_approve_updates_standardized_fields(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "gov_edit_admin", "MATERIAL_EXPERT")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    _make_valve_pair(db_session, iocl, ongc)

    mapping = db_session.query(CommonMaterialMapping).first()
    resp = client.post(
        f"/api/approvals/{mapping.id}/edit-and-approve",
        json={"remarks": "Corrected description", "standardized_description": "Carbon Steel Gate Valve, API 600, Class 150"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision_status"] == MappingDecisionStatus.EDITED_AND_APPROVED.value
    assert body["common_material"]["standardized_description"] == "Carbon Steel Gate Valve, API 600, Class 150"


def test_viewer_cannot_approve(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "gov_viewer", "VIEWER")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    _make_valve_pair(db_session, iocl, ongc)

    mapping = db_session.query(CommonMaterialMapping).first()
    resp = client.post(f"/api/approvals/{mapping.id}/approve", json={}, headers=headers)
    assert resp.status_code == 403


def test_approved_mapping_is_never_overwritten_by_a_rescan(client, db_session, seed_roles_and_cpse):
    """
    Once approved, a mapping's common material must survive any number of
    subsequent rescans unchanged - even though the scan re-includes any
    material without an active mapping... an APPROVED one is explicitly
    excluded by app.ai.analyzer._handle_decision's own governance guard.
    """
    headers = register_and_login(client, "gov_rescan_admin", "MATERIAL_EXPERT")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    a, b = _make_valve_pair(db_session, iocl, ongc)

    mapping = db_session.query(CommonMaterialMapping).first()
    client.post(f"/api/approvals/{mapping.id}/approve", json={}, headers=headers)
    original_code = mapping.common_material.common_code

    # Direct re-run of the AI pipeline (what a rescan/incremental-sync would trigger).
    analyze_material(db_session, a.id)
    analyze_material(db_session, b.id)

    db_session.refresh(mapping)
    assert mapping.common_material.common_code == original_code
    assert mapping.decision_status == MappingDecisionStatus.APPROVED.value

    audit = client.get("/api/audit-logs", params={"action": "RESCAN_SKIPPED_APPROVED_MAPPING"}, headers=headers).json()
    assert audit["total"] >= 1


def test_repeated_analysis_does_not_duplicate_mappings_for_same_pair(client, db_session, seed_roles_and_cpse):
    """Idempotency (spec section 29): re-running analysis on the same pair
    must update the existing mapping, never create a second row for it."""
    headers = register_and_login(client, "gov_idempotent_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    a, b = _make_valve_pair(db_session, iocl, ongc)

    for _ in range(3):
        analyze_material(db_session, b.id)
        analyze_material(db_session, a.id)

    mappings = db_session.query(CommonMaterialMapping).filter(CommonMaterialMapping.cpse_material_id == a.id).all()
    assert len(mappings) == 1

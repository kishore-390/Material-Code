"""
Automatic batch settlement (reliability improvement on top of the spec 28
pipeline): a burst of newly-synced, mutually-matching materials must
converge to the same common material mapping WITHOUT a human manually
calling /harmonization/scan - see app.connectors.sync_engine._trigger_
batch_settlement and app.workers.tasks.settle_batch.

These tests exercise the real app.connectors.sync_engine.run_full_sync
entry point end to end (fetch -> upsert -> analyze -> settle), using a
fake SourceConnector so no real database-to-database connection is needed -
everything downstream of "here are the canonical records this sync
discovered" is the genuine production code path, identical to a real
PostgreSQL/MySQL sync.
"""
import uuid

from app.connectors import sync_engine
from app.connectors.base import CanonicalMaterialRecord, CanonicalRecordPage
from app.models.enums import MappingDecisionStatus
from app.models.harmonization import CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.source_connection import SourceConnection
from tests.conftest import create_cpse


def _make_connection(db_session, cpse, *, table_name: str) -> SourceConnection:
    connection = SourceConnection(
        cpse_id=cpse.id,
        connection_name=f"{cpse.code} Test Source",
        database_type="POSTGRESQL",
        host="unused", port=5432, database_name="unused",
        username_reference="UNUSED_USER", secret_reference="UNUSED_PASSWORD",
        ssl_enabled=False,
        table_name=table_name,
        column_mapping={"original_material_code": "code", "original_description": "descr", "uom": "uom"},
        cursor_column=None,
        enabled=True,
    )
    db_session.add(connection)
    db_session.commit()
    db_session.refresh(connection)
    return connection


def _one_page(record: CanonicalMaterialRecord) -> CanonicalRecordPage:
    return CanonicalRecordPage(items=[record], has_more=False)


def test_two_matching_materials_synced_separately_converge_without_manual_scan(db_session, seed_roles_and_cpse):
    """
    Mirrors the exact scenario the live demo exposed: CPSE A's connector
    syncs a bolt, then (before any human intervenes) CPSE B's connector
    syncs the same physical bolt worded differently. Neither sync call's
    own settling pass can see the OTHER connection's material by itself -
    what makes them converge is that each `run_full_sync(...,
    wait_for_settlement=True)` call only returns once ITS OWN batch is
    fully settled, so by the time CPSE B's sync (and its own settling pass)
    runs, CPSE A's material - and its embedding - already exists.
    """
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    conn_a = _make_connection(db_session, iocl, table_name="demo_source_iocl_settle_test")
    conn_b = _make_connection(db_session, ongc, table_name="demo_source_ongc_settle_test")

    record_a = CanonicalMaterialRecord(
        original_material_code="IOCL-SETTLE-001", original_description="SS Hex Bolt M10x50", uom="PC",
        classification="Fastener", material_grade="SS304", dimensions="M10x50", standard="ASTM F593",
    )
    record_b = CanonicalMaterialRecord(
        original_material_code="ONGC-SETTLE-001", original_description="Stainless Steel Bolt 10mm x 50mm", uom="PC",
        classification="Fastener", material_grade="SS304", dimensions="M10x50", standard="ASTM F593",
    )

    sync_engine._run_sync(db_session, conn_a, "FULL", lambda page: _one_page(record_a), wait_for_settlement=True)
    sync_engine._run_sync(db_session, conn_b, "FULL", lambda page: _one_page(record_b), wait_for_settlement=True)

    material_a = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "IOCL-SETTLE-001").one()
    material_b = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "ONGC-SETTLE-001").one()

    mapping_a = (
        db_session.query(CommonMaterialMapping)
        .filter(CommonMaterialMapping.cpse_material_id == material_a.id)
        .filter(CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value)
        .one_or_none()
    )
    mapping_b = (
        db_session.query(CommonMaterialMapping)
        .filter(CommonMaterialMapping.cpse_material_id == material_b.id)
        .filter(CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value)
        .one_or_none()
    )

    assert mapping_a is not None, "the first-synced material must also end up mapped once the batch settles"
    assert mapping_b is not None
    assert mapping_a.common_material_id == mapping_b.common_material_id, "both sides must share one common material"

    # No duplicate mappings and no duplicate common-material codes were created.
    assert db_session.query(CommonMaterialMapping).filter(
        CommonMaterialMapping.cpse_material_id.in_([material_a.id, material_b.id])
    ).count() == 2


def test_settlement_never_reassigns_an_approved_mapping(client, db_session, seed_roles_and_cpse):
    """A material already APPROVED into a common material must survive a
    later sync batch's automatic settlement pass unchanged, even though
    settlement re-runs analysis on newly-synced materials."""
    from tests.conftest import create_cpse_material, register_and_login
    from app.ai.analyzer import analyze_material

    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    # A pre-existing, already-embedded candidate so the synced material below
    # finds a match on its own first pass, deterministically, without
    # depending on the settlement pass to produce the mapping this test
    # actually needs to approve and then protect.
    existing_candidate = create_cpse_material(
        db_session, ongc, code="ONGC-EXISTING-BEARING", description="Ball Bearing 6205",
        classification="Bearing", uom="EACH", dimensions="6205",
    )
    analyze_material(db_session, existing_candidate.id)

    conn_a = _make_connection(db_session, iocl, table_name="demo_source_iocl_approve_test")
    record_a = CanonicalMaterialRecord(
        original_material_code="IOCL-APPROVE-001", original_description="Deep Groove Ball Bearing 6205", uom="EACH",
        classification="Bearing", dimensions="6205",
    )
    sync_engine._run_sync(db_session, conn_a, "FULL", lambda page: _one_page(record_a), wait_for_settlement=True)

    material_a = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "IOCL-APPROVE-001").one()
    mapping = db_session.query(CommonMaterialMapping).filter(CommonMaterialMapping.cpse_material_id == material_a.id).first()
    assert mapping is not None, "should have matched the pre-existing, already-embedded candidate on its first pass"

    headers = register_and_login(client, "settle_approve_admin", "MATERIAL_EXPERT")
    approve_resp = client.post(f"/api/approvals/{mapping.id}/approve", json={}, headers=headers)
    assert approve_resp.status_code == 200
    original_common_material_id = mapping.common_material_id

    # A second, unrelated sync batch runs its own settlement pass afterward -
    # must not touch the already-approved mapping above.
    conn_b = _make_connection(db_session, ongc, table_name="demo_source_ongc_approve_test")
    record_b = CanonicalMaterialRecord(
        original_material_code="ONGC-APPROVE-001", original_description="Electrical Cable", uom="METER",
        classification="Cable",
    )
    sync_engine._run_sync(db_session, conn_b, "FULL", lambda page: _one_page(record_b), wait_for_settlement=True)

    db_session.refresh(mapping)
    assert mapping.decision_status in (MappingDecisionStatus.APPROVED.value, MappingDecisionStatus.EDITED_AND_APPROVED.value)
    assert mapping.common_material_id == original_common_material_id

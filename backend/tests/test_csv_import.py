"""
DEMO-ONLY CSV import (app.services.csv_import_service / app.api.endpoints.demo_import).

Every test here exercises the REAL endpoint through the TestClient and the
REAL AI pipeline (app.ai.analyzer.analyze_material via the same settlement
mechanism app.connectors.sync_engine uses) - never a mocked decision. The
point of this suite is to prove the CSV import path is not a second,
parallel implementation: it must produce exactly the same kind of
CPSEMaterial/AIAnalysis/CommonMaterial/CommonMaterialMapping rows a real
database sync would.
"""
import csv
import io

from app.models.enums import MappingDecisionStatus
from app.models.harmonization import CommonMaterial, CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.matching import AIAnalysis
from app.services import normalization
from app.services.csv_import_service import REQUIRED_COLUMNS
from tests.conftest import create_cpse, create_cpse_material, register_and_login


def _row(cpse_code, code, description, **kwargs):
    row = {col: "" for col in REQUIRED_COLUMNS}
    row.update(cpse_code=cpse_code, original_material_code=code, original_description=description)
    row.update(kwargs)
    return row


def _csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REQUIRED_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _upload(client, headers, endpoint, rows, filename="demo.csv"):
    return client.post(
        f"/api/demo-import/{endpoint}",
        headers=headers,
        files={"file": (filename, _csv_bytes(rows), "text/csv")},
    )


def _admin_headers(client, seed_roles_and_cpse):
    return register_and_login(client, "csvadmin", "ADMIN")


def test_valid_csv_import_creates_materials(client, db_session, seed_roles_and_cpse):
    """Scenario: valid CSV. A well-formed row for an existing CPSE is
    accepted, imported, and produces a real CPSEMaterial row."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    rows = [_row("IOCL", "CSV-VALID-01", "Demo Import Test Bolt", material_type="Fastener", uom="PC")]

    validate_resp = _upload(client, headers, "validate", rows)
    assert validate_resp.status_code == 200
    body = validate_resp.json()
    assert body["is_importable"] is True
    assert body["valid_count"] == 1
    assert body["invalid_count"] == 0

    confirm_resp = _upload(client, headers, "confirm", rows)
    assert confirm_resp.status_code == 200
    result = confirm_resp.json()
    assert result["created"] == 1
    assert result["failed"] == 0

    material = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "CSV-VALID-01").first()
    assert material is not None
    assert material.is_demo_data is True
    assert material.original_description == "Demo Import Test Bolt"


def test_invalid_row_missing_required_field_is_rejected(client, seed_roles_and_cpse):
    """Scenario: invalid CSV / row-level validation. A row missing a
    required field is flagged and excluded from import, never inserted."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    rows = [_row("IOCL", "CSV-BAD-01", "")]  # empty description

    resp = _upload(client, headers, "validate", rows)
    body = resp.json()
    assert body["valid_count"] == 0
    assert body["invalid_count"] == 1
    assert any("original_description" in e for e in body["invalid_rows"][0]["errors"])

    confirm_resp = _upload(client, headers, "confirm", rows)
    assert confirm_resp.status_code == 422


def test_missing_required_column_rejected(client, seed_roles_and_cpse):
    """Scenario: CSV missing required column(s) entirely."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[c for c in REQUIRED_COLUMNS if c != "uom"])
    writer.writeheader()
    writer.writerow({c: "x" for c in REQUIRED_COLUMNS if c != "uom"})
    resp = client.post(
        "/api/demo-import/validate",
        headers=headers,
        files={"file": ("bad.csv", buffer.getvalue().encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_importable"] is False
    assert any("uom" in e for e in body["file_errors"])


def test_duplicate_source_material_codes_within_csv_rejected(client, seed_roles_and_cpse):
    """Scenario: duplicate original_material_code within the same CSV."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    rows = [
        _row("IOCL", "CSV-DUP-01", "First copy", material_type="Fastener", uom="PC"),
        _row("IOCL", "CSV-DUP-01", "Second copy", material_type="Fastener", uom="PC"),
    ]
    resp = _upload(client, headers, "validate", rows)
    body = resp.json()
    assert body["valid_count"] == 0
    assert body["invalid_count"] == 2
    assert all("Duplicate" in " ".join(r["errors"]) for r in body["invalid_rows"])


def test_demo_provenance_is_marked_on_every_imported_row(client, db_session, seed_roles_and_cpse):
    """Scenario: demo provenance. Every row imported via CSV must be
    permanently marked is_demo_data - never indistinguishable from a real
    sync's row."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    rows = [_row("IOCL", "CSV-DEMO-01", "Demo Provenance Test", material_type="Fastener", uom="PC")]
    _upload(client, headers, "confirm", rows)

    material = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "CSV-DEMO-01").first()
    assert material.is_demo_data is True


def test_canonical_conversion_runs_normalization_and_extraction(client, db_session, seed_roles_and_cpse):
    """Scenario: canonical conversion. The CSV row must pass through the
    exact same normalization/attribute-extraction step a real sync uses
    (app.services.material_ingestion), not a CSV-specific shortcut."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    rows = [_row("IOCL", "CSV-NORM-01", "SS Hex Bolt M10x50", material_type="Fastener", uom="PC", dimensions="M10x50")]
    _upload(client, headers, "confirm", rows)

    material = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "CSV-NORM-01").first()
    assert material.normalized_description == normalization.normalize_description("SS Hex Bolt M10x50")
    assert material.normalized_classification == normalization.normalize_classification("Fastener")
    assert material.normalized_uom == normalization.normalize_uom("PC")


def test_same_ai_pipeline_executes_for_imported_material(client, db_session, seed_roles_and_cpse):
    """Scenario: same AI pipeline execution. An AIAnalysis row must exist
    for the imported material - proof app.ai.analyzer.analyze_material
    actually ran, not a separate CSV-only code path."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    rows = [_row("IOCL", "CSV-AI-01", "Demo AI Pipeline Test Item", material_type="Widget", uom="EACH")]
    _upload(client, headers, "confirm", rows)

    material = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "CSV-AI-01").first()
    analysis = db_session.query(AIAnalysis).filter(AIAnalysis.material_id == material.id).first()
    assert analysis is not None
    assert analysis.status == "COMPLETED"


def test_new_common_code_generated_for_mutually_equivalent_import(client, db_session, seed_roles_and_cpse):
    """Scenario: new common code generation. Two equivalent materials
    imported together with no pre-existing match must converge to ONE
    newly-generated common code, without a manual rescan."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    rows = [
        _row("IOCL", "CSV-NEW-A", "Grease Nipple Straight 1/4 BSP", material_type="Lubrication Fitting",
             uom="PC", classification="Lubrication Fitting", function="Lubrication"),
        _row("ONGC", "CSV-NEW-B", "Straight Grease Nipple 1/4 inch BSP Thread", material_type="Lubrication Fitting",
             uom="PC", classification="Lubrication Fitting", function="Lubrication"),
    ]
    resp = _upload(client, headers, "confirm", rows)
    result = resp.json()
    assert result["created"] == 2

    codes = {r["original_material_code"]: r["common_material_code"] for r in result["results"]}
    assert codes["CSV-NEW-A"] is not None
    assert codes["CSV-NEW-A"] == codes["CSV-NEW-B"]
    assert codes["CSV-NEW-A"].startswith("CM-")


def test_common_code_reused_not_duplicated_for_a_third_equivalent_material(client, db_session, seed_roles_and_cpse):
    """Scenario: common code reuse. A CSV-imported material equivalent to
    an ALREADY-mapped pair must reuse that existing common code rather than
    minting a second one for the same real-world item."""
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")

    from app.ai.analyzer import analyze_material

    a = create_cpse_material(
        db_session, iocl, code="IOCL-EXIST-01", description="SS Hex Bolt M10x50",
        classification="Fastener", uom="PC", material_grade="SS304", dimensions="M10x50", standard="ASTM F593",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC-EXIST-01", description="Stainless Steel Bolt 10mm x 50mm",
        classification="Fastener", uom="PC", material_grade="SS304", dimensions="M10x50", standard="ASTM F593",
    )
    analyze_material(db_session, b.id)
    analyze_material(db_session, a.id)

    existing_mapping = (
        db_session.query(CommonMaterialMapping)
        .filter(CommonMaterialMapping.cpse_material_id == a.id)
        .filter(CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value)
        .first()
    )
    assert existing_mapping is not None
    existing_code = existing_mapping.common_material.common_code

    headers = _admin_headers(client, seed_roles_and_cpse)
    rows = [
        _row("BPCL", "CSV-REUSE-01", "Hex Head SS304 Bolt 10mm x 50mm", material_type="Fastener",
             uom="PC", material_grade="SS304", dimensions="M10x50", standard="ASTM F593", classification="Fastener"),
    ]
    resp = _upload(client, headers, "confirm", rows)
    result = resp.json()
    assert result["results"][0]["common_material_code"] == existing_code

    all_codes = {c.common_code for c in db_session.query(CommonMaterial).all()}
    assert len(all_codes) == 1


def test_technical_conflict_is_detected_not_hidden(client, db_session, seed_roles_and_cpse):
    """Scenario: technical conflict handling. Two otherwise-similar
    materials with a conflicting grade must be flagged TECHNICAL_CONFLICT,
    never silently harmonized together."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    rows = [
        _row("IOCL", "CSV-CONFLICT-A", "SS Bolt M10x50 SS304", material_type="Fastener", uom="PC",
             material_grade="SS304", classification="Fastener"),
        _row("ONGC", "CSV-CONFLICT-B", "SS Bolt M10x50 SS316", material_type="Fastener", uom="PC",
             material_grade="SS316", classification="Fastener"),
    ]
    resp = _upload(client, headers, "confirm", rows)
    result = resp.json()
    statuses = {r["original_material_code"]: r["decision_status"] for r in result["results"]}
    assert MappingDecisionStatus.TECHNICAL_CONFLICT.value in statuses.values()


def test_no_approval_bypass_via_csv_import(client, seed_roles_and_cpse):
    """Scenario: no approval bypass. A freshly CSV-imported mapping must
    never come back already APPROVED - only a human approval action can do
    that (app.services.harmonization_service), never the import itself."""
    headers = _admin_headers(client, seed_roles_and_cpse)
    rows = [
        _row("IOCL", "CSV-NOBYPASS-A", "Unique Demo Widget Alpha", material_type="Widget", uom="EACH"),
        _row("IOCL", "CSV-NOBYPASS-B", "Totally Unrelated Demo Widget Beta", material_type="Gadget", uom="EACH"),
    ]
    resp = _upload(client, headers, "confirm", rows)
    result = resp.json()
    forbidden = {MappingDecisionStatus.APPROVED.value, MappingDecisionStatus.EDITED_AND_APPROVED.value}
    for row in result["results"]:
        assert row["decision_status"] not in forbidden


def test_security_rejects_non_csv_and_unknown_cpse_and_production_overwrite(client, db_session, seed_roles_and_cpse):
    """Scenario: security validation. (1) non-CSV files are rejected,
    (2) an unknown CPSE code can never be silently onboarded, (3) a
    CSV row can never overwrite a real (non-demo) production material."""
    headers = _admin_headers(client, seed_roles_and_cpse)

    resp = client.post(
        "/api/demo-import/validate",
        headers=headers,
        files={"file": ("not_a_csv.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 422

    iocl = seed_roles_and_cpse["cpse"]
    from app.models.cpse import CPSE

    unknown_rows = [_row("NOSUCHCPSE", "CSV-SEC-01", "Should not import", material_type="Fastener", uom="PC")]
    body = _upload(client, headers, "validate", unknown_rows).json()
    assert body["invalid_count"] == 1
    assert "Unknown CPSE code" in body["invalid_rows"][0]["errors"][0]
    assert db_session.query(CPSE).filter(CPSE.code == "NOSUCHCPSE").first() is None

    real_material = create_cpse_material(
        db_session, iocl, code="REAL-PROD-01", description="Real production material",
        classification="Fastener", uom="PC",
    )
    assert real_material.is_demo_data is False

    overwrite_rows = [_row("IOCL", "REAL-PROD-01", "Attempted demo overwrite", material_type="Fastener", uom="PC")]
    body = _upload(client, headers, "validate", overwrite_rows).json()
    assert body["invalid_count"] == 1
    assert "production data" in body["invalid_rows"][0]["errors"][0]

    confirm_resp = _upload(client, headers, "confirm", overwrite_rows)
    assert confirm_resp.status_code == 422
    db_session.refresh(real_material)
    assert real_material.original_description == "Real production material"


def test_import_history_lists_completed_batches(client, seed_roles_and_cpse):
    headers = _admin_headers(client, seed_roles_and_cpse)
    rows = [_row("IOCL", "CSV-HIST-01", "History Test Item", material_type="Fastener", uom="PC")]
    _upload(client, headers, "confirm", rows)

    resp = client.get("/api/demo-import/history", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["filename"] == "demo.csv" for item in body["items"])


def test_viewer_role_cannot_import(client, seed_roles_and_cpse):
    """RBAC: only ADMIN/MATERIAL_EXPERT can trigger a demo import, mirroring
    the same role restriction as a real sync trigger."""
    headers = register_and_login(client, "csvviewer", "VIEWER")
    rows = [_row("IOCL", "CSV-RBAC-01", "Should be forbidden", material_type="Fastener", uom="PC")]
    resp = _upload(client, headers, "confirm", rows)
    assert resp.status_code == 403

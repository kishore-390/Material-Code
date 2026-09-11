"""
Company self-service material upload (app.api.endpoints.material_upload) -
the real (non-demo) production counterpart to the DEMO ONLY admin CSV
import (app.api.endpoints.demo_import), added per the "add a real
per-company upload path" decision: production ingestion stays
connector-first, but an authorized company user may also upload their own
real material data, strictly scoped to their own CPSE, through the exact
same canonical ingestion pipeline.
"""
import csv
import io

from openpyxl import Workbook

from app.models.material import CPSEMaterial
from app.services.csv_import_service import REQUIRED_COLUMNS
from tests.conftest import create_cpse, register_and_login


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


def _xlsx_bytes(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(REQUIRED_COLUMNS))
    for row in rows:
        ws.append([row.get(col, "") for col in REQUIRED_COLUMNS])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _upload(client, headers, endpoint, content, filename, cpse_id=None, content_type="text/csv"):
    data = {"cpse_id": cpse_id} if cpse_id else {}
    return client.post(
        f"/api/materials/upload/{endpoint}",
        headers=headers,
        files={"file": (filename, content, content_type)},
        data=data,
    )


def test_company_user_can_upload_own_real_material(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "iocl_uploader1", "MATERIAL_EXPERT", cpse_code="IOCL")
    rows = [_row("IOCL", "IOCL-UP-01", "Carbon Steel Pipe 100mm ASTM A106", material_type="Pipe", uom="METER")]

    validate_resp = _upload(client, headers, "validate", _csv_bytes(rows), "iocl_materials.csv")
    assert validate_resp.status_code == 200
    assert validate_resp.json()["is_importable"] is True

    confirm_resp = _upload(client, headers, "confirm", _csv_bytes(rows), "iocl_materials.csv")
    assert confirm_resp.status_code == 200
    result = confirm_resp.json()
    assert result["created"] == 1

    material = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "IOCL-UP-01").first()
    assert material is not None
    assert material.is_demo_data is False


def test_company_user_cannot_upload_for_another_cpse(client, db_session, seed_roles_and_cpse):
    create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")
    headers = register_and_login(client, "iocl_uploader2", "MATERIAL_EXPERT", cpse_code="IOCL")
    rows = [_row("BPCL", "BPCL-UP-01", "CS Pipe 100 MM ASTM A106", material_type="Pipe", uom="METER")]

    validate_resp = _upload(client, headers, "validate", _csv_bytes(rows), "sneaky.csv")
    body = validate_resp.json()
    assert body["invalid_count"] == 1
    assert "not authorized" in body["invalid_rows"][0]["errors"][0]

    confirm_resp = _upload(client, headers, "confirm", _csv_bytes(rows), "sneaky.csv")
    assert confirm_resp.status_code == 422


def test_central_admin_must_specify_cpse_id(client, seed_roles_and_cpse):
    headers = register_and_login(client, "central_uploader1", "ADMIN")
    rows = [_row("IOCL", "IOCL-UP-02", "Item", material_type="Pipe", uom="METER")]
    response = _upload(client, headers, "validate", _csv_bytes(rows), "x.csv")
    assert response.status_code == 422


def test_central_admin_can_upload_on_behalf_of_named_cpse(client, db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    headers = register_and_login(client, "central_uploader2", "ADMIN")
    rows = [_row("IOCL", "IOCL-UP-03", "Item", material_type="Pipe", uom="METER")]

    response = _upload(client, headers, "confirm", _csv_bytes(rows), "x.csv", cpse_id=str(iocl.id))
    assert response.status_code == 200
    assert response.json()["created"] == 1


def test_viewer_cannot_upload_materials(client, seed_roles_and_cpse):
    headers = register_and_login(client, "iocl_viewer_uploader", "VIEWER", cpse_code="IOCL")
    rows = [_row("IOCL", "IOCL-UP-04", "Item", material_type="Pipe", uom="METER")]
    response = _upload(client, headers, "confirm", _csv_bytes(rows), "x.csv")
    assert response.status_code == 403


def test_company_reupload_updates_own_real_data_without_being_blocked(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "iocl_uploader3", "MATERIAL_EXPERT", cpse_code="IOCL")
    rows_v1 = [_row("IOCL", "IOCL-UP-05", "Original Description", material_type="Pipe", uom="METER")]
    first = _upload(client, headers, "confirm", _csv_bytes(rows_v1), "x.csv")
    assert first.json()["created"] == 1

    rows_v2 = [_row("IOCL", "IOCL-UP-05", "Updated Description After Correction", material_type="Pipe", uom="METER")]
    second = _upload(client, headers, "confirm", _csv_bytes(rows_v2), "x.csv")
    assert second.status_code == 200
    assert second.json()["updated"] == 1
    assert second.json()["failed"] == 0

    material = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "IOCL-UP-05").first()
    assert material.original_description == "Updated Description After Correction"
    assert material.is_demo_data is False


def test_demo_import_cannot_overwrite_company_uploaded_real_material(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "iocl_uploader4", "MATERIAL_EXPERT", cpse_code="IOCL")
    rows = [_row("IOCL", "IOCL-UP-06", "Real Company Data", material_type="Pipe", uom="METER")]
    _upload(client, headers, "confirm", _csv_bytes(rows), "x.csv")

    admin_headers = register_and_login(client, "demo_admin_conflict", "ADMIN")
    demo_rows = [_row("IOCL", "IOCL-UP-06", "Demo Attempted Overwrite", material_type="Pipe", uom="METER")]
    demo_csv = _csv_bytes(demo_rows)
    validate_resp = client.post(
        "/api/demo-import/validate", headers=admin_headers,
        files={"file": ("demo.csv", demo_csv, "text/csv")},
    )
    body = validate_resp.json()
    assert body["invalid_count"] == 1
    assert "production data" in body["invalid_rows"][0]["errors"][0]


def test_excel_upload_parses_and_imports(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "iocl_uploader5", "MATERIAL_EXPERT", cpse_code="IOCL")
    rows = [_row("IOCL", "IOCL-UP-07", "Gate Valve Cast Steel 4 inch", material_type="Valve", uom="EACH")]
    xlsx = _xlsx_bytes(rows)

    validate_resp = _upload(
        client, headers, "validate", xlsx, "materials.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert validate_resp.status_code == 200
    assert validate_resp.json()["valid_count"] == 1

    confirm_resp = _upload(
        client, headers, "confirm", xlsx, "materials.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["created"] == 1

    material = db_session.query(CPSEMaterial).filter(CPSEMaterial.original_material_code == "IOCL-UP-07").first()
    assert material is not None
    assert material.original_description == "Gate Valve Cast Steel 4 inch"


def test_upload_history_scoped_to_own_company(client, db_session, seed_roles_and_cpse):
    bpcl = create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")

    iocl_headers = register_and_login(client, "iocl_uploader6", "MATERIAL_EXPERT", cpse_code="IOCL")
    _upload(client, iocl_headers, "confirm", _csv_bytes([_row("IOCL", "IOCL-UP-08", "Item", material_type="Pipe", uom="METER")]), "iocl.csv")

    bpcl_headers = register_and_login(client, "bpcl_uploader1", "MATERIAL_EXPERT", cpse_code="BPCL")
    _upload(client, bpcl_headers, "confirm", _csv_bytes([_row("BPCL", "BPCL-UP-08", "Item", material_type="Pipe", uom="METER")]), "bpcl.csv")

    iocl_history = client.get("/api/materials/upload/history", headers=iocl_headers).json()
    assert all(item["filename"] == "iocl.csv" for item in iocl_history["items"])
    assert any(item["filename"] == "iocl.csv" for item in iocl_history["items"])

    admin_headers = register_and_login(client, "central_uploader3", "ADMIN")
    admin_history = client.get("/api/materials/upload/history", headers=admin_headers).json()
    filenames = {item["filename"] for item in admin_history["items"]}
    assert {"iocl.csv", "bpcl.csv"}.issubset(filenames)


def test_upload_template_download(client, seed_roles_and_cpse):
    headers = register_and_login(client, "iocl_uploader7", "MATERIAL_EXPERT", cpse_code="IOCL")
    response = client.get("/api/materials/upload/template", headers=headers)
    assert response.status_code == 200
    assert "cpse_code" in response.text
    assert "original_material_code" in response.text

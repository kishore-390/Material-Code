"""
"Each CPSE company should only be able to access its own material
database" (role-based per-company data isolation). A user registered with
a cpse_code (a Company Admin/User in spec terms) must never be able to see
another company's materials/CPSE row/dashboard, no matter what id they pass
in a request - app.api.deps.scoped_cpse_id/assert_cpse_access enforce this
uniformly. A central/admin user (no cpse_code) remains unrestricted, since
cross-company comparison is the entire point of the central approval
workflow.
"""
from tests.conftest import create_cpse, create_cpse_material, register_and_login


def test_company_user_sees_only_own_materials_in_list(client, db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    bpcl = create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")
    create_cpse_material(db_session, iocl, code="IOCL-ISO-01", description="IOCL Item", classification="Pipe", uom="Meter")
    create_cpse_material(db_session, bpcl, code="BPCL-ISO-01", description="BPCL Item", classification="Pipe", uom="Meter")

    headers = register_and_login(client, "iocl_user", "MATERIAL_EXPERT", cpse_code="IOCL")
    response = client.get("/api/cpse-materials", headers=headers)
    assert response.status_code == 200
    codes = {m["original_material_code"] for m in response.json()["items"]}
    assert "IOCL-ISO-01" in codes
    assert "BPCL-ISO-01" not in codes


def test_company_user_cannot_force_another_cpse_id_in_list_filter(client, db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    bpcl = create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")
    create_cpse_material(db_session, bpcl, code="BPCL-ISO-02", description="BPCL Item", classification="Pipe", uom="Meter")

    headers = register_and_login(client, "iocl_user2", "MATERIAL_EXPERT", cpse_code="IOCL")
    response = client.get("/api/cpse-materials", params={"cpse_id": str(bpcl.id)}, headers=headers)
    assert response.status_code == 403


def test_company_user_cannot_view_another_companys_material_detail(client, db_session, seed_roles_and_cpse):
    bpcl = create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")
    other = create_cpse_material(db_session, bpcl, code="BPCL-ISO-03", description="BPCL Item", classification="Pipe", uom="Meter")

    headers = register_and_login(client, "iocl_user3", "MATERIAL_EXPERT", cpse_code="IOCL")
    response = client.get(f"/api/cpse-materials/{other.id}", headers=headers)
    assert response.status_code == 403


def test_company_user_search_never_returns_another_companys_materials(client, db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    bpcl = create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")
    create_cpse_material(db_session, iocl, code="IOCL-ISO-04", description="Ball Valve Assembly", classification="Valve", uom="Nos")
    create_cpse_material(db_session, bpcl, code="BPCL-ISO-04", description="Ball Valve Assembly", classification="Valve", uom="Nos")

    headers = register_and_login(client, "iocl_user4", "MATERIAL_EXPERT", cpse_code="IOCL")
    response = client.get("/api/cpse-materials/search", params={"q": "Ball Valve"}, headers=headers)
    assert response.status_code == 200
    codes = {m["original_material_code"] for m in response.json()}
    assert codes == {"IOCL-ISO-04"}


def test_central_admin_is_not_restricted_across_companies(client, db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    bpcl = create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")
    create_cpse_material(db_session, iocl, code="IOCL-ISO-05", description="Item", classification="Pipe", uom="Meter")
    create_cpse_material(db_session, bpcl, code="BPCL-ISO-05", description="Item", classification="Pipe", uom="Meter")

    headers = register_and_login(client, "central_admin", "ADMIN")
    response = client.get("/api/cpse-materials", headers=headers)
    codes = {m["original_material_code"] for m in response.json()["items"]}
    assert {"IOCL-ISO-05", "BPCL-ISO-05"}.issubset(codes)


def test_company_user_cannot_run_cross_company_similarity_search(client, db_session, seed_roles_and_cpse):
    iocl = seed_roles_and_cpse["cpse"]
    material = create_cpse_material(db_session, iocl, code="IOCL-ISO-06", description="Item", classification="Pipe", uom="Meter")

    headers = register_and_login(client, "iocl_user5", "MATERIAL_EXPERT", cpse_code="IOCL")
    response = client.get(f"/api/cpse-materials/{material.id}/similar", headers=headers)
    assert response.status_code == 403


def test_company_user_sees_only_own_cpse_in_roster(client, db_session, seed_roles_and_cpse):
    create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")
    headers = register_and_login(client, "iocl_user6", "MATERIAL_EXPERT", cpse_code="IOCL")

    response = client.get("/api/cpse", headers=headers)
    codes = {c["code"] for c in response.json()}
    assert codes == {"IOCL"}


def test_company_user_cannot_view_another_cpse_detail(client, db_session, seed_roles_and_cpse):
    bpcl = create_cpse(db_session, "BPCL", "Bharat Petroleum Corporation Limited")
    headers = register_and_login(client, "iocl_user7", "MATERIAL_EXPERT", cpse_code="IOCL")

    response = client.get(f"/api/cpse/{bpcl.id}", headers=headers)
    assert response.status_code == 403


def test_company_user_cannot_view_cross_company_dashboard(client, seed_roles_and_cpse):
    headers = register_and_login(client, "iocl_user8", "MATERIAL_EXPERT", cpse_code="IOCL")
    response = client.get("/api/dashboard/statistics", headers=headers)
    assert response.status_code == 403

    response = client.get("/api/dashboard/trends", headers=headers)
    assert response.status_code == 403


def test_central_admin_can_view_dashboard(client, seed_roles_and_cpse):
    headers = register_and_login(client, "central_admin2", "ADMIN")
    response = client.get("/api/dashboard/statistics", headers=headers)
    assert response.status_code == 200
